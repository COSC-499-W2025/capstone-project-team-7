# Skills Extractor

A sophisticated module for extracting computer science skills and concepts from code analysis, with a focus on **depth of insight** rather than surface-level descriptions.

**Status**: ✅ **Fully integrated into Textual CLI** - Ready to use!

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Skill Categories](#skill-categories)
- [Understanding the Output](#understanding-the-output)
- [Export Format](#export-format)
- [Supported Languages](#supported-languages)
- [Testing](#testing)
- [Integration Points](#integration-points)
  - [✅ Textual CLI Integration](#-textual-cli-integration-ready-to-use)
  - [API Routes](#with-api-routes-api)
- [Best Practices](#best-practices)
- [Future Enhancements](#future-enhancements)
- [Related Modules](#related-modules)
- [Contributing](#contributing)

## Overview

The Skills Extractor analyzes code to identify evidence of:

- **Object-Oriented Programming** (abstraction, encapsulation, polymorphism, inheritance)
- **Data Structures** (hash maps, trees, graphs, heaps, queues, stacks)
- **Algorithms** (sorting, searching, recursion, dynamic programming)
- **Design Patterns** (singleton, factory, observer, decorator, strategy)
- **Software Engineering Practices** (error handling, testing, logging, type hints, async programming)

Each skill is backed by **concrete evidence** from the codebase, including:
- File paths
- Line numbers
- Pattern descriptions
- Confidence scores

## Quick Start

```python
from analyzer.skills_extractor import SkillsExtractor

# Create extractor
extractor = SkillsExtractor()

# Extract skills from multiple sources
skills = extractor.extract_skills(
    code_analysis=code_analysis_results,  # From CodeAnalyzer
    git_analysis=git_repo_results,        # From analyze_git_repo
    file_contents=source_files_dict       # Dict of file_path: content
)

# Get results
top_skills = extractor.get_top_skills(limit=10)
by_category = extractor.get_skills_by_category()
export_data = extractor.export_to_dict()
```

## Usage Examples

### 1. Basic Code Analysis

```python
from analyzer.skills_extractor import SkillsExtractor

# Sample code to analyze
code_files = {
    "main.py": """
from abc import ABC, abstractmethod
from typing import Dict, List

class DataProcessor(ABC):
    @abstractmethod
    def process(self, data: List) -> Dict:
        pass

class HashMapProcessor(DataProcessor):
    def process(self, data: List) -> Dict:
        result = {}
        for item in data:
            result[item.id] = item
        return result
"""
}

extractor = SkillsExtractor()
skills = extractor.extract_skills(file_contents=code_files)

print(f"Found {len(skills)} skills:")
for skill_name, skill in skills.items():
    print(f"  - {skill_name}: {skill.description}")
    print(f"    Evidence: {len(skill.evidence)} instances")
```

### 2. Integration with Code Parser

```python
from local_analysis.code_parser import CodeAnalyzer
from analyzer.skills_extractor import SkillsExtractor
from pathlib import Path

# Run code analysis
analyzer = CodeAnalyzer()
code_result = analyzer.analyze_directory(Path("./project"))

# Extract skills
skills_extractor = SkillsExtractor()
skills = skills_extractor.extract_skills(code_analysis=code_result)

# Get actionable insights
top_skills = skills_extractor.get_top_skills(limit=5)
for skill in top_skills:
    print(f"{skill.name} (proficiency: {skill.proficiency_score:.2f})")
```

### 3. Full Project Analysis

```python
from local_analysis.code_parser import CodeAnalyzer
from local_analysis.git_repo import analyze_git_repo
from analyzer.skills_extractor import SkillsExtractor
from pathlib import Path

# Analyze code
code_analyzer = CodeAnalyzer()
code_result = code_analyzer.analyze_directory(Path("./project"))

# Analyze git history
git_result = analyze_git_repo("./project")

# Read important files for deep analysis
important_files = {}
for file in Path("./project/src").glob("**/*.py"):
    if file.stat().st_size < 100_000:  # Skip huge files
        important_files[str(file)] = file.read_text()

# Extract skills from all sources
extractor = SkillsExtractor()
skills = extractor.extract_skills(
    code_analysis=code_result,
    git_analysis=git_result,
    file_contents=important_files
)

# Export for storage
skills_data = extractor.export_to_dict()
```

### 4. Save to Database

```python
from cli.services.projects_service import ProjectsService

# Extract skills (as above)
skills_data = extractor.export_to_dict()

# Store in database
project_service = ProjectsService()
project_service.save_scan(
    user_id="user-uuid",
    project_name="My Awesome Project",
    project_path="/path/to/project",
    scan_data={
        "skills": skills_data,
        "code_analysis": code_result,
        "git_analysis": git_result,
    }
)
```

## Skill Categories

### Object-Oriented Programming (oop)
- **Abstraction**: Abstract classes and interfaces
- **Encapsulation**: Private fields with getters/setters
- **Polymorphism**: Method overriding
- **Inheritance**: Class hierarchies
- **Interface Design**: Protocol definitions

### Data Structures (data_structures)
- **Hash-based Data Structures**: Dicts, maps, sets for O(1) lookup
- **Tree Data Structures**: Binary trees, BSTs
- **Graph Algorithms**: Adjacency lists, DFS, BFS
- **Queue Data Structure**: FIFO operations
- **Stack Data Structure**: LIFO operations
- **Heap/Priority Queue**: Efficient priority operations

### Algorithms (algorithms)
- **Sorting Algorithms**: Quick sort, merge sort, etc.
- **Search Algorithms**: Binary search, hash lookups
- **Recursive Problem Solving**: Recursive functions
- **Dynamic Programming**: Memoization, tabulation

### Design Patterns (patterns)
- **Singleton Pattern**: Single instance management
- **Factory Pattern**: Object creation abstraction
- **Observer Pattern**: Event-driven architecture
- **Decorator Pattern**: Functionality extension
- **Strategy Pattern**: Algorithm encapsulation

### Software Engineering Practices (practices)
- **Error Handling**: Try-catch blocks, exceptions
- **Automated Testing**: Unit tests, test coverage
- **Logging**: Debug and monitoring logs
- **Static Typing**: Type hints and annotations
- **Asynchronous Programming**: Async/await patterns
- **Code Documentation**: Docstrings, comments
- **Version Control (Git)**: Commit management
- **Team Collaboration**: Multi-contributor projects
- **Code Complexity Management**: Maintainable complexity
- **Maintainable Code**: High maintainability scores
- **Refactoring**: Well-structured, low-priority code

## Understanding the Output

### Skill Object
```python
@dataclass
class Skill:
    name: str                    # E.g., "Dynamic Programming"
    category: str                # E.g., "algorithms"
    description: str             # Detailed explanation
    evidence: List[Evidence]     # Supporting proof
    proficiency_score: float     # 0.0 to 1.0 (more evidence = higher)
```

### Evidence Object
```python
@dataclass
class SkillEvidence:
    skill_name: str              # Links to skill
    evidence_type: str           # "code_pattern", "metric", "practice"
    description: str             # What was found
    file_path: str               # Where it was found
    line_number: Optional[int]   # Specific line (if applicable)
    confidence: float            # 0.0 to 1.0
```

### Proficiency Scoring

Proficiency scores are calculated based on:
- **Quantity of evidence**: More instances = higher score
- **Diminishing returns**: Each additional piece has less impact
- **Formula**: `min(1.0, evidence_count * 0.2 + 0.2)`

Examples:
- 1 piece of evidence: 0.4
- 2 pieces: 0.6
- 3 pieces: 0.8
- 4+ pieces: 1.0

## Export Format

```json
{
  "skills": [
    {
      "name": "Dynamic Programming",
      "category": "algorithms",
      "description": "Optimizes recursive solutions using memoization",
      "proficiency_score": 0.8,
      "evidence_count": 3,
      "evidence": [
        {
          "type": "code_pattern",
          "description": "Uses memoization in python",
          "file": "algorithms.py",
          "line": 42,
          "confidence": 0.9
        }
      ]
    }
  ],
  "summary": {
    "total_skills": 15,
    "by_category": {
      "oop": 4,
      "data_structures": 3,
      "algorithms": 3,
      "patterns": 2,
      "practices": 3
    },
    "top_skills": [
      {"name": "Hash-based Data Structures", "score": 1.0},
      {"name": "Error Handling", "score": 0.8}
    ]
  }
}
```

## Supported Languages

- Python
- JavaScript / TypeScript
- Java
- C / C++

Each language has specific patterns for detecting OOP, data structures, and practices.

## Testing

Run the test suite:

```bash
pytest tests/test_skills_extractor.py -v
```

Run the demo:

```bash
cd backend/src/analyzer
python skills_demo.py
```

## Integration Points

### ✅ Textual CLI Integration (READY TO USE)

The Skills Extractor is **fully integrated** into the Textual CLI application with **enhanced multi-project support**. Users can extract and view skills directly from scan results.

**How to Use:**
1. Run the CLI: `python -m src.cli.textual_app`
2. Select "Run Portfolio Scan" and choose a project directory
3. **Automatic project detection** identifies multiple projects in the directory
4. View **project summary** with detected projects, types, and monorepo indicators
5. In scan results, click **"Skills analysis"** button
6. View formatted skills summary organized by category
7. Export JSON (skills automatically included)

**🆕 Multi-Project Detection:**
The system now automatically detects multiple projects within a scanned directory:
- **Project markers identified**: package.json, requirements.txt, pom.xml, Cargo.toml, go.mod, and more
- **Monorepo detection**: Automatically identifies monorepo structures
- **Project types**: Detects Python, JavaScript, TypeScript, Java, Ruby, Go, Rust, PHP, C#, and multi-language projects
- **Visual indicators**: Shows 📦 for projects and ⚡ for monorepos

**Enhanced Overview Display:**
```
📦 Project Detection
  2 projects detected
  ⚡ Monorepo structure identified

  Projects:
    1. frontend (javascript)
       └─ package.json, package-lock.json, tsconfig.json +3 more
    2. backend (python)
       └─ requirements.txt, setup.py, pyproject.toml

🎯 Skills Detected
  Error Handling, Asynchronous Programming, React Framework, 
  RESTful API Design, Automated Testing, MongoDB, Hash-based Data Structures,
  ...and 8 more
```

**Display Format:**
```
Skills Detected: 15 total
============================================================

Object-Oriented Programming (4 skills):
------------------------------------------------------------
  • Encapsulation (Advanced, 8 instances)
    Defines classes with private attributes and controlled access
  • Polymorphism (Intermediate, 3 instances)
    Uses method overriding and interface implementations

Data Structures (5 skills):
------------------------------------------------------------
  • Hash Maps (Advanced, 12 instances)
    Implements dictionaries and lookup tables efficiently
...
```

**Features:**
- ✅ Multi-project detection 
- ✅ Monorepo identification 
- ✅ Project type recognition 
- ✅ Enhanced visual overview 
- ✅ Background execution (non-blocking UI)
- ✅ Result caching (instant re-viewing)
- ✅ Automatic JSON export integration
- ✅ Smart file filtering (excludes node_modules, .git, etc.)
- ✅ Multi-language support
- ✅ Proficiency levels (Beginner/Intermediate/Advanced)

**Project Detection Service:**
The `ProjectDetector` (`analyzer/project_detector.py`) provides:
```python
from analyzer.project_detector import ProjectDetector

detector = ProjectDetector()

# Detect all projects in a directory
projects = detector.detect_projects(Path("./workspace"))
# Returns: List[ProjectInfo] with name, path, type, and markers

# Check if it's a monorepo
is_monorepo = detector.is_monorepo(projects)

# Get summary
summary = detector.get_project_structure_summary(projects)
# Returns: "Monorepo with 3 projects: 2 python, 1 javascript"
```

**ProjectInfo Structure:**
```python
@dataclass
class ProjectInfo:
    name: str                     # Project directory name
    path: Path                    # Full path to project
    project_type: str            # "python", "javascript", "multi-language", etc.
    root_indicators: List[str]   # ["package.json", "tsconfig.json", ...]
    description: Optional[str]   # "TypeScript project with Docker"
```

**Service Layer:**
The `SkillsAnalysisService` (`cli/services/skills_analysis_service.py`) provides:
```python
from cli.services.skills_analysis_service import SkillsAnalysisService

service = SkillsAnalysisService()

# Extract skills from a project
skills = service.extract_skills(
    target_path=Path("./project"),
    code_analysis_result=code_result,  # Optional
    git_analysis_result=git_result,    # Optional
    file_contents=files_dict           # Optional (auto-read if None)
)

# Format for display
summary = service.format_summary(skills)
print(summary)

# Prepare for export
export_data = service.export_skills_data(skills)
```

**State Management:**
Enhanced state tracking for projects and skills:
```python
# In textual_app.py
self._scan_state.skills_analysis_result    # List[Skill]
self._scan_state.skills_analysis_error     # Optional[str]
self._scan_state.detected_projects         # List[ProjectInfo] 
self._scan_state.is_monorepo              # bool 
```

**Export Format:**
Skills and project information are automatically included in JSON exports:
```json
{
  "detected_projects": [
    {
      "name": "frontend",
      "path": "/path/to/workspace/frontend",
      "type": "javascript",
      "markers": ["package.json", "package-lock.json", "tsconfig.json"],
      "description": "JavaScript/Node.js project"
    },
    {
      "name": "backend",
      "path": "/path/to/workspace/backend",
      "type": "python",
      "markers": ["requirements.txt", "setup.py"],
      "description": "Python project"
    }
  ],
  "is_monorepo": true,
  "skills_analysis": {
    "success": true,
    "total_skills": 15,
    "skills_by_category": {
      "Object-Oriented Programming": [...],
      "Data Structures": [...],
      "Algorithms": [...],
      "Design Patterns": [...],
      "Best Practices": [...]
    },
    "top_skills": [
      {
        "name": "Hash Maps",
        "category": "Data Structures",
        "proficiency": 0.92,
        "evidence_count": 12
      }
    ],
    "all_skills": [...]
  }
}
```

**Testing:**
```bash
# Run integration tests
python backend/test_skills_integration.py

# Expected output:
✅ PASSED: Service Initialization
✅ PASSED: Skills Extraction
✅ PASSED: ScanState Integration

# Test project detection
python backend/test_multi_project_tabs.py

# Expected output:
✓ Project detection works (5 projects found)
✓ State structure is correct
✓ ALL TESTS PASSED
```

### With API Routes (`api/`)
Create endpoint for skills:

```python
@router.get("/projects/{project_id}/skills")
async def get_project_skills(project_id: str):
    # Load project data
    project = projects_service.get_project_scan(user_id, project_id)
    
    # Extract skills if not cached
    if "skills" not in project["scan_data"]:
        extractor = SkillsExtractor()
        skills = extractor.extract_skills(
            code_analysis=project["scan_data"]["code_analysis"]
        )
        project["scan_data"]["skills"] = extractor.export_to_dict()
    
    return project["scan_data"]["skills"]
```

## Best Practices

1. **Combine Multiple Sources**: Use code analysis + git history + file contents for best results
2. **Filter Files**: Only analyze relevant source files (skip node_modules, build artifacts)
3. **Cache Results**: Skills extraction can be expensive; cache in database
4. **Threshold Filtering**: Consider filtering low-confidence evidence
5. **Context Matters**: More evidence = more reliable skill detection

## Future Enhancements

Potential improvements:
- [ ] Machine learning for pattern detection
- [ ] Framework-specific skills (React, Django, etc.)
- [ ] Code smell detection
- [ ] Performance optimization patterns
- [ ] Security best practices detection
- [ ] Architectural pattern recognition

## Related Modules

- `project_detector.py`: **Multi-project detection and monorepo identification** 
- `code_parser.py`: Static code analysis and metrics
- `git_repo.py`: Git history and contribution analysis
- `projects_service.py`: Database storage
- `llm/client.py`: LLM-based analysis (complementary)

## Contributing

When adding new patterns:

1. Add to appropriate pattern dictionary in `_init_patterns()`
2. Add skill description in `_get_skill_description()`
3. Add test case in `test_skills_extractor.py`
4. Document in this README

Example:
```python
# In _init_patterns()
self.practice_patterns['dependency_injection'] = {
    'python': [r'def\s+__init__\(self.*:.*\)'],
    'java': [r'@Inject', r'@Autowired'],
}

# In _get_skill_description()
"Dependency Injection": "Uses dependency injection for loose coupling"
```

## License

Part of the capstone project. See main project LICENSE.
