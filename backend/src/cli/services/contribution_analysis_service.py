"""
Contribution Analysis Service

Provides contribution metrics extraction for the Textual CLI application.
Wraps the ContributionAnalyzer module and formats results for display.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ...local_analysis.contribution_analyzer import (
    ContributionAnalyzer,
    ProjectContributionMetrics,
    ContributorMetrics,
    ActivityBreakdown,
)

logger = logging.getLogger(__name__)


class ContributionAnalysisError(Exception):
    """Raised when contribution analysis fails."""
    pass


class ContributionAnalysisService:
    """
    Service for analyzing project contributions.
    
    Extracts and formats:
    - Individual vs collaborative project detection
    - Activity type breakdown (code, tests, docs, design, config)
    - Contributor-specific metrics
    - Project timeline and duration
    - Contribution frequency patterns
    """

    def __init__(self):
        """Initialize the contribution analysis service."""
        self._analyzer = ContributionAnalyzer()

    def analyze_contributions(
        self,
        git_analysis: Dict[str, Any],
        code_analysis: Optional[Dict[str, Any]] = None,
        parse_result: Optional[Any] = None,
    ) -> ProjectContributionMetrics:
        """
        Analyze contributions from project data.
        
        Args:
            git_analysis: Git repository analysis data
            code_analysis: Optional code analysis results
            parse_result: Optional parse result with file metadata
            
        Returns:
            ProjectContributionMetrics with comprehensive data
            
        Raises:
            ContributionAnalysisError: If analysis fails
        """
        try:
            metrics = self._analyzer.analyze_contributions(
                git_analysis=git_analysis,
                code_analysis=code_analysis,
                parse_result=parse_result,
            )
            
            logger.info(
                f"Analyzed contributions: {metrics.total_contributors} contributors, "
                f"{metrics.total_commits} commits"
            )
            return metrics
            
        except Exception as exc:
            logger.error(f"Contribution analysis failed: {exc}")
            raise ContributionAnalysisError(f"Failed to analyze contributions: {exc}") from exc

    def format_summary(self, metrics: ProjectContributionMetrics) -> str:
        """
        Format contribution metrics as a summary string for display.
        
        Args:
            metrics: ProjectContributionMetrics to format
            
        Returns:
            Formatted multi-line string
        """
        lines = []
        
        lines.append("[b]Contribution Analysis[/b]\n")
        
        # Project classification
        project_type_display = {
            "individual": "Individual Project",
            "collaborative": "Collaborative Project",
            "unknown": "Unknown Type"
        }
        lines.append(f"Project Type: {project_type_display.get(metrics.project_type, 'Unknown')}")
        
        # Timeline
        if metrics.project_start_date and metrics.project_end_date:
            start_display = metrics.project_start_date[:10]  # Just the date part
            end_display = metrics.project_end_date[:10]
            lines.append(f"Timeline: {start_display} → {end_display}")
            
            if metrics.project_duration_days:
                lines.append(f"Duration: {metrics.project_duration_days} days")
        
        # Commit statistics
        lines.append(f"\n[b]Commit Statistics[/b]")
        lines.append(f"Total Commits: {metrics.total_commits}")
        lines.append(f"Total Contributors: {metrics.total_contributors}")
        
        if metrics.commit_frequency > 0:
            lines.append(f"Average Commit Frequency: {metrics.commit_frequency} commits/day")
        
        # Activity breakdown
        lines.append(f"\n[b]Activity Breakdown[/b]")
        activity = metrics.overall_activity_breakdown
        percentages = activity.percentages
        
        if activity.total_lines > 0:
            lines.append(f"Total Lines Analyzed: {activity.total_lines:,}")
            lines.append(f"  • Code: {activity.code_lines:,} ({percentages['code']}%)")
            lines.append(f"  • Tests: {activity.test_lines:,} ({percentages['test']}%)")
            lines.append(f"  • Documentation: {activity.documentation_lines:,} ({percentages['documentation']}%)")
            lines.append(f"  • Design: {activity.design_lines:,} ({percentages['design']}%)")
            lines.append(f"  • Configuration: {activity.config_lines:,} ({percentages['config']}%)")
        else:
            lines.append("No detailed activity breakdown available")
        
        # Languages
        if metrics.languages_detected:
            langs = ", ".join(sorted(metrics.languages_detected)[:5])
            if len(metrics.languages_detected) > 5:
                langs += f" (+{len(metrics.languages_detected) - 5} more)"
            lines.append(f"\n[b]Languages:[/b] {langs}")
        
        return "\n".join(lines)

    def format_contributors_detail(self, metrics: ProjectContributionMetrics) -> str:
        """
        Format detailed contributor information.
        
        Args:
            metrics: ProjectContributionMetrics with contributor data
            
        Returns:
            Formatted multi-line string with contributor details
        """
        lines = []
        
        lines.append("[b]Contributor Details[/b]\n")
        
        if not metrics.contributors:
            lines.append("No contributor data available")
            return "\n".join(lines)
        
        # Sort by commit count
        sorted_contributors = sorted(
            metrics.contributors,
            key=lambda c: c.commits,
            reverse=True
        )
        
        for idx, contrib in enumerate(sorted_contributors, 1):
            lines.append(f"[b]{idx}. {contrib.name}[/b]")
            
            if contrib.email:
                lines.append(f"   Email: {contrib.email}")
            
            lines.append(f"   Commits: {contrib.commits} ({contrib.commit_percentage}%)")
            
            if contrib.first_commit_date and contrib.last_commit_date:
                first = contrib.first_commit_date[:10]
                last = contrib.last_commit_date[:10]
                lines.append(f"   Active: {first} → {last}")
            
            if contrib.active_days > 0:
                lines.append(f"   Active Days: {contrib.active_days}")
            
            if contrib.contribution_frequency > 0:
                lines.append(f"   Frequency: {contrib.contribution_frequency} commits/day")
            
            # Activity breakdown for this contributor if available
            if contrib.activity_breakdown.total_lines > 0:
                percentages = contrib.activity_breakdown.percentages
                lines.append(f"   Activity Mix:")
                if percentages['code'] > 0:
                    lines.append(f"     • Code: {percentages['code']}%")
                if percentages['test'] > 0:
                    lines.append(f"     • Tests: {percentages['test']}%")
                if percentages['documentation'] > 0:
                    lines.append(f"     • Docs: {percentages['documentation']}%")
            
            lines.append("")  # Blank line between contributors
        
        return "\n".join(lines)

    def format_contribution_paragraph(self, metrics: ProjectContributionMetrics) -> str:
        """
        Format contribution metrics as a narrative paragraph.
        
        Args:
            metrics: ProjectContributionMetrics to format
            
        Returns:
            Narrative paragraph describing the contributions
        """
        parts = []
        
        # Project type and timeline
        if metrics.project_type == "individual":
            parts.append("This is an individual project")
        elif metrics.project_type == "collaborative":
            parts.append(f"This collaborative project involves {metrics.total_contributors} contributors")
        else:
            parts.append("This project")
        
        # Duration and activity
        if metrics.project_duration_days:
            parts.append(f"spanning {metrics.project_duration_days} days")
            
            if metrics.total_commits > 0:
                parts.append(f"with {metrics.total_commits} commits")
        elif metrics.total_commits > 0:
            parts.append(f"with {metrics.total_commits} total commits")
        
        paragraph = " ".join(parts) + "."
        
        # Activity breakdown insight
        activity = metrics.overall_activity_breakdown
        if activity.total_lines > 0:
            percentages = activity.percentages
            dominant_type = max(percentages.items(), key=lambda x: x[1])
            
            if dominant_type[1] > 50:
                activity_insight = f" The work is primarily focused on {dominant_type[0]} ({dominant_type[1]}%)"
            else:
                # Mixed activity
                top_activities = sorted(
                    [(k, v) for k, v in percentages.items() if v > 5],
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                activity_list = ", ".join([f"{k} ({v}%)" for k, v in top_activities])
                activity_insight = f" The work involves a mix of activities including {activity_list}"
            
            paragraph += activity_insight + "."
        
        # Contributor insight for collaborative projects
        if metrics.project_type == "collaborative" and metrics.primary_contributor:
            primary = metrics.primary_contributor
            paragraph += f" {primary.name} is the primary contributor with {primary.commits} commits ({primary.commit_percentage}%)."
        
        return paragraph

    def export_data(self, metrics: ProjectContributionMetrics) -> Dict[str, Any]:
        """
        Export contribution metrics to dictionary for JSON serialization.
        
        Args:
            metrics: ProjectContributionMetrics to export
            
        Returns:
            Dictionary representation
        """
        return self._analyzer.export_to_dict(metrics)
