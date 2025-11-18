"""
Project Detector Module

Detects and separates multiple projects within a directory.
Identifies project boundaries based on common markers like package files,
build configurations, and directory structure.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    """Information about a detected project."""
    name: str
    path: Path
    project_type: str  # e.g., "python", "javascript", "java", "multi-language"
    root_indicators: List[str]  # Files that indicate this is a project root
    description: Optional[str] = None


class ProjectDetector:
    """
    Detects project boundaries within a directory tree.
    
    A project is identified by the presence of specific marker files
    that indicate a project root (e.g., package.json, requirements.txt, pom.xml).
    """
    
    def __init__(self):
        """Initialize the project detector with marker patterns."""
        # Project marker files - presence indicates a project root
        self.project_markers = {
            'python': [
                'setup.py',
                'pyproject.toml',
                'requirements.txt',
                'Pipfile',
                'poetry.lock',
                'setup.cfg',
                'environment.yml',
                'conda.yaml'
            ],
            'javascript': [
                'package.json',
                'yarn.lock',
                'package-lock.json',
                'pnpm-lock.yaml'
            ],
            'typescript': [
                'tsconfig.json',
                'package.json'
            ],
            'java': [
                'pom.xml',
                'build.gradle',
                'build.gradle.kts',
                'settings.gradle'
            ],
            'ruby': [
                'Gemfile',
                'Gemfile.lock',
                '.gemspec'
            ],
            'go': [
                'go.mod',
                'go.sum'
            ],
            'rust': [
                'Cargo.toml',
                'Cargo.lock'
            ],
            'php': [
                'composer.json',
                'composer.lock'
            ],
            'csharp': [
                '.csproj',
                '.sln',
                'packages.config'
            ],
            'general': [
                'Dockerfile',
                'docker-compose.yml',
                'docker-compose.yaml',
                'Makefile',
                '.git',
                'README.md'
            ]
        }
        
        # Directories that should be excluded from traversal
        self.excluded_dirs = {
            'node_modules',
            '__pycache__',
            '.git',
            '.svn',
            '.hg',
            'venv',
            '.venv',
            'env',
            '.env',
            'virtualenv',
            'build',
            'dist',
            'target',
            '.idea',
            '.vscode',
            '.pytest_cache',
            '.mypy_cache',
            '__MACOSX',
            'coverage',
            '.next',
            'out',
            '.nuxt',
            '.output'
        }
    
    def detect_projects(self, root_path: Path, max_depth: int = 5) -> List[ProjectInfo]:
        """
        Detect all projects within a directory tree.
        
        Args:
            root_path: Root directory to search
            max_depth: Maximum depth to traverse (prevents infinite recursion)
            
        Returns:
            List of detected ProjectInfo objects
        """
        if not root_path.is_dir():
            logger.warning(f"Path is not a directory: {root_path}")
            return []
        
        projects = []
        visited_roots = set()
        
        self._scan_directory(root_path, root_path, projects, visited_roots, 0, max_depth)
        
        # If no projects found, treat the root as a single project
        if not projects:
            logger.info("No project markers found, treating root as single project")
            projects.append(ProjectInfo(
                name=root_path.name,
                path=root_path,
                project_type="unknown",
                root_indicators=[],
                description="No specific project markers found"
            ))
        
        logger.info(f"Detected {len(projects)} project(s) in {root_path}")
        return projects
    
    def _scan_directory(
        self,
        current_path: Path,
        root_path: Path,
        projects: List[ProjectInfo],
        visited_roots: Set[Path],
        depth: int,
        max_depth: int
    ):
        """Recursively scan directory for project markers."""
        
        if depth > max_depth:
            return
        
        # Check if this directory has already been identified as a project root
        if current_path in visited_roots:
            return
        
        # Check for project markers in current directory
        markers_found = self._find_project_markers(current_path)
        
        if markers_found:
            # This is a project root
            project_type = self._determine_project_type(markers_found)
            
            project_info = ProjectInfo(
                name=current_path.name,
                path=current_path,
                project_type=project_type,
                root_indicators=markers_found,
                description=self._generate_project_description(project_type, markers_found)
            )
            
            projects.append(project_info)
            visited_roots.add(current_path)
            
            logger.debug(f"Found {project_type} project at: {current_path}")
            
            # Don't traverse deeper into this project's dependencies
            # But do check immediate subdirectories for nested projects
            try:
                for subdir in current_path.iterdir():
                    if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                        self._scan_directory(subdir, root_path, projects, visited_roots, depth + 1, max_depth)
            except PermissionError:
                logger.debug(f"Permission denied: {current_path}")
        else:
            # Not a project root, continue scanning subdirectories
            try:
                for subdir in current_path.iterdir():
                    if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                        self._scan_directory(subdir, root_path, projects, visited_roots, depth + 1, max_depth)
            except PermissionError:
                logger.debug(f"Permission denied: {current_path}")
    
    def _find_project_markers(self, directory: Path) -> List[str]:
        """Find project marker files in a directory."""
        markers = []
        
        try:
            dir_contents = set(p.name for p in directory.iterdir())
            
            for language, marker_files in self.project_markers.items():
                for marker in marker_files:
                    if marker in dir_contents:
                        markers.append(marker)
        except PermissionError:
            logger.debug(f"Permission denied: {directory}")
        
        return markers
    
    def _determine_project_type(self, markers: List[str]) -> str:
        """Determine project type based on markers found."""
        
        type_scores = {lang: 0 for lang in self.project_markers.keys()}
        
        for marker in markers:
            for lang, lang_markers in self.project_markers.items():
                if marker in lang_markers:
                    # Weight certain markers more heavily
                    if marker in ['package.json', 'pom.xml', 'setup.py', 'Cargo.toml', 'go.mod']:
                        type_scores[lang] += 3
                    else:
                        type_scores[lang] += 1
        
        # Find the type with highest score
        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]
        
        # If multiple types have high scores, it's multi-language
        high_scoring_types = [t for t, score in type_scores.items() if score >= 2 and score >= best_score - 1]
        
        if len(high_scoring_types) > 1:
            return "multi-language"
        elif best_score > 0:
            return best_type
        else:
            return "unknown"
    
    def _generate_project_description(self, project_type: str, markers: List[str]) -> str:
        """Generate a description of the project based on markers."""
        
        descriptions = {
            'python': "Python project",
            'javascript': "JavaScript/Node.js project",
            'typescript': "TypeScript project",
            'java': "Java project",
            'ruby': "Ruby project",
            'go': "Go project",
            'rust': "Rust project",
            'php': "PHP project",
            'csharp': "C# project",
            'multi-language': "Multi-language project",
            'unknown': "Project"
        }
        
        base_desc = descriptions.get(project_type, "Project")
        
        # Add specific details based on markers
        details = []
        if 'Dockerfile' in markers or 'docker-compose.yml' in markers or 'docker-compose.yaml' in markers:
            details.append("with Docker")
        if '.git' in markers:
            details.append("with Git")
        if 'Makefile' in markers:
            details.append("with Make")
        
        if details:
            return f"{base_desc} {', '.join(details)}"
        return base_desc
    
    def is_monorepo(self, projects: List[ProjectInfo]) -> bool:
        """Determine if the detected projects form a monorepo structure."""
        if len(projects) <= 1:
            return False
        
        # Check if projects share a common root and are organized in a structured way
        # Simple heuristic: if we found multiple projects in subdirectories, it's likely a monorepo
        return len(projects) > 1
    
    def get_project_structure_summary(self, projects: List[ProjectInfo]) -> str:
        """Generate a human-readable summary of the project structure."""
        
        if len(projects) == 0:
            return "No projects detected"
        elif len(projects) == 1:
            project = projects[0]
            return f"Single {project.project_type} project: {project.name}"
        else:
            # Multiple projects - likely a monorepo
            type_counts = {}
            for project in projects:
                type_counts[project.project_type] = type_counts.get(project.project_type, 0) + 1
            
            type_summary = ", ".join(f"{count} {ptype}" for ptype, count in sorted(type_counts.items()))
            return f"Monorepo with {len(projects)} projects: {type_summary}"
