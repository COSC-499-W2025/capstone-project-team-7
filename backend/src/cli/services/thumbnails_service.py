"""Service for managing project thumbnails in Supabase storage."""

import os
import uuid
import io
from typing import Optional, Tuple
from PIL import Image


class ThumbnailsService:
    """Service for uploading and managing project thumbnails."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize the thumbnails service.
        
        Args:
            supabase_url: Supabase project URL (defaults to env SUPABASE_URL)
            supabase_key: Supabase service role key (defaults to env SUPABASE_KEY)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.bucket_name = "thumbnails"
        
    def upload_thumbnail(self, image_path: str, project_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Upload an image as a project thumbnail to Supabase storage.
        
        Args:
            image_path: Path to the local image file
            project_id: ID of the project to associate the thumbnail with
            
        Returns:
            Tuple of (public_url, error_message). If successful, public_url is set and error_message is None.
            If failed, public_url is None and error_message contains the error.
        """
        try:
            from supabase import create_client
            
            if not self.supabase_url or not self.supabase_key:
                error = "Missing SUPABASE_URL or SUPABASE_KEY in environment"
                print(f"ERROR: {error}")
                return None, error
            
            print(f"Starting upload for project {project_id}...")
            print(f"Connecting to Supabase: {self.supabase_url}")
            
            supabase = create_client(self.supabase_url, self.supabase_key)
            
            # Convert image to JPG format
            file_name = f"public/{project_id}_{uuid.uuid4().hex[:8]}.jpg"
            jpg_data = self._convert_image_to_jpg(image_path)
            
            if jpg_data is None:
                return None, "Failed to convert image to JPG format"
            
            print(f"Converted to JPG, size: {len(jpg_data)} bytes")
            
            # Upload to Supabase storage
            print(f"Uploading to bucket '{self.bucket_name}' as '{file_name}'...")
            file_options = {"content-type": "image/jpg", "upsert": "false"}
            result = supabase.storage.from_(self.bucket_name).upload(
                path=file_name,
                file=jpg_data,
                file_options=file_options
            )
            print(f"Upload result: {result}")
            
            # Get the public URL
            public_url = self._get_public_url(supabase, file_name)
            print(f"Final public URL: {public_url}")
            
            return public_url, None
            
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"Thumbnail upload error: {error}")
            import traceback
            traceback.print_exc()
            return None, error
    
    def _convert_image_to_jpg(self, image_path: str) -> Optional[bytes]:
        """Convert an image file to JPG format.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            JPG image data as bytes, or None if conversion failed
        """
        try:
            print(f"Reading and converting file: {image_path}")
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                # Convert RGBA/LA/P to RGB
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPG to bytes
            jpg_buffer = io.BytesIO()
            img.save(jpg_buffer, format='JPEG', quality=85)
            return jpg_buffer.getvalue()
            
        except Exception as e:
            print(f"Error converting image: {e}")
            return None
    
    def _get_public_url(self, supabase, file_name: str) -> str:
        """Get the public URL for an uploaded file.
        
        Args:
            supabase: Supabase client instance
            file_name: Name/path of the file in storage
            
        Returns:
            Public URL for the file
        """
        try:
            public_url_response = supabase.storage.from_(self.bucket_name).get_public_url(file_name)
            print(f"Public URL response: {public_url_response}")
            return public_url_response
        except Exception as url_exc:
            print(f"Error getting public URL: {url_exc}")
            # Fallback to manual construction with URL encoding
            from urllib.parse import quote
            encoded_bucket = quote(self.bucket_name)
            encoded_file = quote(file_name)
            return f"{self.supabase_url}/storage/v1/object/public/{encoded_bucket}/{encoded_file}"
    
    def update_project_thumbnail_url(self, project_id: str, thumbnail_url: str) -> Optional[str]:
        """Update a project's thumbnail_url in the database.
        
        Args:
            project_id: ID of the project to update
            thumbnail_url: Public URL of the uploaded thumbnail
            
        Returns:
            Error message if failed, None if successful
        """
        try:
            from supabase import create_client
            
            if not self.supabase_url or not self.supabase_key:
                error = "Missing SUPABASE_URL or SUPABASE_KEY"
                print(f"ERROR: {error}")
                return error
            
            print(f"Updating database for project {project_id} with URL: {thumbnail_url}")
            
            supabase = create_client(self.supabase_url, self.supabase_key)
            
            # Update the projects table
            print(f"Executing update query...")
            result = supabase.table("projects").update({
                "thumbnail_url": thumbnail_url
            }).eq("id", project_id).execute()
            
            print(f"Database update result: {result}")
            return None
            
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"Database update error: {error}")
            import traceback
            traceback.print_exc()
            return error
