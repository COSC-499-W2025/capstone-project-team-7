"""
Contribution Analysis Service

Provides contribution metrics extraction for the Textual CLI application.
Wraps the ContributionAnalyzer module, formats results for display, and
derives lightweight ranking signals from contribution data.
"""

import logging
import math
import os
from datetime import datetime, timezone
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

    # --- Ranking helpers -------------------------------------------------

    def compute_contribution_score(
        self,
        metrics: ProjectContributionMetrics,
        *,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Compute a normalized contribution-based importance score for a project.

        Signals (weights tuned for “commit volume first”):
        - 50%: commit volume (log scaled)
        - 20%: user share of commits (matches on email/name, falls back to solo projects)
        - 15%: recency (newer end dates score higher)
        - 10%: commit frequency (commits/day)
        - 5% : activity mix bonus for tests/docs/design work
        """
        reference_now = now or datetime.now(timezone.utc)

        # Commit volume (log-scaled to keep huge repos from dominating)
        total_commits = max(0, metrics.total_commits or 0)
        volume_score = 0.0
        if total_commits > 0:
            volume_score = min(1.0, math.log1p(total_commits) / math.log1p(1000))

        # User share of commits
        user_share = 0.0
        # Support env override for the user's git email
        if not user_email:
            user_email = os.environ.get("PORTFOLIO_USER_EMAIL")
        normalized_email = (user_email or "").strip().lower()
        normalized_name = (user_name or "").strip().lower()
        if metrics.contributors:
            for contributor in metrics.contributors:
                if contributor is None:
                    continue
                email_match = normalized_email and contributor.email and contributor.email.lower() == normalized_email
                name_match = normalized_name and contributor.name and contributor.name.lower() == normalized_name
                if email_match or name_match:
                    user_share = max(user_share, min(1.0, (contributor.commit_percentage or 0) / 100.0))
            if user_share == 0.0 and metrics.is_solo_project:
                # Solo projects implicitly belong to the user
                user_share = 1.0
        elif metrics.is_solo_project:
            user_share = 1.0

        # Recency: newer end dates score higher, decay over ~2 years
        recency_score = 0.0
        end_date = metrics.project_end_date
        if end_date:
            try:
                parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                days_old = (reference_now - parsed_end).days
                recency_score = max(0.0, 1.0 - min(days_old, 730) / 730)  # linear decay over 2 years
            except Exception:
                recency_score = 0.0

        # Commit frequency: saturate at 5 commits/day
        freq = max(0.0, metrics.commit_frequency or 0.0)
        frequency_score = min(1.0, freq / 5.0)

        # Activity mix bonus: reward tests/docs/design balance slightly
        percentages = metrics.overall_activity_breakdown.percentages
        mix_bonus = (
            percentages.get("test", 0.0)
            + percentages.get("documentation", 0.0)
            + percentages.get("design", 0.0)
        )
        activity_mix_score = min(1.0, mix_bonus / 60.0)  # cap when 60%+ is non-core-code support work

        # Weighted aggregate -> 0..100
        score = (
            0.50 * volume_score
            + 0.20 * user_share
            + 0.15 * recency_score
            + 0.10 * frequency_score
            + 0.05 * activity_mix_score
        ) * 100.0

        return {
            "score": round(score, 2),
            "user_commit_share": round(user_share, 4),
            "components": {
                "volume": round(volume_score, 4),
                "user_share": round(user_share, 4),
                "recency": round(recency_score, 4),
                "frequency": round(frequency_score, 4),
                "activity_mix": round(activity_mix_score, 4),
            },
            "total_commits": total_commits,
        }

    def metrics_from_dict(self, data: Dict[str, Any]) -> ProjectContributionMetrics:
        """Rehydrate ProjectContributionMetrics from a serialized dictionary."""
        breakdown = data.get("overall_activity_breakdown") or {}
        breakdown_lines = (breakdown.get("lines") or {}) if isinstance(breakdown, dict) else {}
        activity = ActivityBreakdown(
            code_lines=breakdown_lines.get("code", 0) or 0,
            test_lines=breakdown_lines.get("test", 0) or 0,
            documentation_lines=breakdown_lines.get("documentation", 0) or 0,
            design_lines=breakdown_lines.get("design", 0) or 0,
            config_lines=breakdown_lines.get("config", 0) or 0,
        )

        contributors_data = data.get("contributors") or []
        contributors = []
        for contributor in contributors_data:
            if not isinstance(contributor, dict):
                continue
            contrib_activity_lines = (
                contributor.get("activity_breakdown", {}).get("lines", {})
                if isinstance(contributor.get("activity_breakdown"), dict)
                else {}
            )
            contrib_activity = ActivityBreakdown(
                code_lines=contrib_activity_lines.get("code", 0) or 0,
                test_lines=contrib_activity_lines.get("test", 0) or 0,
                documentation_lines=contrib_activity_lines.get("documentation", 0) or 0,
                design_lines=contrib_activity_lines.get("design", 0) or 0,
                config_lines=contrib_activity_lines.get("config", 0) or 0,
            )
            contributors.append(
                ContributorMetrics(
                    name=contributor.get("name", "Unknown"),
                    email=contributor.get("email"),
                    commits=contributor.get("commits", 0) or 0,
                    commit_percentage=contributor.get("commit_percentage", 0.0) or 0.0,
                    first_commit_date=contributor.get("first_commit_date"),
                    last_commit_date=contributor.get("last_commit_date"),
                    active_days=contributor.get("active_days", 0) or 0,
                    activity_breakdown=contrib_activity,
                )
            )

        metrics = ProjectContributionMetrics(
            project_path=data.get("project_path", ""),
            project_type=data.get("project_type", "unknown"),
            total_commits=data.get("total_commits", 0) or 0,
            total_contributors=data.get("total_contributors", 0) or len(contributors),
            project_duration_days=data.get("project_duration_days"),
            project_start_date=data.get("project_start_date"),
            project_end_date=data.get("project_end_date"),
            contributors=contributors,
            overall_activity_breakdown=activity,
            commit_frequency=data.get("commit_frequency", 0.0) or 0.0,
            languages_detected=set(data.get("languages_detected", []) or []),
        )
        return metrics
