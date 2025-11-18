"""
Contribution Analyzer Module

Extracts individual contribution metrics from Git repositories and code analysis.
Provides detailed insights into:
- Individual vs collaborative project detection
- Activity type breakdown (code, tests, documentation, design)
- Contribution frequency and patterns
- Project duration and timeline
- Individual contributor statistics
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActivityBreakdown:
    """Breakdown of activity by type."""
    code_lines: int = 0
    test_lines: int = 0
    documentation_lines: int = 0
    design_lines: int = 0
    config_lines: int = 0
    
    @property
    def total_lines(self) -> int:
        return self.code_lines + self.test_lines + self.documentation_lines + self.design_lines + self.config_lines
    
    @property
    def percentages(self) -> Dict[str, float]:
        """Return percentage breakdown of activity types."""
        if self.total_lines == 0:
            return {
                "code": 0.0,
                "test": 0.0,
                "documentation": 0.0,
                "design": 0.0,
                "config": 0.0
            }
        
        return {
            "code": round((self.code_lines / self.total_lines) * 100, 2),
            "test": round((self.test_lines / self.total_lines) * 100, 2),
            "documentation": round((self.documentation_lines / self.total_lines) * 100, 2),
            "design": round((self.design_lines / self.total_lines) * 100, 2),
            "config": round((self.config_lines / self.total_lines) * 100, 2)
        }


@dataclass
class ContributorMetrics:
    """Metrics for an individual contributor."""
    name: str
    email: Optional[str] = None
    commits: int = 0
    commit_percentage: float = 0.0
    first_commit_date: Optional[str] = None
    last_commit_date: Optional[str] = None
    active_days: int = 0
    activity_breakdown: ActivityBreakdown = field(default_factory=ActivityBreakdown)
    files_touched: Set[str] = field(default_factory=set)
    languages_used: Set[str] = field(default_factory=set)
    
    @property
    def contribution_frequency(self) -> float:
        """Average commits per day of activity."""
        if self.active_days == 0:
            return 0.0
        return round(self.commits / self.active_days, 2)
    
    @property
    def days_active_span(self) -> Optional[int]:
        """Total days between first and last commit."""
        if not self.first_commit_date or not self.last_commit_date:
            return None
        try:
            first = datetime.fromisoformat(self.first_commit_date.replace('Z', '+00:00'))
            last = datetime.fromisoformat(self.last_commit_date.replace('Z', '+00:00'))
            return (last - first).days + 1
        except (ValueError, AttributeError):
            return None


@dataclass
class ProjectContributionMetrics:
    """Complete contribution analysis for a project."""
    project_path: str
    project_type: str  # "individual", "collaborative", "unknown"
    total_commits: int = 0
    total_contributors: int = 0
    project_duration_days: Optional[int] = None
    project_start_date: Optional[str] = None
    project_end_date: Optional[str] = None
    contributors: List[ContributorMetrics] = field(default_factory=list)
    overall_activity_breakdown: ActivityBreakdown = field(default_factory=ActivityBreakdown)
    commit_frequency: float = 0.0  # Avg commits per day
    languages_detected: Set[str] = field(default_factory=set)
    
    @property
    def primary_contributor(self) -> Optional[ContributorMetrics]:
        """Return contributor with most commits."""
        if not self.contributors:
            return None
        return max(self.contributors, key=lambda c: c.commits)
    
    @property
    def is_solo_project(self) -> bool:
        """Check if this is a solo/individual project."""
        return self.project_type == "individual" or self.total_contributors == 1


class ContributionAnalyzer:
    """
    Analyzes Git repositories and code to extract contribution metrics.
    
    Provides insights into:
    - Individual vs collaborative project classification
    - Activity type breakdown (code, tests, docs, design)
    - Contributor-specific metrics
    - Project timeline and duration
    - Contribution frequency patterns
    """
    
    # File patterns for activity type detection
    TEST_PATTERNS = [
        r'test[_-]',
        r'_test\.',
        r'\.test\.',
        r'\.spec\.',
        r'/tests?/',
        r'/spec(?:s)?/',
        r'/__tests__/',
        r'_spec\.',
    ]
    
    DOCUMENTATION_PATTERNS = [
        r'\.md$',
        r'\.txt$',
        r'\.rst$',
        r'\.adoc$',
        r'readme',
        r'changelog',
        r'contributing',
        r'license',
        r'/docs?/',
    ]
    
    DESIGN_PATTERNS = [
        r'\.svg$',
        r'\.sketch$',
        r'\.fig$',
        r'\.xd$',
        r'\.ai$',
        r'\.psd$',
        r'/design/',
        r'/assets/',
        r'/mockups?/',
    ]
    
    CONFIG_PATTERNS = [
        r'\.json$',
        r'\.yaml$',
        r'\.yml$',
        r'\.toml$',
        r'\.ini$',
        r'\.conf$',
        r'\.config$',
        r'package\.json',
        r'requirements\.txt$',
        r'Dockerfile',
        r'\.env',
        r'Makefile',
    ]
    
    def __init__(self):
        """Initialize the contribution analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self._test_regex = re.compile('|'.join(self.TEST_PATTERNS), re.IGNORECASE)
        self._doc_regex = re.compile('|'.join(self.DOCUMENTATION_PATTERNS), re.IGNORECASE)
        self._design_regex = re.compile('|'.join(self.DESIGN_PATTERNS), re.IGNORECASE)
        self._config_regex = re.compile('|'.join(self.CONFIG_PATTERNS), re.IGNORECASE)
    
    def analyze_contributions(
        self,
        git_analysis: Optional[Dict[str, Any]] = None,
        code_analysis: Optional[Dict[str, Any]] = None,
        parse_result: Optional[Any] = None,
    ) -> ProjectContributionMetrics:
        """
        Analyze project contributions from git history and code analysis.
        
        For Git projects: Uses commit history, contributors, timeline
        For non-Git projects: Uses file metadata, activity breakdown, code structure
        
        Args:
            git_analysis: Optional git repository analysis data with contributors, commits, etc.
            code_analysis: Optional code analysis results
            parse_result: Optional parse result with file metadata
            
        Returns:
            ProjectContributionMetrics with extracted data
        """
        # Determine if this is a Git project or file-based analysis
        has_git = git_analysis is not None and git_analysis.get('contributors')
        
        if not has_git:
            # Non-Git project: Use file-based analysis
            return self._analyze_non_git_project(code_analysis, parse_result)
        
        # Git project: Extract comprehensive metrics
        metrics = ProjectContributionMetrics(
            project_path=git_analysis.get('path', 'unknown'),
            project_type=git_analysis.get('project_type', 'unknown'),
            total_commits=git_analysis.get('commit_count', 0),
        )
        
        # Extract date range and duration
        date_range = git_analysis.get('date_range')
        if date_range:
            metrics.project_start_date = date_range.get('start')
            metrics.project_end_date = date_range.get('end')
            metrics.project_duration_days = self._calculate_duration(
                metrics.project_start_date,
                metrics.project_end_date
            )
        
        # Calculate commit frequency
        if metrics.project_duration_days and metrics.project_duration_days > 0:
            metrics.commit_frequency = round(
                metrics.total_commits / metrics.project_duration_days,
                2
            )
        
        # Process contributors
        contributors_data = git_analysis.get('contributors', [])
        metrics.total_contributors = len(contributors_data)
        
        for contrib_data in contributors_data:
            contributor = self._process_contributor(contrib_data, git_analysis)
            metrics.contributors.append(contributor)
        
        # Extract languages from code analysis
        if code_analysis:
            languages = code_analysis.get('languages', {})
            if isinstance(languages, dict):
                metrics.languages_detected = set(languages.keys())
            elif isinstance(languages, list):
                metrics.languages_detected = set(lang.get('name', '') for lang in languages)
        
        # Analyze activity breakdown from files
        if parse_result and hasattr(parse_result, 'files'):
            self._analyze_activity_breakdown(metrics, parse_result.files, code_analysis)
        elif code_analysis and 'file_details' in code_analysis:
            # Fallback to code analysis file details
            self._analyze_activity_from_code_analysis(metrics, code_analysis)
        
        return metrics
    
    def _process_contributor(
        self,
        contrib_data: Dict[str, Any],
        git_analysis: Dict[str, Any]
    ) -> ContributorMetrics:
        """Process individual contributor data."""
        contributor = ContributorMetrics(
            name=contrib_data.get('name', 'Unknown'),
            email=contrib_data.get('email'),
            commits=contrib_data.get('commits', 0),
            commit_percentage=contrib_data.get('percent', 0.0),
        )
        
        # Set date range (use project dates as fallback)
        date_range = git_analysis.get('date_range')
        if date_range:
            contributor.first_commit_date = date_range.get('start')
            contributor.last_commit_date = date_range.get('end')
        
        # Estimate active days from timeline
        timeline = git_analysis.get('timeline', [])
        if timeline:
            # Count months with activity
            contributor.active_days = len(timeline) * 15  # Rough estimate: 15 days per active month
        
        return contributor
    
    def _calculate_duration(
        self,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Optional[int]:
        """Calculate project duration in days."""
        if not start_date or not end_date:
            return None
        
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            return (end - start).days + 1
        except (ValueError, AttributeError) as exc:
            self.logger.warning(f"Failed to parse dates: {exc}")
            return None
    
    def _classify_file_activity(self, file_path: str) -> str:
        """
        Classify file into activity type.
        
        Returns: "test", "documentation", "design", "config", or "code"
        """
        file_path_lower = file_path.lower()
        
        # Check test first (most specific)
        if self._test_regex.search(file_path_lower):
            return "test"
        # Check config before doc (requirements.txt is config, not doc)
        elif self._config_regex.search(file_path_lower):
            return "config"
        elif self._doc_regex.search(file_path_lower):
            return "documentation"
        elif self._design_regex.search(file_path_lower):
            return "design"
        else:
            return "code"
    
    def _analyze_activity_breakdown(
        self,
        metrics: ProjectContributionMetrics,
        files: List[Any],
        code_analysis: Optional[Dict[str, Any]]
    ):
        """Analyze activity breakdown from file list."""
        activity_counter = defaultdict(int)
        
        for file_obj in files:
            # Get file path
            if hasattr(file_obj, 'path'):
                file_path = file_obj.path
            elif isinstance(file_obj, dict):
                file_path = file_obj.get('path', '')
            else:
                continue
            
            # Classify activity type
            activity_type = self._classify_file_activity(file_path)
            
            # Get line count from code analysis if available
            lines = 0
            if code_analysis and 'file_details' in code_analysis:
                for file_detail in code_analysis['file_details']:
                    if file_detail.get('path') == file_path:
                        lines = file_detail.get('metrics', {}).get('code_lines', 0)
                        break
            
            # If no line count from code analysis, estimate from file size
            if lines == 0 and hasattr(file_obj, 'size_bytes'):
                # Rough estimate: 50 bytes per line
                lines = max(1, file_obj.size_bytes // 50)
            elif lines == 0:
                lines = 1  # Minimum count for presence
            
            activity_counter[activity_type] += lines
        
        # Update activity breakdown
        metrics.overall_activity_breakdown.code_lines = activity_counter.get('code', 0)
        metrics.overall_activity_breakdown.test_lines = activity_counter.get('test', 0)
        metrics.overall_activity_breakdown.documentation_lines = activity_counter.get('documentation', 0)
        metrics.overall_activity_breakdown.design_lines = activity_counter.get('design', 0)
        metrics.overall_activity_breakdown.config_lines = activity_counter.get('config', 0)
    
    def _analyze_activity_from_code_analysis(
        self,
        metrics: ProjectContributionMetrics,
        code_analysis: Dict[str, Any]
    ):
        """Analyze activity breakdown from code analysis data only."""
        activity_counter = defaultdict(int)
        
        for file_detail in code_analysis.get('file_details', []):
            file_path = file_detail.get('path', '')
            activity_type = self._classify_file_activity(file_path)
            
            lines = file_detail.get('metrics', {}).get('code_lines', 0)
            if lines == 0:
                lines = file_detail.get('metrics', {}).get('lines', 1)
            
            activity_counter[activity_type] += lines
        
        # Update activity breakdown
        metrics.overall_activity_breakdown.code_lines = activity_counter.get('code', 0)
        metrics.overall_activity_breakdown.test_lines = activity_counter.get('test', 0)
        metrics.overall_activity_breakdown.documentation_lines = activity_counter.get('documentation', 0)
        metrics.overall_activity_breakdown.design_lines = activity_counter.get('design', 0)
        metrics.overall_activity_breakdown.config_lines = activity_counter.get('config', 0)
    
    def _analyze_non_git_project(
        self,
        code_analysis: Optional[Dict[str, Any]],
        parse_result: Optional[Any]
    ) -> ProjectContributionMetrics:
        """
        Analyze projects without Git history.
        
        Uses file metadata, activity breakdown, and code structure analysis.
        """
        self.logger.info("Analyzing non-Git project using file-based metrics")
        
        # Determine project path
        project_path = str(parse_result.base_path) if parse_result and hasattr(parse_result, 'base_path') else 'unknown'
        
        # Create metrics with required fields
        metrics = ProjectContributionMetrics(
            project_path=project_path,
            project_type="individual",  # Default to individual (no version control = likely single developer)
            total_commits=0,
            total_contributors=1,
        )
        
        # Create a single "Project Author" contributor
        author = ContributorMetrics(
            name="Project Author",
            email=None,
            commits=0,
            commit_percentage=100.0,
        )
        
        # Try to extract dates from file metadata
        if parse_result and hasattr(parse_result, 'files'):
            dates = self._extract_file_dates(parse_result.files)
            if dates:
                author.first_commit_date = dates['earliest']
                author.last_commit_date = dates['latest']
                metrics.project_start_date = dates['earliest']
                metrics.project_end_date = dates['latest']
                metrics.project_duration_days = self._calculate_duration(
                    dates['earliest'],
                    dates['latest']
                )
                # Estimate active days as ~30% of duration (conservative estimate)
                if metrics.project_duration_days:
                    author.active_days = max(1, int(metrics.project_duration_days * 0.3))
        
        metrics.contributors.append(author)
        
        # Extract languages from code analysis
        if code_analysis:
            languages = code_analysis.get('languages', {})
            if isinstance(languages, dict):
                metrics.languages_detected = set(languages.keys())
            elif isinstance(languages, list):
                metrics.languages_detected = set(lang.get('name', '') for lang in languages)
        
        # Analyze activity breakdown from files (this is the key metric for non-Git projects)
        if parse_result and hasattr(parse_result, 'files'):
            self._analyze_activity_breakdown(metrics, parse_result.files, code_analysis)
        elif code_analysis and 'file_details' in code_analysis:
            self._analyze_activity_from_code_analysis(metrics, code_analysis)
        
        # Calculate "commit" frequency as a proxy (files analyzed per day)
        if metrics.project_duration_days and metrics.project_duration_days > 0:
            # Use total lines as a proxy for "work done"
            total_lines = metrics.overall_activity_breakdown.total_lines
            if total_lines > 0:
                # Rough estimate: 100 lines = 1 day of work
                estimated_work_days = max(1, total_lines // 100)
                metrics.commit_frequency = estimated_work_days / metrics.project_duration_days
        
        self.logger.info(
            f"Non-Git analysis complete: {metrics.total_contributors} contributor, "
            f"{metrics.overall_activity_breakdown.total_lines} total lines analyzed"
        )
        
        return metrics
    
    def _extract_file_dates(self, files: List[Any]) -> Optional[Dict[str, str]]:
        """
        Extract earliest and latest dates from file metadata.
        
        Returns dict with 'earliest' and 'latest' ISO date strings, or None.
        """
        dates = []
        
        for file_obj in files:
            # Try to get modification time
            if hasattr(file_obj, 'modified_time') and file_obj.modified_time:
                dates.append(file_obj.modified_time)
            elif hasattr(file_obj, 'created_time') and file_obj.created_time:
                dates.append(file_obj.created_time)
            elif isinstance(file_obj, dict):
                if 'modified_time' in file_obj:
                    dates.append(file_obj['modified_time'])
                elif 'created_time' in file_obj:
                    dates.append(file_obj['created_time'])
        
        if not dates:
            return None
        
        try:
            # Parse all dates and find min/max
            parsed_dates = []
            for date_str in dates:
                try:
                    parsed = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    parsed_dates.append(parsed)
                except (ValueError, AttributeError):
                    continue
            
            if not parsed_dates:
                return None
            
            earliest = min(parsed_dates)
            latest = max(parsed_dates)
            
            return {
                'earliest': earliest.isoformat(),
                'latest': latest.isoformat()
            }
        except Exception as exc:
            self.logger.warning(f"Failed to extract file dates: {exc}")
            return None
    
    def export_to_dict(self, metrics: ProjectContributionMetrics) -> Dict[str, Any]:
        """
        Export contribution metrics to dictionary for JSON serialization.
        
        Args:
            metrics: ProjectContributionMetrics to export
            
        Returns:
            Dictionary representation
        """
        return {
            "project_path": metrics.project_path,
            "project_type": metrics.project_type,
            "is_solo_project": metrics.is_solo_project,
            "total_commits": metrics.total_commits,
            "total_contributors": metrics.total_contributors,
            "project_duration_days": metrics.project_duration_days,
            "project_start_date": metrics.project_start_date,
            "project_end_date": metrics.project_end_date,
            "commit_frequency": metrics.commit_frequency,
            "languages_detected": list(metrics.languages_detected),
            "overall_activity_breakdown": {
                "lines": {
                    "code": metrics.overall_activity_breakdown.code_lines,
                    "test": metrics.overall_activity_breakdown.test_lines,
                    "documentation": metrics.overall_activity_breakdown.documentation_lines,
                    "design": metrics.overall_activity_breakdown.design_lines,
                    "config": metrics.overall_activity_breakdown.config_lines,
                    "total": metrics.overall_activity_breakdown.total_lines,
                },
                "percentages": metrics.overall_activity_breakdown.percentages,
            },
            "contributors": [
                {
                    "name": contrib.name,
                    "email": contrib.email,
                    "commits": contrib.commits,
                    "commit_percentage": contrib.commit_percentage,
                    "first_commit_date": contrib.first_commit_date,
                    "last_commit_date": contrib.last_commit_date,
                    "active_days": contrib.active_days,
                    "contribution_frequency": contrib.contribution_frequency,
                    "days_active_span": contrib.days_active_span,
                    "activity_breakdown": {
                        "lines": {
                            "code": contrib.activity_breakdown.code_lines,
                            "test": contrib.activity_breakdown.test_lines,
                            "documentation": contrib.activity_breakdown.documentation_lines,
                            "design": contrib.activity_breakdown.design_lines,
                            "config": contrib.activity_breakdown.config_lines,
                        },
                        "percentages": contrib.activity_breakdown.percentages,
                    },
                    "files_touched": list(contrib.files_touched),
                    "languages_used": list(contrib.languages_used),
                }
                for contrib in metrics.contributors
            ],
            "primary_contributor": {
                "name": metrics.primary_contributor.name if metrics.primary_contributor else None,
                "commits": metrics.primary_contributor.commits if metrics.primary_contributor else 0,
            } if metrics.primary_contributor else None,
        }
