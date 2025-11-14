# Skills Extractor

A sophisticated module for extracting computer science skills and concepts from code analysis, with a focus on **depth of insight** rather than surface-level descriptions.

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

### With CLI (`parse_zip.py`)
Add skills extraction to the scan pipeline:

```python
from analyzer.skills_extractor import SkillsExtractor

# In parse_zip or CLI handler
skills_extractor = SkillsExtractor()
skills = skills_extractor.extract_skills(
    code_analysis=analysis_result,
    git_analysis=git_repos,
    file_contents=important_files
)

# Add to output
payload["skills"] = skills_extractor.export_to_dict()
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
