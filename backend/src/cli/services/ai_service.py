from __future__ import annotations

from dataclasses import dataclass
import logging
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
import difflib
from ...scanner.models import ParseResult
from ...scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

class AIDependencyError(RuntimeError):
    """Raised when optional AI dependencies are missing."""


class InvalidAPIKeyError(RuntimeError):
    """Raised when the provided API key is invalid."""


class AIProviderError(RuntimeError):
    """Raised when the AI provider returns an error."""


_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class AIClientConfig:
    temperature: float
    max_tokens: int


def _validate_and_resolve_path(
    file_path: str, 
    base_path: Path, 
    output_base: Path
) -> tuple[Path, Path]:
    """
    Validate and resolve a file path, handling archive prefixes.
    
    Returns:
        Tuple of (output_path, read_path) - both validated and resolved
    
    Raises:
        ValueError: If path is invalid or escapes directories
    """
    # 1. Block absolute paths
    if Path(file_path).is_absolute():
        raise ValueError(f"Absolute paths not allowed: {file_path}")
    
    # 2. Convert to Path
    path_obj = Path(file_path)
    
    # 3. Block path traversal attempts
    if '..' in path_obj.parts:
        raise ValueError(f"Path traversal (..) not allowed: {file_path}")
    
    # 4. Try to find the file (handles archive prefix stripping)
    full_read_path = base_path / path_obj
    clean_path = path_obj  # Path to use for output structure
    
    # ✅ If file doesn't exist, try stripping first component (archive prefix)
    if not full_read_path.exists() and len(path_obj.parts) > 1:
        stripped_path = Path(*path_obj.parts[1:])
        candidate_path = base_path / stripped_path
        
        if candidate_path.exists():
            # Use the stripped path for both reading and output structure
            full_read_path = candidate_path
            clean_path = stripped_path
    
    # 5. Verify read path stays within base_path (security check)
    try:
        full_read_path.resolve().relative_to(base_path.resolve())
    except ValueError:
        raise ValueError(f"Path escapes repository: {file_path}")
    
    # 6. Create output path PRESERVING directory structure
    output_file = output_base / clean_path
    
    # 7. Verify output stays within output_base (security check)
    try:
        output_file.resolve().relative_to(output_base.resolve())
    except ValueError:
        raise ValueError(f"Output path escapes output directory: {clean_path}")
    
    return output_file, full_read_path

