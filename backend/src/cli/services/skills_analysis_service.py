"""
Skills Analysis Service

Provides skills extraction for the Textual CLI application.
Wraps the SkillsExtractor module and formats results for display.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from ...analyzer.skills_extractor import SkillsExtractor, Skill, SkillEvidence

logger = logging.getLogger(__name__)


class SkillsAnalysisError(Exception):
    """Raised when skills analysis fails."""
    pass


class SkillsAnalysisService:
    """
    Service for extracting skills from project scans.
    
    This service bridges the Textual CLI and the SkillsExtractor module,
    providing methods to extract skills from various sources and format
    them for display.
    """

    def __init__(self):
        """Initialize the skills analysis service."""
        self._extractor = SkillsExtractor()

    def extract_skills(
        self,
        target_path: Path,
        code_analysis_result: Optional[Any] = None,
        git_analysis_result: Optional[Dict[str, Any]] = None,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> List[Skill]:
        """
        Extract skills from the provided project data.
        
        Args:
            target_path: Path to the project directory
            code_analysis_result: Optional CodeAnalyzer DirectoryResult
            git_analysis_result: Optional git analysis data
            file_contents: Optional dictionary mapping file paths to content
            
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
            )
            
            # Convert dict to list
            skills = list(skills_dict.values())
            
            logger.info(f"Extracted {len(skills)} skills from project")
            return skills
            
        except Exception as exc:
            logger.error(f"Skills extraction failed: {exc}")
            raise SkillsAnalysisError(f"Failed to extract skills: {exc}") from exc

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
            "practices": "Best Practices"
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
            "all_skills": []
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
