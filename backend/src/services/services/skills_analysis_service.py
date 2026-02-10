"""
Skills Analysis Service

Provides skills extraction for the backend API.
Wraps the SkillsExtractor module and formats results for display.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

from analyzer.skills_extractor import SkillsExtractor, Skill, SkillEvidence
from analyzer.project_detector import ProjectDetector, ProjectInfo
from analyzer.llm.skill_progress_summary import (
    SkillProgressSummary,
    summarize_skill_progress,
)
from local_analysis.skill_progress_timeline import build_skill_progression

logger = logging.getLogger(__name__)


class SkillsAnalysisError(Exception):
    """Raised when skills analysis fails."""
    pass


class SkillsAnalysisService:
    """
    Service for extracting skills from project scans.
    
    This service bridges the backend API and the SkillsExtractor module,
    providing methods to extract skills from various sources and format
    them for display.
    """

    def __init__(self):
        """Initialize the skills analysis service."""
        self._extractor = SkillsExtractor()
        self._project_detector = ProjectDetector()
        self._detected_projects: List[ProjectInfo] = []
    
    def detect_projects(self, target_path: Path) -> List[ProjectInfo]:
        """Detect all projects within the target directory.
        
        Args:
            target_path: Path to scan for projects
            
        Returns:
            List of detected ProjectInfo objects
        """
        self._detected_projects = self._project_detector.detect_projects(target_path)
        return self._detected_projects
    
    def extract_skills(
        self,
        target_path: Path,
        code_analysis_result: Optional[Any] = None,
        git_analysis_result: Optional[Dict[str, Any]] = None,
        file_contents: Optional[Dict[str, str]] = None,
        include_chronological: bool = True,
    ) -> List[Skill]:
        """
        Extract skills from the provided project data.
        
        Args:
            target_path: Path to the project directory
            code_analysis_result: Optional CodeAnalyzer DirectoryResult
            git_analysis_result: Optional git analysis data
            file_contents: Optional dictionary mapping file paths to content
            include_chronological: Whether to extract git timestamps for chronological tracking
            
        Returns:
            List of extracted Skill objects
            
        Raises:
            SkillsAnalysisError: If extraction fails
        """
        try:
            # If no file contents provided, read source files from target
            if file_contents is None:
                file_contents = self._read_source_files(target_path)
            
            # Extract skills using all available data
            skills_dict = self._extractor.extract_skills(
                file_contents=file_contents,
                code_analysis=code_analysis_result,
                git_analysis=git_analysis_result,
                repo_path=str(target_path) if include_chronological else None,
            )
            
            # Convert dict to list
            skills = list(skills_dict.values())
            
            logger.info(f"Extracted {len(skills)} skills from project")
            return skills
            
        except Exception as exc:
            logger.error(f"Skills extraction failed: {exc}")
            raise SkillsAnalysisError(f"Failed to extract skills: {exc}") from exc
    
    def extract_skills_per_project(
        self,
        target_path: Path,
        code_analysis_result: Optional[Any] = None,
        git_analysis_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Extract skills separately for each detected project.
        
        Args:
            target_path: Path to the root directory containing projects
            code_analysis_result: Optional CodeAnalyzer DirectoryResult
            git_analysis_result: Optional git analysis data
            
        Returns:
            Dictionary mapping project paths to their skill extraction results
        """
        # Detect projects if not already done
        if not self._detected_projects:
            self.detect_projects(target_path)
        
        results = {}
        
        for project in self._detected_projects:
            logger.info(f"Extracting skills for project: {project.name} at {project.path}")
            
            try:
                # Create a new extractor for each project
                project_extractor = SkillsExtractor()
                
                # Read files only from this project's directory
                file_contents = self._read_source_files(project.path)
                
                # Extract skills for this project
                skills_dict = project_extractor.extract_skills(
                    file_contents=file_contents,
                    code_analysis=None,  # TODO: Filter code analysis by project
                    git_analysis=git_analysis_result if str(project.path) == str(target_path) else None,
                    repo_path=str(project.path)
                )
                
                skills = list(skills_dict.values())
                
                results[str(project.path)] = {
                    "project_info": {
                        "name": project.name,
                        "path": str(project.path),
                        "type": project.project_type,
                        "description": project.description,
                        "markers": project.root_indicators
                    },
                    "skills": skills,
                    "skill_count": len(skills),
                    "export": project_extractor.export_to_dict()
                }
                
            except Exception as exc:
                logger.error(f"Failed to extract skills for {project.name}: {exc}")
                results[str(project.path)] = {
                    "project_info": {
                        "name": project.name,
                        "path": str(project.path),
                        "type": project.project_type
                    },
                    "error": str(exc)
                }
        
        return results

    def _read_source_files(self, target_path: Path, max_file_size: int = 500 * 1024) -> Dict[str, str]:
        """
        Read source code files from the target directory.
        
        Args:
            target_path: Directory to scan for source files
            max_file_size: Maximum file size to read (default 500KB)
            
        Returns:
            Dictionary mapping relative file paths to content
        """
        file_contents = {}
        
        # Source code extensions to include
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp'}
        
        # Directories to exclude
        excluded_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'env', 'build', 'dist'}
        
        if not target_path.is_dir():
            logger.warning(f"Target path is not a directory: {target_path}")
            return file_contents
        
        try:
            for file_path in target_path.rglob('*'):
                # Skip if in excluded directory
                if any(excluded in file_path.parts for excluded in excluded_dirs):
                    continue
                
                # Skip if not a file or wrong extension
                if not file_path.is_file() or file_path.suffix not in extensions:
                    continue
                
                # Skip if too large
                if file_path.stat().st_size > max_file_size:
                    logger.debug(f"Skipping large file: {file_path.name} ({file_path.stat().st_size} bytes)")
                    continue
                
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    relative_path = str(file_path.relative_to(target_path))
                    file_contents[relative_path] = content
                except Exception as exc:
                    logger.debug(f"Failed to read {file_path}: {exc}")
                    continue
        
        except Exception as exc:
            logger.error(f"Error reading source files: {exc}")
        
        logger.info(f"Read {len(file_contents)} source files from {target_path}")
        return file_contents

    def format_summary(self, skills: List[Skill]) -> str:
        """
        Format skills as a summary text for display in the CLI.
        
        Args:
            skills: List of extracted Skill objects
            
        Returns:
            Formatted string with skills summary
        """
        if not skills:
            return "No skills detected in this project.\n"
        
        # Map short category names to display names
        category_display_names = {
            "oop": "Object-Oriented Programming",
            "data_structures": "Data Structures",
            "algorithms": "Algorithms",
            "patterns": "Design Patterns",
            "practices": "Best Practices",
            "frameworks": "Frameworks & Libraries",
            "databases": "Database Technologies",
            "architecture": "Software Architecture"
        }
        
        # Group skills by category
        categorized: Dict[str, List[Skill]] = {}
        for skill in skills:
            # Get display name for category
            display_name = category_display_names.get(skill.category, skill.category)
            if display_name not in categorized:
                categorized[display_name] = []
            categorized[display_name].append(skill)
        
        # Build summary text
        lines = [f"Skills Detected: {len(skills)} total\n"]
        lines.append("=" * 60)
        
        # Sort categories for consistent display
        category_order = [
            "Object-Oriented Programming",
            "Data Structures",
            "Algorithms",
            "Design Patterns",
            "Frameworks & Libraries",
            "Database Technologies",
            "Software Architecture",
            "Best Practices"
        ]
        
        for category in category_order:
            if category not in categorized:
                continue
            
            category_skills = categorized[category]
            # Sort by proficiency score (highest first)
            category_skills.sort(key=lambda s: s.proficiency_score, reverse=True)
            
            lines.append(f"\n{category} ({len(category_skills)} skills):")
            lines.append("-" * 60)
            
            for skill in category_skills:
                evidence_count = len(skill.evidence)
                proficiency = skill.proficiency_score
                
                # Format proficiency level
                if proficiency >= 0.8:
                    level = "Advanced"
                elif proficiency >= 0.5:
                    level = "Intermediate"
                else:
                    level = "Beginner"
                
                lines.append(f"  • {skill.name} ({level}, {evidence_count} instances)")
                
                if skill.description:
                    lines.append(f"    {skill.description}")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_detailed_report(self, skills: List[Skill], max_evidence_per_skill: int = 3) -> str:
        """
        Format a detailed report with evidence for each skill.
        
        Args:
            skills: List of extracted Skill objects
            max_evidence_per_skill: Maximum evidence items to show per skill
            
        Returns:
            Formatted detailed report string
        """
        if not skills:
            return "No skills detected.\n"
        
        # Sort by proficiency (highest first)
        sorted_skills = sorted(skills, key=lambda s: s.proficiency_score, reverse=True)
        
        lines = [f"Detailed Skills Report: {len(skills)} skills\n"]
        lines.append("=" * 80)
        
        for i, skill in enumerate(sorted_skills, 1):
            lines.append(f"\n{i}. {skill.name}")
            lines.append(f"   Category: {skill.category}")
            lines.append(f"   Proficiency: {skill.proficiency_score:.2f}")
            
            if skill.description:
                lines.append(f"   Description: {skill.description}")
            
            # Show sample evidence
            if skill.evidence:
                evidence_to_show = skill.evidence[:max_evidence_per_skill]
                lines.append(f"   Evidence ({len(skill.evidence)} instances, showing {len(evidence_to_show)}):")
                
                for ev in evidence_to_show:
                    lines.append(f"     - {ev.description}")
                    if ev.file_path:
                        location = f"{ev.file_path}"
                        if ev.line_number is not None:
                            location += f":{ev.line_number}"
                        lines.append(f"       Location: {location}")
                    lines.append(f"       Confidence: {ev.confidence:.2f}")
            
            lines.append("-" * 80)
        
        return "\n".join(lines)

    def get_chronological_overview(self) -> List[Dict[str, Any]]:
        """
        Get chronological overview of when skills were exercised.
        
        Returns:
            List of time periods with skills exercised in each period
        """
        return self._extractor.get_chronological_overview()

    def build_skill_progression(
        self,
        contribution_metrics: Optional[Any] = None,
        author_emails: Optional[set[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build a month-level skill progression timeline using existing analyses.

        Args:
            contribution_metrics: Optional ProjectContributionMetrics for commits/languages.
            author_emails: Optional set of author emails to filter git activity to a single contributor.

        Returns:
            Dict with timeline entries or None if no chronological data is available.
        """
        chronological = self.get_chronological_overview()
        if not chronological:
            return None

        progression = build_skill_progression(chronological, contribution_metrics, author_emails=author_emails)

        def _period_to_dict(period):
            return {
                "period_label": period.period_label,
                "commits": period.commits,
                "tests_changed": period.tests_changed,
                "skill_count": period.skill_count,
                "evidence_count": period.evidence_count,
                "top_skills": period.top_skills,
                "languages": period.languages,
                "contributors": period.contributors,
                "commit_messages": period.commit_messages,
                "top_files": period.top_files,
                "activity_types": period.activity_types,
                "period_languages": period.period_languages,
            }

        return {"timeline": [_period_to_dict(p) for p in progression.timeline]}

    def summarize_skill_progression(
        self,
        timeline: List[Dict[str, Any]],
        call_model: callable,
    ) -> SkillProgressSummary:
        """
        Summarize skill progression timeline using a provided model caller.

        Args:
            timeline: list of period entries.
            call_model: callable that takes a prompt and returns raw model text.

        Returns:
            SkillProgressSummary with narrative and bullet lists.
        """
        return summarize_skill_progress(timeline, call_model)
    
    def export_skills_data(self, skills: List[Skill]) -> Dict[str, Any]:
        """
        Export skills data in a format suitable for JSON export.
        
        Args:
            skills: List of extracted Skill objects
            
        Returns:
            Dictionary containing skills data for export
        """
        skills_data = {
            "total_skills": len(skills),
            "skills_by_category": {},
            "top_skills": [],
            "all_skills": [],
            "chronological_overview": self.get_chronological_overview()
        }
        
        # Categorize skills
        for skill in skills:
            if skill.category not in skills_data["skills_by_category"]:
                skills_data["skills_by_category"][skill.category] = []
            
            skill_dict = {
                "name": skill.name,
                "proficiency": skill.proficiency_score,
                "evidence_count": len(skill.evidence),
                "description": skill.description or ""
            }
            
            skills_data["skills_by_category"][skill.category].append(skill_dict)
            skills_data["all_skills"].append({
                **skill_dict,
                "category": skill.category
            })
        
        # Get top 10 skills by proficiency
        sorted_skills = sorted(skills, key=lambda s: s.proficiency_score, reverse=True)
        skills_data["top_skills"] = [
            {
                "name": s.name,
                "category": s.category,
                "proficiency": s.proficiency_score,
                "evidence_count": len(s.evidence)
            }
            for s in sorted_skills[:10]
        ]
        
        return skills_data

    def format_skills_summary(self, skills: List[Skill]) -> str:
        """Format a concise skills summary with key statistics.
        
        Args:
            skills: List of extracted Skill objects
            
        Returns:
            Formatted summary string
        """
        if not skills:
            return "No skills detected."
        
        # Category mapping
        category_display = {
            "oop": "Object-Oriented Programming",
            "data_structures": "Data Structures",
            "algorithms": "Algorithms",
            "patterns": "Design Patterns",
            "practices": "Best Practices",
            "frameworks": "Frameworks & Libraries",
            "databases": "Database Technologies",
            "architecture": "Software Architecture"
        }
        
        # Calculate stats
        total_proficiency = sum(s.proficiency_score for s in skills)
        avg_proficiency = total_proficiency / len(skills)
        
        # Group by category
        from collections import defaultdict
        category_counts = defaultdict(int)
        for skill in skills:
            category_counts[skill.category] += 1
        
        # Find top skills
        sorted_skills = sorted(skills, key=lambda s: s.proficiency_score, reverse=True)
        top_3 = sorted_skills[:3]
        
        # Build summary
        lines = []
        lines.append("[b]Skills Overview[/b]")
        lines.append(f"Total skills detected: {len(skills)}")
        lines.append(f"Average proficiency: {avg_proficiency:.2f}")
        lines.append("")
        lines.append("[b]By Category[/b]")
        for cat_key, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            display_name = category_display.get(cat_key, cat_key)
            lines.append(f"- {display_name}: {count} skills")
        lines.append("")
        lines.append("[b]Top Skills[/b]")
        for i, skill in enumerate(top_3, 1):
            level = "Advanced" if skill.proficiency_score >= 0.8 else "Intermediate" if skill.proficiency_score >= 0.5 else "Beginner"
            lines.append(f"{i}. {skill.name} ({level}, proficiency: {skill.proficiency_score:.2f})")
            if skill.description:
                lines.append(f"   {skill.description}")
        
        return "\n".join(lines)

    def format_skills_paragraph(self, skills: List[Skill]) -> str:
        """Generate a narrative paragraph summarizing the skills analysis.
        
        Args:
            skills: List of extracted Skill objects
            
        Returns:
            A paragraph-style summary of the skills
        """
        if not skills:
            return "No programming skills were detected in the analyzed code."
        
        # Category mapping
        category_display = {
            "oop": "object-oriented programming",
            "data_structures": "data structures",
            "algorithms": "algorithms",
            "patterns": "design patterns",
            "practices": "best practices",
            "frameworks": "frameworks and libraries",
            "databases": "database technologies",
            "architecture": "software architecture"
        }
        
        # Calculate stats
        total_proficiency = sum(s.proficiency_score for s in skills)
        avg_proficiency = total_proficiency / len(skills)
        
        # Group by category
        from collections import defaultdict
        category_counts = defaultdict(int)
        for skill in skills:
            category_counts[skill.category] += 1
        
        # Determine proficiency level
        if avg_proficiency >= 0.75:
            proficiency_desc = "demonstrates advanced proficiency"
        elif avg_proficiency >= 0.6:
            proficiency_desc = "shows solid proficiency"
        elif avg_proficiency >= 0.4:
            proficiency_desc = "exhibits moderate proficiency"
        else:
            proficiency_desc = "displays foundational proficiency"
        
        # Get top skill
        top_skill = max(skills, key=lambda s: s.proficiency_score)
        
        # Build category list (top 3)
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        category_names = [category_display.get(cat, cat) for cat, _ in sorted_categories]
        
        # Construct paragraph
        if len(category_names) == 1:
            categories_text = category_names[0]
        elif len(category_names) == 2:
            categories_text = f"{category_names[0]} and {category_names[1]}"
        else:
            categories_text = f"{', '.join(category_names[:-1])}, and {category_names[-1]}"
        
        paragraph = (
            f"The analysis detected {len(skills)} programming skill{'' if len(skills) == 1 else 's'} "
            f"across the codebase, which {proficiency_desc} with an average score of {avg_proficiency:.2f}. "
            f"The code primarily showcases expertise in {categories_text}, "
            f"with '{top_skill.name}' standing out as the most prominent skill "
            f"(proficiency: {top_skill.proficiency_score:.2f}). "
        )
        
        # Add context about category distribution
        if len(category_counts) > 3:
            paragraph += f"Skills span {len(category_counts)} different categories, indicating a well-rounded technical foundation."
        elif len(category_counts) > 1:
            paragraph += "The skill distribution reflects a balanced approach to software development."
        else:
            paragraph += "The analysis reveals a focused specialization in this area."
        
        return paragraph

    def format_chronological_overview(self) -> str:
        """
        Format chronological overview of skills for display.
        
        Returns:
            Formatted string showing skills by time period
        """
        overview = self.get_chronological_overview()
        
        if not overview:
            return "No chronological data available. Skills were detected but timestamps are not available."
        
        lines = ["[b]Skills Timeline[/b]"]
        lines.append("Skills exercised over time (by month):")
        lines.append("=" * 60)
        
        for entry in overview:
            period = entry['period']
            skill_count = entry['skill_count']
            evidence_count = entry['evidence_count']
            skills_list = entry['skills_exercised']
            
            lines.append(f"\n[b]{period}[/b] ({skill_count} skills, {evidence_count} instances)")
            for skill_name in skills_list[:5]:  # Show top 5 skills per period
                lines.append(f"  • {skill_name}")
            
            if len(skills_list) > 5:
                lines.append(f"  ... and {len(skills_list) - 5} more")
        
        lines.append("\\n" + "=" * 60)
        return "\\n".join(lines)
    
    def format_skill_progression(self) -> str:
        """Format skill progression over time showing how skills evolved.
        
        Returns:
            Formatted string showing skill progression
        """
        progression = self._extractor.get_skill_progression()
        
        if not progression:
            return "No progression data available."
        
        lines = ["[b]Skill Progression[/b]"]
        lines.append("How your skills evolved over time:")
        lines.append("=" * 60)
        
        # Show progression for top skills
        top_skills = self._extractor.get_top_skills(limit=5)
        top_skill_names = {s.name for s in top_skills}
        
        for skill_name in top_skill_names:
            if skill_name not in progression:
                continue
            
            skill_timeline = progression[skill_name]
            lines.append(f"\\n[b]{skill_name}[/b]")
            
            # Group by period to show progression
            periods = {}
            for entry in skill_timeline:
                period = entry['period']
                if period not in periods:
                    periods[period] = entry
            
            # Show progression through periods
            for period in sorted(periods.keys()):
                entry = periods[period]
                level = "Beginner" if entry['proficiency'] < 0.5 else "Intermediate" if entry['proficiency'] < 0.8 else "Advanced"
                lines.append(f"  {period}: {level} (used {entry['evidence_count']}x)")
        
        lines.append("\\n" + "=" * 60)
        return "\\n".join(lines)
    
    def format_skill_adoption(self) -> str:
        """Format skill adoption timeline showing when skills were first learned.
        
        Returns:
            Formatted string showing skill adoption timeline
        """
        adoption = self._extractor.get_skill_adoption_timeline()
        
        if not adoption:
            return "No adoption timeline available."
        
        lines = ["[b]Skill Acquisition Timeline[/b]"]
        lines.append("When you first started using each skill:")
        lines.append("=" * 60)
        
        # Group by period
        by_period = defaultdict(list)
        for entry in adoption:
            by_period[entry['first_used_period']].append(entry)
        
        for period in sorted(by_period.keys()):
            skills_in_period = by_period[period]
            lines.append(f"\\n[b]{period}[/b] ({len(skills_in_period)} new skills)")
            
            for entry in sorted(skills_in_period, key=lambda x: x['current_proficiency'], reverse=True):
                level = "Advanced" if entry['current_proficiency'] >= 0.8 else "Intermediate" if entry['current_proficiency'] >= 0.5 else "Beginner"
                lines.append(f"  • {entry['skill_name']} (now {level}, used {entry['total_usage']}x)")
        
        lines.append("\\n" + "=" * 60)
        return "\\n".join(lines)
    
    def format_multi_project_summary(self, projects_results: Dict[str, Dict[str, Any]]) -> str:
        """Format summary for multiple projects.
        
        Args:
            projects_results: Dictionary of project results from extract_skills_per_project
            
        Returns:
            Formatted summary string
        """
        if not projects_results:
            return "No projects analyzed."
        
        lines = ["[b]Multi-Project Analysis[/b]"]
        lines.append(f"Analyzed {len(projects_results)} project(s):")
        lines.append("=" * 80)
        
        for project_path, result in projects_results.items():
            if "error" in result:
                project_info = result["project_info"]
                lines.append(f"\\n[b]{project_info['name']}[/b] ({project_info['type']})")
                lines.append(f"  Path: {project_info['path']}")
                lines.append(f"  [red]Error: {result['error']}[/red]")
                continue
            
            project_info = result["project_info"]
            skills = result["skills"]
            
            lines.append(f"\\n[b]{project_info['name']}[/b] ({project_info['type']})")
            lines.append(f"  Path: {project_info['path']}")
            
            if project_info.get('description'):
                lines.append(f"  Description: {project_info['description']}")
            
            lines.append(f"  Skills detected: {len(skills)}")
            
            if skills:
                # Show top 3 skills for this project
                sorted_skills = sorted(skills, key=lambda s: s.proficiency_score, reverse=True)[:3]
                lines.append("  Top skills:")
                for skill in sorted_skills:
                    level = "Advanced" if skill.proficiency_score >= 0.8 else "Intermediate" if skill.proficiency_score >= 0.5 else "Beginner"
                    lines.append(f"    • {skill.name} ({level})")
            
            lines.append("")  # Blank line between projects
        
        lines.append("=" * 80)
        
        # Add aggregate statistics
        total_skills = sum(result.get("skill_count", 0) for result in projects_results.values() if "error" not in result)
        unique_skills = set()
        for result in projects_results.values():
            if "error" not in result and "skills" in result:
                unique_skills.update(s.name for s in result["skills"])
        
        lines.append(f"\\n[b]Aggregate Statistics[/b]")
        lines.append(f"Total skill instances: {total_skills}")
        lines.append(f"Unique skills: {len(unique_skills)}")
        
        return "\\n".join(lines)
    
    def get_skills_summary_stats(self, skills: List[Skill]) -> Dict[str, Any]:
        """
        Generate summary statistics for skills.
        
        Args:
            skills: List of extracted Skill objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not skills:
            return {
                "total_skills": 0,
                "average_proficiency": 0.0,
                "categories": [],
                "top_skill": None
            }
        
        # Calculate statistics
        total_proficiency = sum(s.proficiency_score for s in skills)
        avg_proficiency = total_proficiency / len(skills)
        
        # Get unique categories
        categories = list(set(s.category for s in skills))
        
        # Find top skill
        top_skill = max(skills, key=lambda s: s.proficiency_score)
        
        return {
            "total_skills": len(skills),
            "average_proficiency": round(avg_proficiency, 2),
            "categories": categories,
            "top_skill": {
                "name": top_skill.name,
                "category": top_skill.category,
                "proficiency": top_skill.proficiency_score
            }
        }
