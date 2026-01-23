from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, PlainTextResponse

try:
    from backend.src.cli.services.resume_generation_service import ResumeGenerationService
except Exception:
    from cli.services.resume_generation_service import ResumeGenerationService

router = APIRouter()
logger = logging.getLogger(__name__)


class ResumeHeader(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class ResumeItemPayload(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    summary: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)


class OnePageRequest(BaseModel):
    header: ResumeHeader
    items: List[ResumeItemPayload] = Field(default_factory=list)
    compile_pdf: bool = True


@router.post("/api/resume/generate")
def generate_onepage_resume(payload: OnePageRequest):
    service = ResumeGenerationService()
    # Prepare header and item dicts
    header = payload.header.dict()
    items: List[Dict[str, Any]] = [it.dict() for it in payload.items]

    tex = service.build_onepage_tex(header=header, items=items)
    if payload.compile_pdf:
        pdf_path = service.compile_tex_to_pdf(tex, filename_root=f"onepage_{uuid.uuid4().hex}")
        if pdf_path:
            return FileResponse(pdf_path, media_type="application/pdf", filename="resume.pdf")
        else:
            # Fall back to returning .tex source
            return PlainTextResponse(tex, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=resume.tex"})
    return PlainTextResponse(tex, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=resume.tex"})
*** End Patch