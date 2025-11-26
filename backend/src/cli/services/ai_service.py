from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any, Dict, List, Optional, Sequence

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


class AIService:
    """Utility helpers around the LLM client lifecycle and formatting."""

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
        import logging
        logger = logging.getLogger(__name__)
        
        if client is None or parse_result is None:
            logger.error("AI analysis prerequisites missing - client or parse_result is None")
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
            })
        
        logger.info(f"[AI Service] Total files: {len(files)}, Relevant files: {len(relevant_files)}")
        logger.info(f"[AI Service] Scan path: {scan_path}")
        logger.info(f"[AI Service] Read base path: {read_base_path}")
        logger.info(f"[AI Service] Git repos: {git_repos}")
        
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
            logger.info(f"[AI Service] Calling client.summarize_scan_with_ai with {len(relevant_files)} files")
            result = client.summarize_scan_with_ai(
                scan_summary=scan_summary,
                relevant_files=relevant_files,
                scan_base_path=read_base_path,
                project_dirs=project_dirs,
                progress_callback=progress_callback,
            )
            logger.info(f"[AI Service] Analysis complete, result keys: {list(result.keys()) if result else 'None'}")
            return result
        except Exception as exc:
            logger.error(f"[AI Service] Error during analysis: {exc}")
            raise AIProviderError(str(exc)) from exc

    def format_analysis(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format AI analysis result into structured sections with Rich markup.
        
        Returns a dict with:
            - portfolio_overview: str (with Rich markup)
            - projects: list of {name, path, overview, key_files: [{file_path, analysis, file_size, priority_score}]}
            - supporting_files: str or None
            - skipped_files: list of {path, reason, size_mb}
        """
        structured_result: Dict[str, Any] = {
            "portfolio_overview": None,
            "projects": [],
            "supporting_files": None,
            "skipped_files": []
        }
        
        # Helper function to escape Rich markup in AI-generated text
        def escape_rich_markup(text: str) -> str:
            if not text:
                return ""
            # Escape square brackets that might interfere with Rich markup
            return text.replace("[", r"\[").replace("]", r"\]")
        
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
