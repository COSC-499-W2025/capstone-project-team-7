"""
Upload and Parse API routes
Implements /api/uploads endpoints per api-plan.md
"""

import base64
import json
import logging
import os
import uuid
import hashlib
import magic
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body, Header, Depends
from pydantic import BaseModel, Field

from services.archive_utils import ensure_zip
from scanner.parser import parse_zip
from scanner.models import ParseResult, ScanPreferences
from api.request_context import set_request_access_token

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

def _extract_user_id_from_token(token: str) -> Optional[str]:
    try:
        import jwt

        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if user_id:
            return user_id
    except Exception:
        pass

    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        padding = "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(decoded.decode("utf-8"))
        user_id = payload.get("sub")
        if user_id:
            return user_id
    except Exception:
        return None

    return None


# Authentication helper
async def verify_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify JWT token from Authorization header.
    Returns user_id from token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    set_request_access_token(token)

    user_id = _extract_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


# Pydantic models
class UploadResponse(BaseModel):
    upload_id: str
    status: str = "stored"
    filename: str
    size_bytes: int
    

class UploadStatus(BaseModel):
    upload_id: str
    status: str
    filename: str
    size_bytes: int
    created_at: str
    metadata: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    expected: Optional[str] = None


class FileMetadata(BaseModel):
    """File metadata from parse result"""
    path: str
    size_bytes: int
    mime_type: str
    created_at: str
    modified_at: str
    file_hash: Optional[str] = None
    media_info: Optional[Dict[str, Any]] = None


class ParseIssueResponse(BaseModel):
    """Parse issue/warning for API response"""
    path: str
    code: str
    message: str


class ParseRequest(BaseModel):
    """Request body for parse operation"""
    profile_id: Optional[str] = Field(None, description="Optional profile ID for scan preferences")
    relevance_only: bool = Field(False, description="Only include relevant files")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Custom scan preferences")


class ParseResponse(BaseModel):
    """Parse result response"""
    upload_id: str
    status: str = "parsed"
    files: List[FileMetadata]
    issues: List[ParseIssueResponse]
    summary: Dict[str, int]
    parse_started_at: str
    parse_completed_at: str
    duplicate_count: int = 0


class UploadFromPathRequest(BaseModel):
    source_path: str = Field(..., description="Absolute or relative path to a directory or .zip file")


# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "200")) * 1024 * 1024
UPLOAD_TTL_SECONDS = int(os.getenv("UPLOAD_TTL_SECONDS", "86400"))
ALLOWED_MIME_TYPES = [
    "application/zip",
    "application/x-zip-compressed",
]


# In-memory storage for upload metadata (will be replaced with DB)
# TODO: Replace with Supabase database persistence for production
uploads_store: Dict[str, Dict[str, Any]] = {}


def _parse_created_at_epoch(upload_data: Dict[str, Any]) -> Optional[float]:
    created_at_epoch = upload_data.get("created_at_epoch")
    if isinstance(created_at_epoch, (int, float)):
        return float(created_at_epoch)

    created_at_raw = upload_data.get("created_at")
    if not isinstance(created_at_raw, str):
        return None

    try:
        return datetime.fromisoformat(created_at_raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _delete_upload_file(upload_data: Dict[str, Any]) -> None:
    storage_path_value = upload_data.get("storage_path")
    if not isinstance(storage_path_value, str) or not storage_path_value:
        return

    storage_path = Path(storage_path_value)
    if not storage_path.exists():
        return

    try:
        storage_path.unlink()
    except OSError as exc:
        logger.warning("Failed to delete expired upload file %s: %s", storage_path, exc)


def cleanup_expired_uploads() -> int:
    if UPLOAD_TTL_SECONDS <= 0:
        return 0

    cutoff_epoch = datetime.utcnow().timestamp() - UPLOAD_TTL_SECONDS
    expired_ids: List[str] = []

    for upload_id, upload_data in list(uploads_store.items()):
        created_at_epoch = _parse_created_at_epoch(upload_data)
        if created_at_epoch is None:
            continue
        if created_at_epoch <= cutoff_epoch:
            expired_ids.append(upload_id)

    for upload_id in expired_ids:
        upload_data = uploads_store.pop(upload_id, None)
        if upload_data is None:
            continue
        _delete_upload_file(upload_data)

    if expired_ids:
        logger.info("Cleaned up %d expired uploads", len(expired_ids))

    return len(expired_ids)


def validate_zip_file(file_content: bytes, filename: str) -> tuple[bool, Optional[str]]:
    """
    Validate that uploaded file is a valid ZIP archive
    Returns (is_valid, error_message)
    
    Note: ZIP extraction safety (path traversal prevention) is handled by
    the scanner.parser module during parse operation.
    """
    # Check file extension
    if not filename.lower().endswith('.zip'):
        return False, "File must have .zip extension"
    
    # Check magic bytes (ZIP signature: PK\x03\x04 or PK\x05\x06 for empty ZIP)
    if len(file_content) < 4:
        return False, "File is too small to be a valid ZIP archive"
    
    # ZIP files start with 'PK'
    if not file_content[:2] == b'PK':
        return False, "File does not have valid ZIP signature"
    
    # Use python-magic to verify MIME type
    try:
        mime = magic.from_buffer(file_content, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            return False, f"Invalid MIME type: {mime}, expected ZIP archive"
    except Exception as e:
        return False, f"Failed to detect file type: {str(e)}"
    
    return True, None


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def _validate_source_path(source_path: str) -> Path:
    blocked_prefixes = [
        "/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/boot",
        "/root", "/proc", "/sys", "/dev", "/private/etc", "/private/var",
    ]

    input_path = Path(source_path)
    try:
        if not input_path.is_absolute():
            input_path = Path.cwd() / input_path
        input_str = str(input_path)
    except (OSError, ValueError):
        input_str = source_path

    for blocked in blocked_prefixes:
        if input_str.startswith(blocked) or source_path.startswith(blocked):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "path_not_allowed", "message": f"Access to {blocked} is not allowed"},
            )

    try:
        target = Path(source_path).resolve()
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_path", "message": f"Invalid path: {exc}"},
        )

    resolved_str = str(target)
    for blocked in blocked_prefixes:
        if resolved_str.startswith(blocked):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "path_not_allowed", "message": f"Access to {blocked} is not allowed"},
            )

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "path_not_found", "message": f"Path does not exist: {source_path}"},
        )

    return target


