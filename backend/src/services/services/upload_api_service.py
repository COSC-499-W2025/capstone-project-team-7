"""
Upload API Service
Provides HTTP client to interact with upload and parse API endpoints
"""

from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from scanner.models import ParseResult, FileMetadata, ParseIssue, ScanPreferences


@dataclass
class UploadResponse:
    """Response from upload endpoint"""
    upload_id: str
    status: str
    filename: str
    size_bytes: int


@dataclass
class ParseResponse:
    """Response from parse endpoint"""
    upload_id: str
    status: str
    files: List[FileMetadata]
    issues: List[ParseIssue]
    summary: Dict[str, int]
    parse_started_at: str
    parse_completed_at: str
    duplicate_count: int


class UploadAPIError(Exception):
    """Base exception for upload API errors"""
    pass


class AuthenticationError(UploadAPIError):
    """Authentication failed"""
    pass


class UploadAPIService:
    """
    Service for interacting with upload and parse API endpoints.
    
    Handles:
    - File uploads to /api/uploads
    - Parse requests to /api/uploads/{upload_id}/parse
    - Authentication via Bearer token
    """
    
    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize API service.
        
        Args:
            base_url: Base URL for API (defaults to http://localhost:8000)
            auth_token: JWT authentication token (can be set later)
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.auth_token = auth_token
    
    def set_auth_token(self, token: str) -> None:
        """Set the authentication token for API requests"""
        self.auth_token = token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including authentication"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def upload_file(self, file_path: Path) -> UploadResponse:
        """
        Upload a ZIP file to the API.
        
        Args:
            file_path: Path to ZIP file to upload
            
        Returns:
            UploadResponse with upload_id and metadata
            
        Raises:
            AuthenticationError: If authentication fails
            UploadAPIError: If upload fails
        """
        if not file_path.exists():
            raise UploadAPIError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == ".zip":
            raise UploadAPIError(f"File must be a ZIP archive: {file_path}")
        
        url = f"{self.base_url}/api/uploads"
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/zip")}
                response = requests.post(
                    url,
                    files=files,
                    headers=self._get_headers(),
                    timeout=300  # 5 minutes for large files
                )
            
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your token.")
            
            if response.status_code == 413:
                raise UploadAPIError("File too large. Maximum size is 200 MB.")
            
            if response.status_code == 400:
                detail = response.json().get("detail", {})
                error_msg = detail.get("message", "Invalid file format")
                raise UploadAPIError(error_msg)
            
            response.raise_for_status()
            data = response.json()
            
            return UploadResponse(
                upload_id=data["upload_id"],
                status=data["status"],
                filename=data["filename"],
                size_bytes=data["size_bytes"]
            )
            
        except requests.RequestException as e:
            raise UploadAPIError(f"Upload request failed: {str(e)}")
    
    def parse_upload(
        self,
        upload_id: str,
        relevant_only: bool = False,
        preferences: Optional[ScanPreferences] = None
    ) -> ParseResponse:
        """
        Parse an uploaded file.
        
        Args:
            upload_id: Upload ID from upload_file()
            relevant_only: Only include relevant files
            preferences: Optional scan preferences
            
        Returns:
            ParseResponse with parsed files and metadata
            
        Raises:
            AuthenticationError: If authentication fails
            UploadAPIError: If parse fails
        """
        url = f"{self.base_url}/api/uploads/{upload_id}/parse"
        
        # Build request body
        request_body: Dict[str, Any] = {
            "relevance_only": relevant_only
        }
        
        if preferences:
            prefs_dict: Dict[str, Any] = {}
            if preferences.allowed_extensions:
                prefs_dict["allowed_extensions"] = list(preferences.allowed_extensions)
            if preferences.excluded_dirs:
                prefs_dict["excluded_dirs"] = list(preferences.excluded_dirs)
            if preferences.max_file_size_bytes:
                prefs_dict["max_file_size_bytes"] = preferences.max_file_size_bytes
            if preferences.follow_symlinks is not None:
                prefs_dict["follow_symlinks"] = preferences.follow_symlinks
            
            if prefs_dict:
                request_body["preferences"] = prefs_dict
        
        try:
            response = requests.post(
                url,
                json=request_body,
                headers=self._get_headers(),
                timeout=600  # 10 minutes for large archives
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your token.")
            
            if response.status_code == 404:
                raise UploadAPIError(f"Upload not found: {upload_id}")
            
            if response.status_code == 403:
                raise UploadAPIError("Access denied to this upload")
            
            response.raise_for_status()
            data = response.json()
            
            # Convert API response to domain models
            files = []
            for file_data in data["files"]:
                from datetime import datetime
                file_meta = FileMetadata(
                    path=file_data["path"],
                    size_bytes=file_data["size_bytes"],
                    mime_type=file_data["mime_type"],
                    created_at=datetime.fromisoformat(file_data["created_at"].replace("Z", "+00:00")),
                    modified_at=datetime.fromisoformat(file_data["modified_at"].replace("Z", "+00:00")),
                    file_hash=file_data.get("file_hash")
                )
                
                # Add media info if present
                if "media_info" in file_data and file_data["media_info"]:
                    from scanner.media_types import ImageMetadata, AudioMetadata, VideoMetadata
                    media_data = file_data["media_info"]
                    media_type = media_data.get("media_type", "")
                    
                    # Construct the appropriate media metadata based on type
                    if "image" in media_type.lower():
                        meta: ImageMetadata = {}
                        if media_data.get("width"):
                            meta["width"] = media_data["width"]
                        if media_data.get("height"):
                            meta["height"] = media_data["height"]
                        if media_data.get("format"):
                            meta["format"] = media_data["format"]
                        file_meta.media_info = meta
                    elif "audio" in media_type.lower():
                        meta_audio: AudioMetadata = {}
                        if media_data.get("duration_seconds"):
                            meta_audio["duration_seconds"] = media_data["duration_seconds"]
                        file_meta.media_info = meta_audio
                    elif "video" in media_type.lower():
                        meta_video: VideoMetadata = {}
                        if media_data.get("duration_seconds"):
                            meta_video["duration_seconds"] = media_data["duration_seconds"]
                        file_meta.media_info = meta_video
                
                files.append(file_meta)
            
            issues = []
            for issue_data in data["issues"]:
                issues.append(ParseIssue(
                    path=issue_data["path"],
                    code=issue_data["code"],
                    message=issue_data["message"]
                ))
            
            return ParseResponse(
                upload_id=data["upload_id"],
                status=data["status"],
                files=files,
                issues=issues,
                summary=data["summary"],
                parse_started_at=data["parse_started_at"],
                parse_completed_at=data["parse_completed_at"],
                duplicate_count=data["duplicate_count"]
            )
            
        except requests.RequestException as e:
            raise UploadAPIError(f"Parse request failed: {str(e)}")
    
    def upload_and_parse(
        self,
        file_path: Path,
        relevant_only: bool = False,
        preferences: Optional[ScanPreferences] = None
    ) -> tuple[UploadResponse, ParseResponse]:
        """
        Convenience method to upload and parse in one call.
        
        Args:
            file_path: Path to ZIP file
            relevant_only: Only include relevant files
            preferences: Optional scan preferences
            
        Returns:
            Tuple of (UploadResponse, ParseResponse)
        """
        upload_resp = self.upload_file(file_path)
        parse_resp = self.parse_upload(upload_resp.upload_id, relevant_only, preferences)
        return upload_resp, parse_resp
