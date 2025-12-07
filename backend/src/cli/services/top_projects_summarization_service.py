"""
Service for generating summaries of top-ranked user projects.

Implements filtering, ranking, and formatting of project summaries for
display in the UI or export to files.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TopProjectsSummarizationService:
    """Service for generating summaries of top-ranked user projects."""

    def __init__(self, ai_service: Optional[Any] = None):
        """
        Initialize summarization service.

        Args:
            ai_service: Optional AIService for LLM-enhanced summaries
        """
        self.ai_service = ai_service

    def get_top_projects(
        self, projects: List[Dict[str, Any]], count: int = 5, sort_by: str = "importance"
    ) -> List[Dict[str, Any]]:
        """
        Get top N projects ranked by importance or recency.

        Args:
            projects: List of project dicts from ProjectsService
            count: Number of top projects to return
            sort_by: "importance" (default) or "recency"

        Returns:
            List of top N projects, sorted appropriately
        """
        if not projects:
            return []

        if sort_by == "recency":
            sorted_projects = sorted(
                projects, key=lambda p: p.get("scan_timestamp") or "", reverse=True
            )
        else:  # importance (default)
            sorted_projects = sorted(
                projects,
                key=lambda p: (
                    p.get("contribution_score") is None,
                    -(p.get("contribution_score") or 0),
                    p.get("scan_timestamp") or "",
                ),
            )

        return sorted_projects[:count]

    def generate_project_summary(
        self,
        project: Dict[str, Any],
        include_metrics: bool = True,
        include_technologies: bool = True,
        include_documents: bool = False,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a structured summary for a single project.

        Args:
            project: Project dict (from DB or projects list)
            include_metrics: Include contribution metrics
            include_technologies: Include languages and tech stack
            include_documents: Include document/PDF summaries
            use_llm: Use AI service for natural language summary

        Returns:
            Dict containing project summary
        """
        summary = {
            "project_name": project.get("project_name"),
            "path": project.get("project_path"),
            "scan_date": project.get("scan_timestamp"),
        }

        # Importance ranking metrics
        if include_metrics:
            summary["metrics"] = {
                "importance_score": project.get("contribution_score"),
                "your_contribution": f"{project.get('user_commit_share', 0):.1f}%",
                "total_commits": project.get("total_commits"),
                "primary_contributor": project.get("primary_contributor"),
                "project_duration": project.get("project_end_date"),
            }

        # Technology stack
        if include_technologies:
            languages = project.get("languages", [])
            summary["technologies"] = {
                "languages": languages,
                "has_code_analysis": project.get("has_code_analysis", False),
                "has_git_analysis": project.get("has_git_analysis", False),
            }

        # Document/PDF summaries
        if include_documents:
            summary["documents"] = {
                "has_pdf_analysis": project.get("has_pdf_analysis", False),
                "has_media_analysis": project.get("has_media_analysis", False),
            }

        # Optional: LLM-enhanced narrative
        if use_llm and self.ai_service:
            summary["narrative"] = self._generate_narrative(project)

        return summary

    def generate_batch_summaries(
        self,
        projects: List[Dict[str, Any]],
        count: int = 5,
        use_llm: bool = False,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Generate summaries for multiple top projects.

        Args:
            projects: List of all projects
            count: Number of top projects to summarize
            use_llm: Use AI for narratives
            **kwargs: Additional options for generate_project_summary()

        Returns:
            List of project summaries
        """
        top_projects = self.get_top_projects(projects, count=count)
        return [self.generate_project_summary(p, use_llm=use_llm, **kwargs) for p in top_projects]

    def format_report(
        self, summaries: List[Dict[str, Any]], format_type: str = "text"
    ) -> str:
        """
        Format project summaries for output/export.

        Args:
            summaries: List of project summaries
            format_type: "text", "markdown", or "json"

        Returns:
            Formatted report string
        """
        if format_type == "json":
            return json.dumps(summaries, indent=2)

        elif format_type == "markdown":
            return self._format_markdown(summaries)

        else:  # text (default)
            return self._format_text(summaries)

    def _format_text(self, summaries: List[Dict[str, Any]]) -> str:
        """Format as plain text."""
        lines = ["TOP PROJECTS SUMMARY\n" + "=" * 50 + "\n"]

        for i, summary in enumerate(summaries, 1):
            lines.append(f"{i}. {summary['project_name']}")

            if "metrics" in summary:
                metrics = summary["metrics"]
                lines.append(f"   Importance Score: {metrics['importance_score']:.2f}")
                lines.append(f"   Your Contribution: {metrics['your_contribution']}")
                lines.append(f"   Total Commits: {metrics['total_commits']}")

            if "technologies" in summary:
                techs = summary["technologies"]["languages"]
                if techs:
                    lines.append(f"   Languages: {', '.join(techs)}")

            if "narrative" in summary:
                lines.append(f"   Summary: {summary['narrative']}")

            lines.append("")  # Blank line between projects

        return "\n".join(lines)

    def _format_markdown(self, summaries: List[Dict[str, Any]]) -> str:
        """Format as markdown."""
        lines = ["# Top Projects Summary\n"]

        for i, summary in enumerate(summaries, 1):
            lines.append(f"## {i}. {summary['project_name']}\n")

            if "metrics" in summary:
                metrics = summary["metrics"]
                lines.append("### Metrics")
                lines.append(f"- **Importance Score**: {metrics['importance_score']:.2f}")
                lines.append(f"- **Your Contribution**: {metrics['your_contribution']}")
                lines.append(f"- **Total Commits**: {metrics['total_commits']}")
                lines.append("")

            if "technologies" in summary:
                techs = summary["technologies"]["languages"]
                if techs:
                    lines.append("### Technologies")
                    lines.append(f"- Languages: {', '.join(techs)}")
                    lines.append("")

            if "narrative" in summary:
                lines.append("### Summary")
                lines.append(summary["narrative"])
                lines.append("")

        return "\n".join(lines)

    def _generate_narrative(self, project: Dict[str, Any]) -> str:
        """
        Generate a natural language narrative using LLM.
        (Implementation depends on AIService capabilities)
        """
        if not self.ai_service:
            return "Narrative generation requires AI service."

        # Prepare context
        context = {
            "project_name": project.get("project_name"),
            "languages": project.get("languages", []),
            "importance_score": project.get("contribution_score", 0),
            "user_contribution": project.get("user_commit_share", 0),
            "total_commits": project.get("total_commits", 0),
        }

        # Call AI service to generate narrative
        # This assumes AIService has a method like generate_project_narrative()
        try:
            narrative = self.ai_service.generate_project_narrative(context)
            return narrative
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return "Unable to generate AI summary at this time."