def _store_upload_content(
    *,
    content: bytes,
    filename: str,
    content_type: Optional[str],
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> UploadResponse:
    file_size = len(content)
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "message": f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_UPLOAD_SIZE} bytes)",
                "max_size_bytes": MAX_UPLOAD_SIZE,
            },
        )

    is_valid, error_msg = validate_zip_file(content, filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_format",
                "message": error_msg,
                "expected": ".zip",
            },
        )

    upload_id = f"upl_{uuid.uuid4().hex[:12]}"
    file_hash = compute_file_hash(content)
    upload_path = UPLOAD_DIR / f"{upload_id}.zip"
    upload_path.write_bytes(content)

    created_at = datetime.utcnow()
    merged_metadata: Dict[str, Any] = {
        "original_filename": filename,
        "content_type": content_type,
    }
    if metadata:
        merged_metadata.update(metadata)

    upload_metadata = {
        "upload_id": upload_id,
        "user_id": user_id,
        "status": "stored",
        "filename": filename,
        "size_bytes": file_size,
        "file_hash": file_hash,
        "storage_path": str(upload_path),
        "created_at": created_at.isoformat() + "Z",
        "created_at_epoch": created_at.timestamp(),
        "metadata": merged_metadata,
    }
    uploads_store[upload_id] = upload_metadata

    return UploadResponse(
        upload_id=upload_id,
        status="stored",
        filename=filename,
        size_bytes=file_size,
    )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(..., description="ZIP archive to upload"),
    user_id: str = Depends(verify_auth_token)
):
    """
    Upload a ZIP archive
    
    - Validates file format (extension and magic bytes)
    - Stores file with unique upload_id
    - Returns upload metadata
    - Max size: 200 MB
    - Requires authentication
    """
    try:
        cleanup_expired_uploads()
        filename = file.filename or "upload.zip"
        content = await file.read()
        return _store_upload_content(
            content=content,
            filename=filename,
            content_type=file.content_type,
            user_id=user_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "upload_failed",
                "message": f"Failed to process upload: {str(e)}"
            }
        )


@router.post("/from-path", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_from_path(
    payload: UploadFromPathRequest,
    user_id: str = Depends(verify_auth_token),
):
    try:
        cleanup_expired_uploads()

        source = _validate_source_path(payload.source_path)
        archive_path = ensure_zip(source)
        content = archive_path.read_bytes()

        filename = archive_path.name if archive_path.suffix.lower() == ".zip" else f"{archive_path.name}.zip"
        metadata = {
            "source_path": str(source),
            "source_kind": "directory" if source.is_dir() else "zip",
        }

        return _store_upload_content(
            content=content,
            filename=filename,
            content_type="application/zip",
            user_id=user_id,
            metadata=metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "upload_failed",
                "message": f"Failed to process source path upload: {str(exc)}",
            },
        )


