"""
Project Detector Module

Detects and separates multiple projects within a directory.
Identifies project boundaries based on common markers like package files,
build configurations, and directory structure.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
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

    Detection uses three priority-ordered rules:
      1. Git root  — if the scan root has a .git directory, the whole tree is
                     one project (one repo = one project).
      2. Root markers — if the root has a primary language marker, it is the
                        project root; no subdirectory scanning needed.
      3. Subdirectory scan — root has no markers; scan for independent child
                             projects.  Two suppression tiers apply:
                             - structural_dirs (tests/, docs/, lib/, …) are
                               always suppressed — they are never independent
                               project roots.
                             - architectural_dirs (backend/, frontend/, …) are
                               only suppressed when already inside a detected
                               project, so that a true multi-project workspace
                               that happens to name its projects "backend" and
                               "frontend" is still correctly identified.
    """

    def __init__(self):
        """Initialize the project detector with marker patterns."""
        # Project marker files used for TYPE SCORING (not detection gating).
        # These are passed to _determine_project_type and _generate_project_description.
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

        # Patterns that should match as suffixes (e.g., MyApp.csproj)
        self.suffix_patterns = {
            '.csproj',
            '.sln',
            '.gemspec',
            '.cabal',
            '.vcxproj',
            '.fsproj',
            '.vbproj'
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

        # PRIMARY markers: a directory must contain at least one of these to be
        # considered a project root during subdirectory scanning (Rule 3).
        # Lock files and README.md are intentionally excluded — they appear
        # throughout project trees and are not reliable standalone indicators.
        self.primary_markers = {
            # Python
            'setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile',
            'environment.yml', 'conda.yaml',
            # JavaScript / TypeScript (package.json covers both)
            'package.json',
            # Java
            'pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle',
            # Ruby
            'Gemfile',
            # Go
            'go.mod',
            # Rust
            'Cargo.toml',
            # PHP
            'composer.json',
            # C#
            '.csproj', '.sln',
            # Monorepo / workspace root indicators — these signal that the
            # directory is a unified project root even without language markers.
            'docker-compose.yml', 'docker-compose.yaml',
            'Makefile',
            'Dockerfile',
            # JS/TS workspace managers
            'lerna.json', 'nx.json', 'turbo.json', 'pnpm-workspace.yaml',
        }

        # Directories that are ALWAYS treated as internal sub-components and
        # never registered as independent project roots.  These names describe
        # support infrastructure (tests, docs, scripts, assets, …) that is
        # never meaningful as a standalone project.
        self.structural_dirs = {
            'tests', 'test', 'spec', 'specs',
            'docs', 'doc', 'documentation',
            'scripts', 'bin', 'tools',
            'examples', 'example', 'demo', 'demos',
            'samples', 'fixtures',
            'assets', 'static', 'public', 'resources',
            'lib', 'libs', 'vendor',
        }

        # Directories whose names suggest full-stack sub-components but that
        # CAN legitimately be independent project roots in a true multi-project
        # workspace.  These are suppressed only when we are already inside a
        # detected project (inside_project=True) to prevent double-counting
        # sub-dirs of an already-registered project.  At the top level of a
        # Rule-3 scan (inside_project=False) they are allowed through so that
        # a workspace that names its projects "backend" and "frontend" is still
        # correctly split into two independent projects.
        self.architectural_dirs = {
            'backend', 'frontend', 'client', 'server', 'api',
            'web', 'app', 'mobile', 'native', 'desktop', 'electron',
            'ui', 'gui', 'cli', 'gateway', 'worker', 'service', 'services',
        }

        # Union kept for any external code that referenced the old attribute.
        self.project_internal_dirs = self.structural_dirs | self.architectural_dirs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        # ------------------------------------------------------------------
        # RULE 1: Git root → entire directory is ONE project.
        # One git repository == one project, regardless of how many
        # backend/frontend/etc. subdirectories it contains.
        # ------------------------------------------------------------------
        has_git = (root_path / '.git').is_dir()
        if has_git:
            # Gather markers from root + immediate subdirs for accurate typing
            _, root_markers = self._find_project_markers(root_path)
            root_markers = list(root_markers)  # copy
            # .git is already picked up as a supplementary marker; avoid double-counting
            if '.git' not in root_markers:
                root_markers.append('.git')
            try:
                for subdir in root_path.iterdir():
                    if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                        _, sub_markers = self._find_project_markers(subdir)
                        root_markers.extend(sub_markers)
            except PermissionError:
                logger.debug(f"Permission denied reading subdirs of: {root_path}")

            project_type = self._determine_project_type(root_markers)
            logger.info(f"Git root detected — treating '{root_path.name}' as single {project_type} project")
            return [ProjectInfo(
                name=root_path.name,
                path=root_path,
                project_type=project_type,
                root_indicators=root_markers,
                description=self._generate_project_description(project_type, root_markers)
            )]

        # ------------------------------------------------------------------
        # RULE 2: Root has primary language markers (no git) → root IS the
        # project root.  A requirements.txt / package.json / pom.xml at the
        # top level means the whole directory is one project.
        # ------------------------------------------------------------------
        primary_found, all_markers = self._find_project_markers(root_path)
        if primary_found:
            project_type = self._determine_project_type(all_markers)
            logger.info(f"Root markers found — treating '{root_path.name}' as single {project_type} project")
            return [ProjectInfo(
                name=root_path.name,
                path=root_path,
                project_type=project_type,
                root_indicators=all_markers,
                description=self._generate_project_description(project_type, all_markers)
            )]

        # ------------------------------------------------------------------
        # RULE 3: No git, no root markers → scan subdirectories for
        # independent projects (true multi-project workspace).
        # project_internal_dirs filters structural sub-components so that
        # e.g. backend/ and frontend/ do not become false separate projects.
        # ------------------------------------------------------------------
        projects: List[ProjectInfo] = []
        visited_roots: Set[Path] = set()
        self._scan_directory(root_path, root_path, projects, visited_roots, 0, max_depth)

        if not projects:
            # Fallback: no independent projects found — gather type info from
            # immediate subdirs so the single project entry has a useful type.
            all_sub_markers: List[str] = []
            try:
                for subdir in root_path.iterdir():
                    if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                        _, sub_markers = self._find_project_markers(subdir)
                        all_sub_markers.extend(sub_markers)
            except PermissionError:
                pass

            project_type = self._determine_project_type(all_sub_markers) if all_sub_markers else "unknown"
            logger.info(f"No project markers found — treating '{root_path.name}' as single {project_type} project")
            projects.append(ProjectInfo(
                name=root_path.name,
                path=root_path,
                project_type=project_type,
                root_indicators=all_sub_markers[:10],
                description=self._generate_project_description(project_type, all_sub_markers)
                    if all_sub_markers else "No specific project markers found"
            ))

        logger.info(f"Detected {len(projects)} project(s) in {root_path}")
        return projects

    def is_monorepo(self, projects: List[ProjectInfo]) -> bool:
        """Determine if the detected projects form a monorepo structure."""
        return len(projects) > 1

    def get_project_structure_summary(self, projects: List[ProjectInfo]) -> str:
        """Generate a human-readable summary of the project structure."""
        if len(projects) == 0:
            return "No projects detected"
        elif len(projects) == 1:
            project = projects[0]
            return f"Single {project.project_type} project: {project.name}"
        else:
            type_counts: Dict[str, int] = {}
            for project in projects:
                type_counts[project.project_type] = type_counts.get(project.project_type, 0) + 1
            type_summary = ", ".join(f"{count} {ptype}" for ptype, count in sorted(type_counts.items()))
            return f"Monorepo with {len(projects)} projects: {type_summary}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _scan_directory(
        self,
        current_path: Path,
        root_path: Path,
        projects: List[ProjectInfo],
        visited_roots: Set[Path],
        depth: int,
        max_depth: int,
        inside_project: bool = False,
    ):
        """
        Recursively scan directory for project markers (Rule 3 only).

        Suppression is two-tiered:
          - structural_dirs  — always suppressed; never independent roots.
          - architectural_dirs — suppressed only when inside_project=True so
            that a workspace whose top-level directories happen to be named
            "backend" or "frontend" is still split correctly.
        """
        if depth > max_depth:
            return

        if current_path in visited_roots:
            return

        primary_found, all_markers = self._find_project_markers(current_path)
        dir_name_lower = current_path.name.lower()

        if primary_found:
            # A directory is "internal" (non-registerable) if:
            #   a) its name is in structural_dirs (always internal), OR
            #   b) its name is in architectural_dirs AND we are already inside
            #      a registered project (sub-component of a detected project).
            is_internal = (
                dir_name_lower in self.structural_dirs
                or (dir_name_lower in self.architectural_dirs and inside_project)
            )
            if not is_internal:
                # Register as a genuine independent project root
                project_type = self._determine_project_type(all_markers)
                projects.append(ProjectInfo(
                    name=current_path.name,
                    path=current_path,
                    project_type=project_type,
                    root_indicators=all_markers,
                    description=self._generate_project_description(project_type, all_markers)
                ))
                visited_roots.add(current_path)
                logger.debug(f"Found {project_type} project at: {current_path}")

                # Recurse into direct children; mark them as inside_project so
                # their own subtrees are not scanned for further project roots.
                try:
                    for subdir in current_path.iterdir():
                        if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                            self._scan_directory(
                                subdir, root_path, projects, visited_roots,
                                depth + 1, max_depth, inside_project=True,
                            )
                except PermissionError:
                    logger.debug(f"Permission denied: {current_path}")
            # else: primary markers found but dir is a known sub-component →
            # do NOT register, do NOT recurse further.

        else:
            # No primary markers here.  Recurse only when not already inside a
            # registered project, and only if the directory name does not belong
            # to structural_dirs (architectural dirs are traversable at this
            # level because they may contain genuine independent sub-projects).
            if not inside_project and dir_name_lower not in self.structural_dirs:
                try:
                    for subdir in current_path.iterdir():
                        if subdir.is_dir() and subdir.name not in self.excluded_dirs:
                            self._scan_directory(
                                subdir, root_path, projects, visited_roots,
                                depth + 1, max_depth, inside_project=False,
                            )
                except PermissionError:
                    logger.debug(f"Permission denied: {current_path}")

    def _find_project_markers(self, directory: Path) -> Tuple[List[str], List[str]]:
        """
        Find project marker files in a directory.

        Returns:
            (primary_found, all_markers) where:
            - primary_found: markers from self.primary_markers present here
            - all_markers:   all markers (primary + supplementary from
                             project_markers dict) used for type-scoring
        """
        primary_found: List[str] = []
        all_markers: List[str] = []

        try:
            dir_contents = list(directory.iterdir())
            dir_names = {p.name for p in dir_contents}

            # Check primary markers first
            for marker in self.primary_markers:
                if marker in self.suffix_patterns:
                    if any(p.name.endswith(marker) for p in dir_contents):
                        primary_found.append(marker)
                        all_markers.append(marker)
                else:
                    if marker in dir_names:
                        primary_found.append(marker)
                        all_markers.append(marker)

            # Collect supplementary markers from project_markers dict for scoring
            primary_set = set(primary_found)
            for language, marker_files in self.project_markers.items():
                for marker in marker_files:
                    if marker in primary_set:
                        continue  # already counted
                    if marker in self.suffix_patterns:
                        if any(p.name.endswith(marker) for p in dir_contents):
                            all_markers.append(marker)
                    else:
                        if marker in dir_names:
                            all_markers.append(marker)

        except PermissionError:
            logger.debug(f"Permission denied: {directory}")

        return primary_found, all_markers

    def _determine_project_type(self, markers: List[str]) -> str:
        """Determine project type based on markers found."""
        type_scores = {lang: 0 for lang in self.project_markers.keys()}

        for marker in markers:
            for lang, lang_markers in self.project_markers.items():
                if marker in lang_markers:
                    if marker in ['package.json', 'pom.xml', 'setup.py', 'Cargo.toml', 'go.mod']:
                        type_scores[lang] += 3
                    else:
                        type_scores[lang] += 1

        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]

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
