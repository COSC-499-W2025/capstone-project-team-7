"""User Resume Service - manages full resume documents stored in Supabase."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

try:
    from supabase.client import Client, create_client as _create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore[assignment]
    _create_client = None

from services.services.supabase_keys import (
    apply_client_access_token,
    create_postgrest_client,
    is_jwt_like,
    resolve_supabase_api_key,
)

logger = logging.getLogger(__name__)


class UserResumeServiceError(Exception):
    """Raised when user resume operations fail."""


class UserResumeService:
    """Service for managing user resume documents in Supabase."""

    VALID_TEMPLATES = {"jake", "classic", "modern", "minimal", "custom"}
    _SKILL_CATEGORIES: Dict[str, Dict[str, str]] = {
        "languages": {
            "python": "Python",
            "typescript": "TypeScript",
            "javascript": "JavaScript",
            "java": "Java",
            "c#": "C#",
            "c++": "C++",
            "go": "Go",
            "rust": "Rust",
            "sql": "SQL",
            "bash": "Bash",
            "html": "HTML",
            "css": "CSS",
        },
        "frameworks": {
            "react": "React",
            "next.js": "Next.js",
            "nextjs": "Next.js",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "node.js": "Node.js",
            "nodejs": "Node.js",
            "express": "Express",
            "spring": "Spring",
        },
        "developer_tools": {
            "git": "Git",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "aws": "AWS",
            "gcp": "GCP",
            "azure": "Azure",
            "supabase": "Supabase",
            "postgres": "Postgres",
            "postgresql": "Postgres",
            "sqlite": "SQLite",
            "linux": "Linux",
        },
        "libraries": {
            "numpy": "NumPy",
            "pandas": "Pandas",
            "matplotlib": "Matplotlib",
            "scikit-learn": "Scikit-learn",
            "tensorflow": "TensorFlow",
            "pytorch": "PyTorch",
            "zod": "Zod",
            "tailwind": "Tailwind",
            "tailwindcss": "Tailwind",
        },
    }

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ) -> None:
        if not SUPABASE_AVAILABLE:
            raise UserResumeServiceError("Supabase client not available. Install supabase-py.")

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = resolve_supabase_api_key(
            supabase_key,
            prefer_anon_for_python_client=True,
        )

        if not self.supabase_url or not self.supabase_key:
            raise UserResumeServiceError("Supabase credentials not configured.")

        self._access_token: Optional[str] = None
        self.client: Any = None
        self._requires_user_token_client = False

        # supabase-py ships loose/dynamic typing for create_client and we also
        # set _create_client = None in the ImportError path above. Casting to
        # Any lets us validate at runtime (None-check) and still call it safely.
        client_factory = cast(Any, _create_client)
        if client_factory is None:
            raise UserResumeServiceError("Supabase client not available. Install supabase-py.")

        try:
            self.client = client_factory(cast(str, self.supabase_url), cast(str, self.supabase_key))
        except Exception as exc:
            if (self.supabase_key or "").startswith("sb_publishable_"):
                self._requires_user_token_client = True
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                    self._requires_user_token_client = False
                except Exception:
                    self.client = None
            else:
                raise UserResumeServiceError(f"Failed to initialize Supabase client: {exc}") from exc

    def apply_access_token(self, token: Optional[str]) -> None:
        """Apply user's access token for RLS-scoped queries."""
        self._access_token = token

        if token and not is_jwt_like(token) and self.client is not None:
            return

        if self.client is None and token and is_jwt_like(token):
            try:
                client_factory = cast(Any, _create_client)
                if client_factory is None:
                    raise UserResumeServiceError("Supabase client not available. Install supabase-py.")
                self.client = client_factory(cast(str, self.supabase_url), token)
            except Exception as exc:
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                except Exception:
                    raise UserResumeServiceError(
                        f"Failed to initialize user-scoped Supabase client: {exc}"
                    ) from exc

        if self.client is None and token and not is_jwt_like(token) and self._requires_user_token_client:
            raise UserResumeServiceError("JWT access token is required for Supabase operations.")

        if self.client is None and self._requires_user_token_client:
            raise UserResumeServiceError("Authenticated user token is required for Supabase operations.")

        apply_client_access_token(self.client, token)

    def _handle_response(self, response: Any) -> List[Dict[str, Any]]:
        """Extract data from Supabase response."""
        if response is not None:
            return response
        raise UserResumeServiceError("Supabase operation returned None")

    def list_resumes(
        self, user_id: str, *, limit: int = 20, offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List resumes for a user with pagination.
        
        Returns:
            Tuple of (records, total_count) for the requested page.
        """
        if not user_id:
            return [], 0

        try:
            # Get total count first
            count_response = (
                self.client.table("user_resumes")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            total = count_response.count if hasattr(count_response, 'count') and count_response.count is not None else 0

            # Get paginated records
            response = (
                self.client.table("user_resumes")
                .select("id, name, template, is_latex_mode, metadata, created_at, updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            records = self._handle_response(response.data)
            return records, total
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to list resumes: {exc}") from exc

    def get_resume(self, user_id: str, resume_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single resume with full content."""
        if not user_id or not resume_id:
            return None

        try:
            response = (
                self.client.table("user_resumes")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .limit(1)
                .execute()
            )
            data = self._handle_response(response.data)
            return data[0] if data else None
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to fetch resume: {exc}") from exc

    def create_resume(
        self,
        user_id: str,
        *,
        name: str = "Untitled Resume",
        template: str = "jake",
        latex_content: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        is_latex_mode: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new resume document."""
        if not user_id:
            raise UserResumeServiceError("User ID is required to create a resume.")

        if template not in self.VALID_TEMPLATES:
            raise UserResumeServiceError(f"Invalid template: {template}. Must be one of {self.VALID_TEMPLATES}")

        payload = {
            "user_id": user_id,
            "name": name,
            "template": template,
            "latex_content": latex_content,
            "structured_data": structured_data or {},
            "is_latex_mode": is_latex_mode,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table("user_resumes").insert(payload).execute()
            data = self._handle_response(response.data)
            if not data:
                raise UserResumeServiceError("Supabase did not return created resume.")
            return data[0]
        except UserResumeServiceError:
            raise
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to create resume: {exc}") from exc

    def update_resume(
        self,
        user_id: str,
        resume_id: str,
        *,
        name: Optional[str] = None,
        template: Optional[str] = None,
        latex_content: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        is_latex_mode: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing resume."""
        if not user_id or not resume_id:
            return None

        # Check resume exists
        existing = self.get_resume(user_id, resume_id)
        if not existing:
            return None

        if template is not None and template not in self.VALID_TEMPLATES:
            raise UserResumeServiceError(f"Invalid template: {template}. Must be one of {self.VALID_TEMPLATES}")

        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if template is not None:
            payload["template"] = template
        if latex_content is not None:
            payload["latex_content"] = latex_content
        if structured_data is not None:
            payload["structured_data"] = structured_data
        if is_latex_mode is not None:
            payload["is_latex_mode"] = is_latex_mode
        if metadata is not None:
            # Merge with existing metadata
            existing_metadata = existing.get("metadata") or {}
            payload["metadata"] = {**existing_metadata, **metadata}

        if not payload:
            return existing  # Nothing to update

        try:
            response = (
                self.client.table("user_resumes")
                .update(payload)
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
            data = self._handle_response(response.data)
            return data[0] if data else None
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to update resume: {exc}") from exc

    def delete_resume(self, user_id: str, resume_id: str) -> bool:
        """Delete a resume."""
        if not user_id or not resume_id:
            return False

        try:
            response = (
                self.client.table("user_resumes")
                .delete()
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
            data = self._handle_response(response.data)
            return bool(data)
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to delete resume: {exc}") from exc

    def duplicate_resume(self, user_id: str, resume_id: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        """Duplicate an existing resume."""
        existing = self.get_resume(user_id, resume_id)
        if not existing:
            raise UserResumeServiceError("Resume not found.")

        return self.create_resume(
            user_id,
            name=new_name or f"{existing.get('name', 'Resume')} (Copy)",
            template=existing.get("template", "jake"),
            latex_content=existing.get("latex_content"),
            structured_data=existing.get("structured_data"),
            is_latex_mode=existing.get("is_latex_mode", True),
            metadata={"duplicated_from": resume_id},
        )

    def add_resume_items_to_resume(
        self,
        user_id: str,
        resume_id: str,
        *,
        item_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        if not user_id or not resume_id:
            return None

        normalized_ids = [item_id for item_id in item_ids if item_id]
        if not normalized_ids:
            raise UserResumeServiceError("item_ids must include at least one resume item id.")

        existing = self.get_resume(user_id, resume_id)
        if not existing:
            return None

        try:
            response = (
                self.client.table("resume_items")
                .select("id, project_name, start_date, end_date, content, bullets, metadata")
                .eq("user_id", user_id)
                .in_("id", normalized_ids)
                .execute()
            )
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to fetch resume items: {exc}") from exc

        fetched_items = self._handle_response(response.data)
        items_by_id = {str(item.get("id")): item for item in fetched_items}

        structured_data = existing.get("structured_data") or {}
        if not isinstance(structured_data, dict):
            structured_data = {}

        current_projects = structured_data.get("projects")
        projects: List[Dict[str, Any]] = list(current_projects) if isinstance(current_projects, list) else []
        existing_item_links = {
            str(project.get("resume_item_id"))
            for project in projects
            if isinstance(project, dict) and project.get("resume_item_id") is not None
        }

        added = 0
        for item_id in normalized_ids:
            if item_id in existing_item_links:
                continue

            item = items_by_id.get(item_id)
            if not item:
                continue

            project_name = str(item.get("project_name") or "").strip() or "Untitled Project"
            bullets = self._extract_item_bullets(item)
            metadata_value = item.get("metadata")
            metadata: Dict[str, Any] = {}
            if isinstance(metadata_value, dict):
                metadata = {str(key): value for key, value in metadata_value.items()}
            technologies = self._extract_technologies_string(item, metadata)

            project_entry: Dict[str, Any] = {
                "id": str(uuid4()),
                "name": project_name,
                "start_date": item.get("start_date"),
                "end_date": item.get("end_date"),
                "bullets": bullets,
                "resume_item_id": item_id,
            }
            if technologies:
                project_entry["technologies"] = technologies

            projects.append(project_entry)
            existing_item_links.add(item_id)
            added += 1

        structured_data["projects"] = projects
        return self.update_resume(user_id, resume_id, structured_data=structured_data, metadata={"last_added_items": added})

    def detect_skills_from_resume_projects(self, user_id: str, resume_id: str) -> Optional[Dict[str, Any]]:
        if not user_id or not resume_id:
            return None

        existing = self.get_resume(user_id, resume_id)
        if not existing:
            return None

        structured_data = existing.get("structured_data") or {}
        if not isinstance(structured_data, dict):
            structured_data = {}

        projects = structured_data.get("projects")
        project_list: List[Dict[str, Any]] = [p for p in projects if isinstance(p, dict)] if isinstance(projects, list) else []
        detected = self._detect_skills_from_projects(project_list)

        all_items_detected = self._detect_skills_from_all_user_items(user_id)
        
        for category in ["languages", "frameworks", "developer_tools", "libraries"]:
            detected[category] = self._merge_unique_case_insensitive(
                detected.get(category, []), 
                all_items_detected.get(category, [])
            )

        existing_skills_raw = structured_data.get("skills")
        existing_skills = existing_skills_raw if isinstance(existing_skills_raw, dict) else {}

        merged_skills: Dict[str, List[str]] = {}
        for category in ["languages", "frameworks", "developer_tools", "libraries"]:
            current_values = existing_skills.get(category)
            current_list = [str(v) for v in current_values if isinstance(v, str)] if isinstance(current_values, list) else []
            merged_skills[category] = self._merge_unique_case_insensitive(current_list, detected.get(category, []))

        structured_data["skills"] = merged_skills
        return self.update_resume(user_id, resume_id, structured_data=structured_data, metadata={"auto_detected_skills": True})

    def _detect_skills_from_all_user_items(self, user_id: str) -> Dict[str, List[str]]:
        detected: Dict[str, List[str]] = {
            "languages": [],
            "frameworks": [],
            "developer_tools": [],
            "libraries": [],
        }
        
        if not self.client:
            return detected
            
        try:
            response = (
                self.client.table("resume_items")
                .select("metadata, bullets, content")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            logger.warning(f"Failed to fetch user resume items for skill detection: {exc}")
            return detected
            
        if not response.data:
            return detected
            
        for item in response.data:
            metadata = item.get("metadata") or {}
            if isinstance(metadata, dict):
                languages = metadata.get("languages")
                if isinstance(languages, list):
                    for lang in languages:
                        if isinstance(lang, dict):
                            lang_name = lang.get("language")
                            if lang_name:
                                self._add_skill_token(str(lang_name), detected)
                        elif isinstance(lang, str):
                            self._add_skill_token(lang, detected)
                
                technologies = metadata.get("technologies")
                if isinstance(technologies, str):
                    for token in re.split(r"[,/|;]", technologies):
                        self._add_skill_token(token, detected)
                        
                integrations = metadata.get("integration_signals")
                if isinstance(integrations, list):
                    for integration in integrations:
                        if isinstance(integration, str):
                            self._add_skill_token(integration, detected)
            
            bullets = item.get("bullets")
            if isinstance(bullets, list):
                for bullet in bullets:
                    if isinstance(bullet, str):
                        for token in re.split(r"[^a-zA-Z0-9.+#-]+", bullet):
                            self._add_skill_token(token, detected)
            
            content = item.get("content")
            if isinstance(content, str):
                for token in re.split(r"[^a-zA-Z0-9.+#-]+", content):
                    self._add_skill_token(token, detected)
        
        return detected

    def _extract_item_bullets(self, item: Dict[str, Any]) -> List[str]:
        bullets = item.get("bullets")
        if isinstance(bullets, list):
            return [str(bullet).strip() for bullet in bullets if str(bullet).strip()]

        content = item.get("content")
        if not isinstance(content, str):
            return []

        extracted: List[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                candidate = stripped[2:].strip()
                if candidate:
                    extracted.append(candidate)
        return extracted

    def _extract_technologies_string(self, item: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        direct = metadata.get("technologies")
        if isinstance(direct, str):
            return direct.strip()

        languages = metadata.get("languages")
        if isinstance(languages, list):
            names = [str(value).strip() for value in languages if str(value).strip()]
            return ", ".join(names[:8])

        return ""

    def _detect_skills_from_projects(self, projects: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        detected: Dict[str, List[str]] = {
            "languages": [],
            "frameworks": [],
            "developer_tools": [],
            "libraries": [],
        }

        for project in projects:
            technologies = project.get("technologies")
            if isinstance(technologies, str):
                for token in re.split(r"[,/|;]", technologies):
                    self._add_skill_token(token, detected)

            bullets = project.get("bullets")
            if isinstance(bullets, list):
                for bullet in bullets:
                    if isinstance(bullet, str):
                        for token in re.split(r"[^a-zA-Z0-9.+#-]+", bullet):
                            self._add_skill_token(token, detected)

        return detected

    def _add_skill_token(self, token: str, detected: Dict[str, List[str]]) -> None:
        normalized = token.strip().lower()
        if not normalized:
            return

        for category, keyword_map in self._SKILL_CATEGORIES.items():
            match = keyword_map.get(normalized)
            if match and match not in detected[category]:
                detected[category].append(match)

    def _merge_unique_case_insensitive(self, existing: List[str], incoming: List[str]) -> List[str]:
        merged: List[str] = []
        seen_lower: set[str] = set()

        for value in [*existing, *incoming]:
            cleaned = value.strip()
            if not cleaned:
                continue
            lower = cleaned.lower()
            if lower in seen_lower:
                continue
            seen_lower.add(lower)
            merged.append(cleaned)

        return merged

    def render_pdf_bytes(
        self,
        user_id: str,
        resume_id: str,
        *,
        latex_content: Optional[str] = None,
    ) -> bytes:
        if not user_id or not resume_id:
            raise UserResumeServiceError("Missing user or resume identifier.")

        if latex_content is None:
            record = self.get_resume(user_id, resume_id)
            if not record:
                raise UserResumeServiceError("Resume not found.")
            latex_content = record.get("latex_content")

        if not isinstance(latex_content, str) or not latex_content.strip():
            raise UserResumeServiceError("No LaTeX content available for PDF export.")

        if shutil.which("pdflatex") is None:
            raise UserResumeServiceError("pdflatex is not installed on the server.")

        try:
            with tempfile.TemporaryDirectory(prefix="resume_pdf_") as tmp_dir:
                workdir = Path(tmp_dir)
                tex_path = workdir / "resume.tex"
                tex_path.write_text(latex_content, encoding="utf-8")

                command = [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory",
                    str(workdir),
                    str(tex_path),
                ]
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                if process.returncode != 0:
                    error_message = (process.stderr or process.stdout or "LaTeX compilation failed").strip()
                    raise UserResumeServiceError(f"PDF compilation failed: {error_message[-1000:]}")

                pdf_path = workdir / "resume.pdf"
                if not pdf_path.exists():
                    raise UserResumeServiceError("PDF generation failed: output file not found.")

                return pdf_path.read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise UserResumeServiceError("PDF compilation timed out.") from exc
        except OSError as exc:
            raise UserResumeServiceError(f"PDF generation failed: {exc}") from exc