@router.get("/{upload_id}", response_model=UploadStatus)
async def get_upload_status(
    upload_id: str,
    user_id: str = Depends(verify_auth_token)
):
    """
    Get upload status and metadata
    
    Returns stored metadata for the upload to allow polling without filesystem access.
    Only returns uploads owned by the authenticated user.
    """
    cleanup_expired_uploads()

    if upload_id not in uploads_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Upload with ID '{upload_id}' not found"
            }
        )
    
    upload_data = uploads_store[upload_id]
    
    # Verify ownership
    if upload_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Access denied to this upload"
            }
        )
    
    return UploadStatus(
        upload_id=upload_data["upload_id"],
        status=upload_data["status"],
        filename=upload_data["filename"],
        size_bytes=upload_data["size_bytes"],
        created_at=upload_data["created_at"],
        metadata=upload_data.get("metadata")
    )


@router.post("/{upload_id}/parse", response_model=ParseResponse)
async def parse_upload(
    upload_id: str,
    parse_request: Optional[ParseRequest] = Body(default=None),
    user_id: str = Depends(verify_auth_token)
):
    """
    Parse uploaded ZIP archive
    
    - Extracts file metadata, detects languages/frameworks
    - Identifies duplicate files by hash
    - Extracts media metadata if present
    - Detects Git repositories
    - Supports custom scan preferences
    - Returns file list, issues, and summary statistics
    - Requires authentication and upload ownership
    """
    cleanup_expired_uploads()

    # Verify upload exists
    if upload_id not in uploads_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Upload with ID '{upload_id}' not found"
            }
        )
    
    upload_data = uploads_store[upload_id]
    
    # Verify ownership
    if upload_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Access denied to this upload"
            }
        )
    storage_path = Path(upload_data["storage_path"])
    
    if not storage_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "file_missing",
                "message": "Upload file not found on disk"
            }
        )
    
    try:
        if parse_request is None:
            parse_request = ParseRequest(profile_id=None, relevance_only=False, preferences=None)
        parse_started = datetime.utcnow()
        
        # Build scan preferences from request
        preferences = None
        if parse_request.preferences:
            prefs_dict = parse_request.preferences
            preferences = ScanPreferences(
                allowed_extensions=prefs_dict.get("allowed_extensions"),
                excluded_dirs=prefs_dict.get("excluded_dirs"),
                max_file_size_bytes=prefs_dict.get("max_file_size_bytes"),
                follow_symlinks=prefs_dict.get("follow_symlinks")
            )
        
        # Run parse
        parse_result: ParseResult = parse_zip(
            storage_path,
            relevant_only=parse_request.relevance_only,
            preferences=preferences
        )
        
        parse_completed = datetime.utcnow()
        
        # Convert scanner models to API models
        files = []
        file_hashes = {}
        for file_meta in parse_result.files:
            file_dict = {
                "path": file_meta.path,
                "size_bytes": file_meta.size_bytes,
                "mime_type": file_meta.mime_type,
                "created_at": file_meta.created_at.replace(tzinfo=None).isoformat() + "Z",
                "modified_at": file_meta.modified_at.replace(tzinfo=None).isoformat() + "Z",
                "file_hash": file_meta.file_hash
            }
            
            # Add media info if present
            if file_meta.media_info:
                file_dict["media_info"] = {
                    "media_type": file_meta.media_info.get("media_type"),
                    "duration_seconds": file_meta.media_info.get("duration_seconds"),
                    "width": file_meta.media_info.get("width"),
                    "height": file_meta.media_info.get("height"),
                    "format": file_meta.media_info.get("format"),
                }
            
            files.append(FileMetadata(**file_dict))
            
            # Track duplicates by hash
            if file_meta.file_hash:
                if file_meta.file_hash in file_hashes:
                    file_hashes[file_meta.file_hash] += 1
                else:
                    file_hashes[file_meta.file_hash] = 1
        
        # Count duplicates (files with same hash)
        duplicate_count = sum(1 for count in file_hashes.values() if count > 1)
        
        # Convert issues
        issues = [
            ParseIssueResponse(
                path=issue.path,
                code=issue.code,
                message=issue.message
            )
            for issue in parse_result.issues
        ]
        
        # Update upload status
        upload_data["status"] = "parsed"
        upload_data["parse_completed_at"] = parse_completed.isoformat() + "Z"
        upload_data["file_count"] = len(files)
        upload_data["duplicate_count"] = duplicate_count
        
        return ParseResponse(
            upload_id=upload_id,
            status="parsed",
            files=files,
            issues=issues,
            summary=parse_result.summary,
            parse_started_at=parse_started.isoformat() + "Z",
            parse_completed_at=parse_completed.isoformat() + "Z",
            duplicate_count=duplicate_count
        )
        
    except Exception as e:
        logger.exception("parse_upload failed for upload_id=%s", upload_id)
        upload_data["status"] = "parse_failed"
        upload_data["error"] = str(e)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "parse_failed",
                "message": f"Failed to parse upload: {str(e)}"
            }
        )
