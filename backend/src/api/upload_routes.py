"""
Upload and Parse API routes
Implements /api/uploads endpoints per api-plan.md
"""

import logging
import os
import threading
import uuid
import hashlib
import magic
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, status, Body, Header, Depends
from pydantic import BaseModel, Field

from api.security import limiter, validate_storage_path

from scanner.parser import parse_zip
from scanner.models import ParseResult, ScanPreferences, FileMetadata as ScanFileMetadata, ParseIssue as ScanParseIssue
from api.request_context import set_request_access_token

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


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

    try:
        import jwt

        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


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
uploads_store_lock = threading.Lock()


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
    expired_entries: List[Dict[str, Any]] = []

    with uploads_store_lock:
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
            expired_entries.append(upload_data)

    for upload_data in expired_entries:
        _delete_upload_file(upload_data)

    if expired_entries:
        logger.info("Cleaned up %d expired uploads", len(expired_entries))

    return len(expired_entries)


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


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
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
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate size
        if file_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "file_too_large",
                    "message": f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_UPLOAD_SIZE} bytes)",
                    "max_size_bytes": MAX_UPLOAD_SIZE
                }
            )
        
        # Validate ZIP format
        is_valid, error_msg = validate_zip_file(content, filename)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_format",
                    "message": error_msg,
                    "expected": ".zip"
                }
            )
        
        # Generate unique upload ID
        upload_id = f"upl_{uuid.uuid4().hex[:12]}"
        
        # Compute file hash for deduplication
        file_hash = compute_file_hash(content)
        
        # Save file to disk (validated against traversal)
        safe_name = f"{upload_id}.zip"
        upload_path = validate_storage_path(safe_name, UPLOAD_DIR)
        upload_path.write_bytes(content)
        
        # Store metadata
        created_at = datetime.utcnow()
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
            "metadata": {
                "original_filename": filename,
                "content_type": file.content_type,
            }
        }
        
        with uploads_store_lock:
            uploads_store[upload_id] = upload_metadata
        
        return UploadResponse(
            upload_id=upload_id,
            status="stored",
            filename=filename,
            size_bytes=file_size
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
    with uploads_store_lock:
        upload_data = uploads_store.get(upload_id)

    if upload_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Upload with ID '{upload_id}' not found"
            }
        )
    
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
    with uploads_store_lock:
        upload_data = uploads_store.get(upload_id)

    # Verify upload exists
    if upload_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Upload with ID '{upload_id}' not found"
            }
        )
    
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
        with uploads_store_lock:
            current_upload_data = uploads_store.get(upload_id)
            if current_upload_data is not None:
                current_upload_data["status"] = "parsed"
                current_upload_data["parse_completed_at"] = parse_completed.isoformat() + "Z"
                current_upload_data["file_count"] = len(files)
                current_upload_data["duplicate_count"] = duplicate_count
        
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
        with uploads_store_lock:
            current_upload_data = uploads_store.get(upload_id)
            if current_upload_data is not None:
                current_upload_data["status"] = "parse_failed"
                current_upload_data["error"] = str(e)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "parse_failed",
                "message": f"Failed to parse upload: {str(e)}"
            }
        )