class AIService:
    """Utility helpers around the LLM client lifecycle and formatting."""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    def verify_client(
        self,
        api_key: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> tuple[Any, AIClientConfig]:
        try:
            from ...analyzer.llm.client import LLMClient, InvalidAPIKeyError, LLMError
        except Exception as exc:  # pragma: no cover - optional dependency missing
            raise AIDependencyError(str(exc)) from exc

        if not api_key:
            raise InvalidAPIKeyError("API key required.")

        def _create_client() -> LLMClient:
            client = LLMClient(
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            client.verify_api_key()
            return client

        try:
            client = _create_client()
        except InvalidAPIKeyError:
            raise
        except LLMError as exc:
            raise AIProviderError(str(exc)) from exc
        except Exception as exc:
            raise AIProviderError(f"Failed to verify API key: {exc}") from exc

        config = client.get_config()
        client_config = AIClientConfig(
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )
        return client, client_config

    def execute_analysis(
        self,
        client: Any,
        parse_result,
        *,
        languages: Sequence[Dict[str, Any]],
        target_path: Optional[str],
        archive_path: Optional[str],
        git_repos: Sequence[Any],
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
       
        
        if client is None or parse_result is None:
            self.logger.error("AI analysis prerequisites missing - client or parse_result is None")
            raise RuntimeError("AI analysis prerequisites missing.")

        if progress_callback:
            progress_callback("Preparing analysis data…")

        # Use target_path for reading files if available (actual directory)
        # Only fall back to archive_path if no target exists
        scan_path = target_path or archive_path or ""
        read_base_path = target_path if target_path else archive_path
        
        files = parse_result.files or []
        
        # Strip archive prefix from file paths if using target_path
        # Archive paths look like: "capstone-project-team-7/backend/src/main.py"
        # We need to strip the first component to get: "backend/src/main.py"
        relevant_files = []
        for meta in files:
            file_path = meta.path
            
            # If we're using target_path, strip the archive directory prefix
            if target_path and '/' in file_path:
                # Remove the first path component (archive name)
                path_parts = file_path.split('/', 1)
                if len(path_parts) > 1:
                    file_path = path_parts[1]
            
            relevant_files.append({
                "path": file_path,
                "size": meta.size_bytes,
                "mime_type": meta.mime_type,
                "media_info": getattr(meta, "media_info", None),
            })
        
        # Ensure on-disk media files are included even if parser skipped them
        relevant_files = self._ensure_media_candidates(target_path, relevant_files)
        
        media_exts = set(AUDIO_EXTENSIONS + IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)
        media_candidates = [
            f for f in relevant_files
            if f.get("media_info")
            or (f.get("mime_type") or "").startswith(("audio/", "video/", "image/"))
            or Path(f.get("path", "")).suffix.lower() in media_exts
        ]
        include_media = bool(media_candidates)

        self.logger.info(f"[AI Service] Total files: {len(files)}, Relevant files: {len(relevant_files)}")
        self.logger.info(f"[AI Service] Media candidates: {len(media_candidates)}, include_media={include_media}")
        self.logger.info(f"[AI Service] Scan path: {scan_path}")
        self.logger.info(f"[AI Service] Read base path: {read_base_path}")
        self.logger.info(f"[AI Service] Git repos: {git_repos}")
        
        scan_summary = {
            "total_files": len(files),
            "total_size_bytes": sum(meta.size_bytes for meta in files),
            "language_breakdown": list(languages),
            "scan_path": scan_path,
        }
        project_dirs = [str(path) for path in git_repos] if git_repos else None

        if progress_callback:
            progress_callback(f"Analyzing {len(relevant_files)} files…")

        try:
            self.logger.info(f"[AI Service] Calling client.summarize_scan_with_ai with {len(relevant_files)} files")
            result = client.summarize_scan_with_ai(
                scan_summary=scan_summary,
                relevant_files=relevant_files,
                scan_base_path=read_base_path,
                project_dirs=project_dirs,
                progress_callback=progress_callback,
                include_media=include_media,
            )
            self.logger.info(f"[AI Service] Analysis complete, result keys: {list(result.keys()) if result else 'None'}")
            return result
        except Exception as exc:
            self.logger.error(f"[AI Service] Error during analysis: {exc}")
            raise AIProviderError(str(exc)) from exc

    def _ensure_media_candidates(self, base_dir: Optional[str], existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Augment relevant_files with media present on disk (guarded)."""
        if not base_dir:
            return existing
        try:
            from pathlib import Path
            import mimetypes
            from ...scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
            base = Path(base_dir)
            if not base.exists():
                return existing
            seen = {item["path"] for item in existing}
            media_exts = set(AUDIO_EXTENSIONS + IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)
            added = 0
            for path in base.rglob("*"):
                if added >= 30:
                    break
                if not path.is_file():
                    continue
                if path.suffix.lower() not in media_exts:
                    continue
                rel_path = str(path.relative_to(base))
                if rel_path in seen:
                    continue
                existing.append({
                    "path": rel_path,
                    "size": path.stat().st_size,
                    "mime_type": mimetypes.guess_type(path.name)[0] or "",
                    "media_info": None,
                })
                seen.add(rel_path)
                added += 1
        except Exception:
            pass
        return existing

    def collect_media_insights(
        self,
        client: Any,
        parse_result,
        *,
        target_path: Optional[str],
        archive_path: Optional[str],
        max_items: int = 12,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run media-only summarization on demand."""
        import logging
        logger = logging.getLogger(__name__)
        if client is None or parse_result is None:
            raise RuntimeError("Media insights prerequisites missing.")

        scan_path = target_path or archive_path or ""
        read_base_path = target_path if target_path else archive_path
        files = parse_result.files or []

        if progress_callback:
            progress_callback("Gathering media files…")

        relevant_files = []
        for meta in files:
            file_path = meta.path
            if target_path and '/' in file_path:
                path_parts = file_path.split('/', 1)
                if len(path_parts) > 1:
                    file_path = path_parts[1]
            relevant_files.append({
                "path": file_path,
                "size": meta.size_bytes,
                "mime_type": meta.mime_type,
                "media_info": getattr(meta, "media_info", None),
            })

        relevant_files = self._ensure_media_candidates(target_path, relevant_files)

        try:
            logger.info(f"[AI Service] Collecting media insights for {len(relevant_files)} files, scan path: {scan_path}")
            result = client.summarize_media_only(
                relevant_files=relevant_files,
                scan_base_path=read_base_path or "",
                max_items=max_items,
                progress_callback=progress_callback,
            )
            return result
        except Exception as exc:
            logger.error(f"[AI Service] Media insights error: {exc}")
            raise AIProviderError(str(exc)) from exc

    def format_analysis(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format AI analysis result into structured sections with Rich markup.
        
        Returns a dict with:
            - portfolio_overview: str (with Rich markup)
            - projects: list of {name, path, overview, key_files: [{file_path, analysis, file_size, priority_score}]}
            - supporting_files: str or None
            - skipped_files: list of {path, reason, size_mb}
            - media_assets: optional bullet list of media briefs
        """
        structured_result: Dict[str, Any] = {
            "portfolio_overview": None,
            "projects": [],
            "supporting_files": None,
            "skipped_files": [],
            "media_assets": None,
        }
        
        # Helper function to escape Rich markup in AI-generated text
        def escape_rich_markup(text: str) -> str:
            if not text:
                return ""
            # Escape square brackets that might interfere with Rich markup
            return text.replace("[", r"\[").replace("]", r"\]")

        media_briefings = result.get("media_briefings") or []
        if media_briefings:
            structured_result["media_assets"] = "\n".join(
                f"• {escape_rich_markup(entry)}" for entry in media_briefings
            )
        
        # Helper to calculate file priority score
        def file_priority(f):
            path = f.get('file_path', '').lower()
            # Lower score = higher priority
            if '__init__' in path:
                return 200
            if path.endswith('requirements.txt') or path.endswith('package.json'):
                return 150
            if 'test' in path or 'fixture' in path:
                return 100
            if path.endswith(('.py', '.js', '.ts', '.java')):
                if 'src/' in path or 'backend/' in path:
                    return 1
                return 50
            if path.endswith(('.json', '.md', '.txt')):
                return 80
            return 90
        
        # Portfolio Overview
        portfolio = result.get("portfolio_summary") or {}
        if portfolio.get("summary"):
            structured_result["portfolio_overview"] = escape_rich_markup(portfolio["summary"])
        
        # Projects
        projects = result.get("projects") or []
        if projects:
            for idx, project in enumerate(projects, 1):
                name = project.get("project_name", f"Project {idx}")
                path = project.get("project_path") or ""
                analysis = escape_rich_markup(project.get("analysis", "No analysis available."))
                
                # Process key files for this project
                file_summaries = project.get("file_summaries") or []
                sorted_files = sorted(file_summaries, key=file_priority)
                max_files = 3 if len(projects) > 1 else 5
                key_files_data = []
                
                for f in sorted_files:
                    priority = file_priority(f)
                    if priority < 90 and len(key_files_data) < max_files:
                        key_files_data.append({
                            "file_path": f.get('file_path', 'Unknown file'),
                            "analysis": escape_rich_markup(f.get('analysis', 'No analysis available.')),
                            "file_size": f.get('size_bytes', 0),
                            "priority_score": priority
                        })
                
                structured_result["projects"].append({
                    "name": name,
                    "path": path,
                    "overview": analysis,
                    "key_files": key_files_data
                })
        
        # Supporting Files (unassigned files)
        unassigned = result.get("unassigned_files")
        if unassigned and unassigned.get("analysis"):
            structured_result["supporting_files"] = escape_rich_markup(unassigned.get("analysis", ""))
        
        # Handle single-project analysis without multi-project structure
        project_analysis = result.get("project_analysis") or {}
        if project_analysis and not projects:
            analysis_text = project_analysis.get("analysis")
            if analysis_text:
                # Create a single project entry
                structured_result["projects"].append({
                    "name": "Project",
                    "path": ".",
                    "overview": escape_rich_markup(analysis_text),
                    "key_files": []
                })
        
        # File summaries for single-project analysis
        file_summaries = result.get("file_summaries") or []
        if file_summaries and not projects:
            # If we created a project entry above, add files to it
            if structured_result["projects"]:
                sorted_summaries = sorted(file_summaries, key=file_priority)
                key_files_data = []
                for f in sorted_summaries:
                    priority = file_priority(f)
                    if priority < 90 and len(key_files_data) < 5:
                        key_files_data.append({
                            "file_path": f.get('file_path', 'Unknown file'),
                            "analysis": escape_rich_markup(f.get('analysis', 'No analysis available.')),
                            "file_size": f.get('size_bytes', 0),
                            "priority_score": priority
                        })
                structured_result["projects"][0]["key_files"] = key_files_data
        
        # Skipped Files
        skipped = result.get("skipped_files") or []
        for item in skipped:
            structured_result["skipped_files"].append({
                "path": item.get("path", "unknown"),
                "reason": item.get("reason", "No reason provided."),
                "size_mb": item.get("size_mb")
            })
        
        return structured_result

    def summarize_analysis(self, result: Dict[str, Any]) -> str:
        parts: List[str] = []
        files_count = result.get("files_analyzed_count")
        if files_count:
            parts.append(f"Files analyzed: {files_count}")
        project_count = result.get("project_count")
        if project_count:
            parts.append(f"Projects analyzed: {project_count}")
        file_summaries = result.get("file_summaries") or []
        if file_summaries:
            parts.append(f"Key file insights: {len(file_summaries)}")
        media_briefings = result.get("media_briefings") or []
        if media_briefings:
            parts.append(f"Media assets reviewed: {len(media_briefings)}")
        analysis_text = (result.get("project_analysis") or {}).get("analysis") or ""
        if not analysis_text and result.get("projects"):
            first_project = result["projects"][0]
            analysis_text = first_project.get("analysis", "")
        if not analysis_text and result.get("portfolio_summary"):
            analysis_text = result["portfolio_summary"].get("summary", "")
        if analysis_text:
            snippet = analysis_text.strip().splitlines()[0]
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            parts.append(f"Preview: {snippet}")
        return "\n".join(f"- {text}" for text in parts) if parts else ""
    
    def execute_auto_suggestion(
    self,
    client: Any,
    selected_files: List[str],
    output_dir: str,
    base_path: Path,
    parse_result: ParseResult,
    progress_callback: Callable[[str, Optional[int]], None]
) -> Dict[str, Any]:
        """
        Execute AI auto-suggestion workflow.
        
        Args:
            selected_files: List of file paths to improve
            output_dir: Directory to save improved files
            base_path: Base directory of scanned project
            parse_result: Parse result with file metadata
            progress_callback: Function to update progress (message, percent)
        
        Returns:
            Dict with:
            - output_dir: Path to output directory
            - total_files: Total files processed
            - successful: Number of successfully improved files
            - failed: Number of failed files
            - results: List of dicts with file results
        """
        
        self.logger.info(f"Starting auto-suggestion for {len(selected_files)} files")
        self.logger.info(f"Base path: {base_path}")
        progress_callback("Initializing auto-suggestion...", 0)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok = True)
        
        self.logger.info(f"Created output directory: {output_path}")
        progress_callback(f"Created output directory: {output_path.name}", 5)
        
        # Track results
        results = []
        successful = 0
        failed = 0
        
        # Create file metadata lookup
        file_metadata = {f.path: f for f in parse_result.files}
        
        # Process each selected file
        total = len(selected_files)
        for idx, file_path in enumerate(selected_files):
            progress_percent = int(10 + (idx / total) * 80)  # 10% to 90%
            progress_callback(f"Processing {file_path}...", progress_percent)
            
            try:
                # Get file metadata
                meta = file_metadata.get(file_path)
                if not meta:
                    self.logger.warning(f"File metadata not found: {file_path}")
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": "File metadata not found"
                    })
                    failed += 1
                    continue
                
                # 🔒 SECURITY: Validate and resolve path safely
                try:
                    output_file, full_read_path = _validate_and_resolve_path(
                        file_path, 
                        Path(base_path).resolve(), 
                        output_path.resolve()
                    )
                    self.logger.info(f"Validated path: {file_path}")
                    self.logger.info(f"Read from: {full_read_path}")
                    self.logger.info(f"Write to: {output_file}")
                except ValueError as path_error:
                    self.logger.error(f"Path validation failed for {file_path}: {path_error}")
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": f"Invalid path: {str(path_error)}"
                    })
                    failed += 1
                    continue
                
                # Verify file exists
                if not full_read_path.exists():
                    self.logger.error(f"File not found: {full_read_path}")
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": f"File not found at {full_read_path}"
                    })
                    failed += 1
                    continue
                
                # Read original file content
                try:
                    original_content = full_read_path.read_text(encoding='utf-8')
                    self.logger.info(f"Successfully read file: {file_path} ({len(original_content)} chars)")
                except UnicodeDecodeError:
                    # Try other encodings
                    try:
                        original_content = full_read_path.read_text(encoding='latin-1')
                        self.logger.warning(f"Read file with latin-1 encoding: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to read file {file_path}: {e}")
                        results.append({
                            "file_path": file_path,
                            "success": False,
                            "error": f"Failed to read file: {str(e)}"
                        })
                        failed += 1
                        continue
                
                # Get file type
                file_type = meta.mime_type or "text/plain"
                
                # Generate improvements via LLM
                self.logger.info(f"Generating improvements for {file_path} (type: {file_type})")
                
                try:
                    improvement_result = client.generate_and_apply_improvements(
                        file_path,
                        original_content,
                        file_type
                    )
                except Exception as llm_error:
                    self.logger.error(f"LLM call failed for {file_path}: {llm_error}")
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": f"LLM error: {str(llm_error)}"
                    })
                    failed += 1
                    continue
                
                # ✅ FIX: Enhanced error handling with detailed logging
                if not improvement_result.get("success"):
                    error = improvement_result.get("error", "Unknown error")
                    raw_response = improvement_result.get("raw_response", "")
                    
                    self.logger.error(f"Failed to improve {file_path}: {error}")
                    if raw_response:
                        self.logger.error(f"Raw LLM response (first 500 chars): {raw_response[:500]}")
                    
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": error,
                        "raw_response": raw_response[:200] if raw_response else None  # Truncate for output
                    })
                    failed += 1
                    continue
                
                # Save improved file
                improved_content = improvement_result.get("improved_code", original_content)
                
                # Preserve directory structure in output
                # output_file = output_path / Path(file_path).name
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    output_file.write_text(improved_content, encoding='utf-8')
                    self.logger.info(f"Saved improved file to: {output_file}")
                except Exception as write_error:
                    self.logger.error(f"Failed to write improved file {file_path}: {write_error}")
                    results.append({
                        "file_path": file_path,
                        "success": False,
                        "error": f"Failed to write output: {str(write_error)}"
                    })
                    failed += 1
                    continue
                
                # Generate diff
                diff = self._generate_diff(
                    original_content,
                    improved_content,
                    file_path
                )
                
                # Count changed lines (exclude diff metadata lines)
                changed_lines = [
                    line for line in diff.split('\n') 
                    if line.startswith('+') and not line.startswith('+++') or
                    line.startswith('-') and not line.startswith('---')
                ]
                lines_changed = len(changed_lines)
                
                # Record success
                results.append({
                    "file_path": file_path,
                    "success": True,
                    "suggestions": improvement_result.get("suggestions", []),
                    "diff": diff,
                    "lines_changed": lines_changed,
                    "output_file": str(output_file)
                })
                successful += 1
                
                self.logger.info(f"✓ Successfully improved {file_path} ({lines_changed} lines changed)")
            
            except Exception as e:
                self.logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "error": f"Unexpected error: {str(e)}"
                })
                failed += 1
        
        progress_callback("Auto-suggestion complete!", 100)
        
        self.logger.info(
            f"Auto-suggestion complete: {successful} successful, {failed} failed out of {total} total"
        )
        
        return {
            "output_dir": str(output_path),
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "results": results
        }


    def _generate_diff(self, original: str, improved: str, filename: str) -> str:
        """Generate unified diff between original and improved content."""
        
        original_lines = original.splitlines(keepends=True)
        improved_lines = improved.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            improved_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )
        
        return ''.join(diff)
