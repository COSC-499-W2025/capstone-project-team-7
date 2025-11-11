from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

class AIDependencyError(RuntimeError):
    """Raised when optional AI dependencies are missing."""


class InvalidAIKeyError(RuntimeError):
    """Raised when the provided API key is invalid."""


class AIProviderError(RuntimeError):
    """Raised when the AI provider returns an error."""


@dataclass(slots=True)
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
            from ...analyzer.llm.client import LLMClient, InvalidAPIKeyError as ClientInvalidKey, LLMError
        except Exception as exc:  # pragma: no cover - optional dependency missing
            raise AIDependencyError(str(exc)) from exc

        if not api_key:
            raise InvalidAIKeyError("API key required.")

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
        except ClientInvalidKey as exc:
            raise InvalidAIKeyError(str(exc)) from exc
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
    ) -> Dict[str, Any]:
        if client is None or parse_result is None:
            raise RuntimeError("AI analysis prerequisites missing.")

        scan_path = target_path or archive_path or ""
        files = parse_result.files or []
        relevant_files = [
            {
                "path": meta.path,
                "size": meta.size_bytes,
                "mime_type": meta.mime_type,
            }
            for meta in files
        ]
        scan_summary = {
            "total_files": len(files),
            "total_size_bytes": sum(meta.size_bytes for meta in files),
            "language_breakdown": list(languages),
            "scan_path": scan_path,
        }
        project_dirs = [str(path) for path in git_repos] if git_repos else None
        try:
            return client.summarize_scan_with_ai(
                scan_summary=scan_summary,
                relevant_files=relevant_files,
                scan_base_path=scan_path,
                project_dirs=project_dirs,
            )
        except Exception as exc:
            raise AIProviderError(str(exc)) from exc

    def format_analysis(self, result: Dict[str, Any]) -> str:
        lines: List[str] = ["[b]AI-Powered Analysis[/b]"]

        portfolio = result.get("portfolio_summary") or {}
        if portfolio.get("summary"):
            lines.append("\n[b]Portfolio Overview[/b]")
            lines.append(portfolio["summary"])

        projects = result.get("projects") or []
        if projects:
            lines.append("\n[b]Project Insights[/b]")
            for idx, project in enumerate(projects, 1):
                name = project.get("project_name", f"Project {idx}")
                path = project.get("project_path") or ""
                header = f"[b]{idx}. {name}[/b]"
                if path:
                    header += f" ({path})"
                lines.append(header)
                lines.append(project.get("analysis", "No analysis available."))
                file_summaries = project.get("file_summaries") or []
                if file_summaries:
                    lines.append("  [i]Key files[/i]")
                    for summary in file_summaries[:3]:
                        lines.append(f"    • {summary.get('file_path', 'Unknown file')}")
                lines.append("")

        unassigned = result.get("unassigned_files")
        if unassigned:
            lines.append("[b]Supporting Files[/b]")
            lines.append(unassigned.get("analysis", ""))

        project_analysis = result.get("project_analysis") or {}
        if project_analysis and not projects:
            analysis_text = project_analysis.get("analysis")
            if analysis_text:
                lines.append("\n[b]Project Insights[/b]")
                lines.append(analysis_text)

        file_summaries = result.get("file_summaries") or []
        if file_summaries:
            lines.append("\n[b]Key Files[/b]")
            for idx, summary in enumerate(file_summaries[:5], 1):
                lines.append(f"[b]{idx}. {summary.get('file_path', 'Unknown file')}[/b]")
                lines.append(summary.get("analysis", "No analysis available."))
                lines.append("")

        skipped = result.get("skipped_files") or []
        if skipped:
            lines.append("[b]Skipped Files[/b]")
            for item in skipped:
                path = item.get("path", "unknown")
                reason = item.get("reason", "No reason provided.")
                size_mb = item.get("size_mb")
                size_txt = f" ({size_mb:.2f} MB)" if isinstance(size_mb, (int, float)) else ""
                lines.append(f"- {path}{size_txt}: {reason}")

        return "\n".join(line for line in lines if line).strip()

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
