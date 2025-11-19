"""
Skills Extractor Module

Extracts computer science skills and concepts from code analysis results.
Focuses on depth of insight rather than surface-level descriptions.

This module identifies evidence of:
- OOP principles (abstraction, encapsulation, polymorphism)
- Data structures and their performance characteristics
- Algorithm complexity awareness
- Design patterns
- Software engineering practices
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillEvidence:
    """Evidence supporting a skill claim."""
    skill_name: str
    evidence_type: str  # e.g., "code_pattern", "data_structure", "optimization"
    description: str
    file_path: str
    line_number: Optional[int] = None
    confidence: float = 1.0  # 0.0 to 1.0
    
    def __hash__(self):
        return hash((self.skill_name, self.file_path, self.line_number))


@dataclass
class Skill:
    """A detected skill with supporting evidence."""
    name: str
    category: str  # "oop", "data_structures", "algorithms", "patterns", "practices"
    description: str
    evidence: List[SkillEvidence] = field(default_factory=list)
    proficiency_score: float = 0.0  # 0.0 to 1.0 based on evidence quality/quantity
    
    def add_evidence(self, evidence: SkillEvidence):
        """Add evidence and update proficiency score."""
        self.evidence.append(evidence)
        # More evidence = higher proficiency (with diminishing returns)
        self.proficiency_score = min(1.0, len(self.evidence) * 0.2 + 0.2)


class SkillsExtractor:
    """
    Extract CS skills with evidence from code analysis results.
    
    Analyzes code to identify:
    - Object-oriented design principles
    - Data structure usage and understanding
    - Algorithm complexity awareness
    - Design pattern implementation
    - Software engineering best practices
    """
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.logger = logging.getLogger(__name__)
        
        # Pattern definitions for skill detection
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for detecting skills in code."""
        
        # OOP Patterns
        self.oop_patterns = {
            'abstract_class': {
                'python': [r'class\s+\w+\(ABC\)', r'@abstractmethod', r'from\s+abc\s+import'],
                'java': [r'abstract\s+class', r'abstract\s+\w+\s+\w+\('],
                'cpp': [r'virtual\s+\w+.*=\s*0', r'pure\s+virtual'],
            },
            'interface': {
                'python': [r'class\s+\w+\(Protocol\)', r'from\s+typing\s+import.*Protocol'],
                'java': [r'interface\s+\w+'],
                'typescript': [r'interface\s+\w+\s*{'],
            },
            'inheritance': {
                'python': [r'class\s+\w+\([^)]+\):'],
                'java': [r'extends\s+\w+', r'implements\s+\w+'],
                'javascript': [r'extends\s+\w+'],
            },
            'encapsulation': {
                'python': [r'@property', r'def\s+get_\w+', r'def\s+set_\w+', r'self\.__\w+'],
                'java': [r'private\s+\w+', r'protected\s+\w+', r'public\s+get\w+', r'public\s+set\w+'],
            },
            'polymorphism': {
                'python': [r'def\s+\w+\(self[^)]*\):.*\n.*super\(\)', r'@override'],
                'java': [r'@Override'],
            }
        }
        
        # Data Structure Patterns
        self.data_structure_patterns = {
            'hash_map': {
                'python': [
                    r'\bdict\(',           # dict() constructor
                    r'=\s*\{\}',           # Empty dict initialization
                    r'\{[^}]*:[^}]*\}',   # Dict literals with key:value
                    r'collections\.defaultdict',
                    r'collections\.Counter',
                    r'\.get\(',            # Dict.get() method
                    r'\[[^\]]+\]\s*=',    # Dict assignment like dict[key] = value
                ],
                'java': [r'HashMap<', r'HashSet<', r'Hashtable<'],
                'javascript': [r'new\s+Map\(', r'new\s+Set\('],
            },
            'tree': {
                'python': [r'class\s+\w*Node\w*', r'\.left\b', r'\.right\b', r'binary.*tree'],
                'java': [r'TreeMap<', r'TreeSet<'],
            },
            'graph': {
                'python': [r'adjacency', r'graph\s*=\s*\{', r'visited\s*=\s*set\(', r'dfs|bfs'],
                'java': [r'Graph\s+\w+', r'adjacency'],
            },
            'queue': {
                'python': [r'from\s+queue\s+import', r'Queue\(', r'collections\.deque', r'\.append\(', r'\.popleft\('],
                'java': [r'Queue<', r'LinkedList<.*>.*queue', r'PriorityQueue<'],
            },
            'stack': {
                'python': [r'\.append\(', r'\.pop\(\)', r'stack\s*=\s*\[\]'],
                'java': [r'Stack<'],
            },
            'heap': {
                'python': [r'import\s+heapq', r'heappush', r'heappop', r'PriorityQueue'],
                'java': [r'PriorityQueue<'],
            },
        }
        
        # Algorithm & Complexity Patterns
        self.algorithm_patterns = {
            'sorting': {
                'python': [r'\.sort\(', r'sorted\(', r'def\s+\w*sort\w*', r'quick_sort|merge_sort|heap_sort'],
                'java': [r'Arrays\.sort', r'Collections\.sort', r'Comparator<'],
            },
            'searching': {
                'python': [r'binary.search', r'def\s+\w*search\w*', r'\bin\b.*dict'],
                'java': [r'binarySearch', r'\.contains\('],
            },
            'recursion': {
                'python': [r'def\s+(\w+).*:.*\1\('],  # function calling itself
                'java': [r'return\s+\w+\('],
            },
            'dynamic_programming': {
                'python': [r'memo\s*=', r'@lru_cache', r'dp\s*=\s*\[', r'tabulation'],
                'java': [r'memo\[', r'dp\['],
            },
        }
        
        # Design Pattern Patterns
        self.design_pattern_patterns = {
            'singleton': {
                'python': [r'__instance\s*=\s*None', r'def\s+__new__'],
                'java': [r'private\s+static.*instance', r'private\s+\w+\(\)'],
            },
            'factory': {
                'python': [r'def\s+create_\w+', r'class\s+\w*Factory'],
                'java': [r'class\s+\w*Factory', r'createInstance'],
            },
            'observer': {
                'python': [r'def\s+notify', r'def\s+subscribe', r'observers\s*='],
                'java': [r'Observable', r'Observer', r'addObserver'],
            },
            'decorator': {
                'python': [r'@\w+', r'def\s+decorator', r'functools\.wraps'],
                'java': [r'@interface'],
            },
            'strategy': {
                'python': [r'class\s+\w*Strategy', r'def\s+execute'],
                'java': [r'interface\s+\w*Strategy', r'class\s+\w*Strategy'],
            },
        }
        
        # Software Engineering Practices
        self.practice_patterns = {
            'error_handling': {
                'python': [r'try:', r'except\s+\w+', r'raise\s+\w+', r'finally:'],
                'java': [r'try\s*{', r'catch\s*\(', r'throw\s+new', r'throws\s+\w+'],
                'javascript': [r'try\s*{', r'catch\s*\(', r'throw\s+new'],
            },
            'testing': {
                'python': [r'import\s+unittest', r'import\s+pytest', r'def\s+test_', r'assert\s+'],
                'java': [r'@Test', r'import\s+org\.junit', r'assertEquals'],
                'javascript': [r'describe\(', r'it\(', r'expect\(', r'test\('],
            },
            'logging': {
                'python': [r'import\s+logging', r'logger\.', r'log\.'],
                'java': [r'import.*Logger', r'logger\.', r'log\.'],
            },
            'type_hints': {
                'python': [r':\s*\w+\s*=', r'->\s*\w+', r'from\s+typing\s+import'],
                'typescript': [r':\s*\w+\s*=', r'interface\s+', r'type\s+\w+\s*='],
            },
            'async_programming': {
                'python': [r'async\s+def', r'await\s+', r'asyncio\.'],
                'javascript': [r'async\s+function', r'await\s+', r'Promise\.'],
            },
            'documentation': {
                'python': [r'""".*"""', r"'''.*'''", r'#\s*TODO', r'#\s*FIXME'],
                'java': [r'/\*\*.*\*/', r'//.*@param', r'//.*@return'],
            },
        }
    
    def extract_skills(
        self,
        code_analysis: Optional[Dict] = None,
        git_analysis: Optional[Dict] = None,
        file_contents: Optional[Dict[str, str]] = None
    ) -> Dict[str, Skill]:
        """
        Extract skills from various analysis sources.
        
        Args:
            code_analysis: Results from CodeAnalyzer (metrics, complexity, etc.)
            git_analysis: Results from git repository analysis
            file_contents: Dictionary mapping file paths to their content
        
        Returns:
            Dictionary mapping skill names to Skill objects
        """
        self.skills = {}
        
        if code_analysis:
            self._extract_from_code_analysis(code_analysis)
        
        if git_analysis:
            self._extract_from_git_analysis(git_analysis)
        
        if file_contents:
            self._extract_from_source_code(file_contents)
        
        return self.skills
    
    def _extract_from_code_analysis(self, analysis: Dict):
        """Extract skills from code analysis metrics."""
        
        # Check for complexity understanding
        if 'summary' in analysis:
            summary = analysis['summary']
            avg_complexity = summary.get('avg_complexity', 0)
            
            if avg_complexity > 0:
                # Evidence of managing complexity
                evidence = SkillEvidence(
                    skill_name="Code Complexity Management",
                    evidence_type="metric",
                    description=f"Maintains average cyclomatic complexity of {avg_complexity:.1f}",
                    file_path="overall",
                    confidence=0.7
                )
                self._add_skill(
                    "Code Complexity Management",
                    "practices",
                    "Demonstrates awareness of code complexity and maintainability",
                    evidence
                )
            
            # Check maintainability
            avg_maintainability = summary.get('avg_maintainability', 0)
            if avg_maintainability >= 70:
                evidence = SkillEvidence(
                    skill_name="Maintainable Code",
                    evidence_type="metric",
                    description=f"Achieves {avg_maintainability:.0f}/100 maintainability score",
                    file_path="overall",
                    confidence=0.8
                )
                self._add_skill(
                    "Maintainable Code",
                    "practices",
                    "Writes clean, maintainable code with good structure",
                    evidence
                )
        
        # Analyze individual files
        if 'files' in analysis:
            for file_result in analysis['files']:
                if not file_result.get('success'):
                    continue
                
                metrics = file_result.get('metrics', {})
                if not metrics:
                    continue
                
                file_path = file_result.get('path', 'unknown')
                language = file_result.get('language', 'unknown')
                
                # Check for refactoring awareness
                if metrics.get('refactor_priority') == 'LOW' and metrics.get('functions', 0) > 5:
                    evidence = SkillEvidence(
                        skill_name="Refactoring",
                        evidence_type="code_quality",
                        description="Maintains well-structured code with low refactoring needs",
                        file_path=file_path,
                        confidence=0.7
                    )
                    self._add_skill(
                        "Refactoring",
                        "practices",
                        "Writes code that requires minimal refactoring",
                        evidence
                    )
                
                # Check for testing
                if 'test' in file_path.lower():
                    evidence = SkillEvidence(
                        skill_name="Unit Testing",
                        evidence_type="practice",
                        description=f"Implements tests in {language}",
                        file_path=file_path,
                        confidence=0.9
                    )
                    self._add_skill(
                        "Unit Testing",
                        "practices",
                        "Writes automated tests to ensure code quality",
                        evidence
                    )
    
    def _extract_from_git_analysis(self, git_analysis: Dict):
        """Extract skills from git repository analysis."""
        
        # Check for version control skills
        commit_count = git_analysis.get('commit_count', 0)
        if commit_count > 0:
            evidence = SkillEvidence(
                skill_name="Version Control (Git)",
                evidence_type="practice",
                description=f"Managed {commit_count} commits",
                file_path=git_analysis.get('path', 'repository'),
                confidence=0.8
            )
            self._add_skill(
                "Version Control (Git)",
                "practices",
                "Uses Git for source code management and collaboration",
                evidence
            )
        
        # Check for collaboration
        contributors = git_analysis.get('contributors', [])
        if len(contributors) > 1:
            evidence = SkillEvidence(
                skill_name="Team Collaboration",
                evidence_type="practice",
                description=f"Collaborated with {len(contributors)} contributors",
                file_path=git_analysis.get('path', 'repository'),
                confidence=0.9
            )
            self._add_skill(
                "Team Collaboration",
                "practices",
                "Works effectively in team environments",
                evidence
            )
        
        # Check for consistent contribution
        timeline = git_analysis.get('timeline', [])
        if len(timeline) >= 3:
            evidence = SkillEvidence(
                skill_name="Consistent Development",
                evidence_type="practice",
                description=f"Active development across {len(timeline)} time periods",
                file_path=git_analysis.get('path', 'repository'),
                confidence=0.7
            )
            self._add_skill(
                "Consistent Development",
                "practices",
                "Maintains consistent development activity over time",
                evidence
            )
        
        # Enhanced: Individual contributor analysis
        for contributor in contributors:
            active_days = contributor.get('active_days', 0)
            if active_days >= 7:  # At least a week of activity
                contrib_name = contributor.get('name', 'Unknown')
                evidence = SkillEvidence(
                    skill_name="Sustained Contribution",
                    evidence_type="practice",
                    description=f"{contrib_name} contributed across {active_days} active days",
                    file_path=git_analysis.get('path', 'repository'),
                    confidence=0.8
                )
                self._add_skill(
                    "Sustained Contribution",
                    "practices",
                    "Demonstrates sustained and regular contribution patterns",
                    evidence
                )
    
    def _extract_from_source_code(self, file_contents: Dict[str, str]):
        """Extract skills by analyzing actual source code."""
        
        for file_path, content in file_contents.items():
            # Detect language
            language = self._detect_language(file_path)
            if not language:
                continue
            
            # Check OOP patterns
            self._check_patterns(
                content, file_path, language,
                self.oop_patterns, "oop",
                {
                    'abstract_class': "Abstraction",
                    'interface': "Interface Design",
                    'inheritance': "Inheritance",
                    'encapsulation': "Encapsulation",
                    'polymorphism': "Polymorphism",
                }
            )
            
            # Check data structures
            self._check_patterns(
                content, file_path, language,
                self.data_structure_patterns, "data_structures",
                {
                    'hash_map': "Hash-based Data Structures",
                    'tree': "Tree Data Structures",
                    'graph': "Graph Algorithms",
                    'queue': "Queue Data Structure",
                    'stack': "Stack Data Structure",
                    'heap': "Heap/Priority Queue",
                }
            )
            
            # Check algorithms
            self._check_patterns(
                content, file_path, language,
                self.algorithm_patterns, "algorithms",
                {
                    'sorting': "Sorting Algorithms",
                    'searching': "Search Algorithms",
                    'recursion': "Recursive Problem Solving",
                    'dynamic_programming': "Dynamic Programming",
                }
            )
            
            # Check design patterns
            self._check_patterns(
                content, file_path, language,
                self.design_pattern_patterns, "patterns",
                {
                    'singleton': "Singleton Pattern",
                    'factory': "Factory Pattern",
                    'observer': "Observer Pattern",
                    'decorator': "Decorator Pattern",
                    'strategy': "Strategy Pattern",
                }
            )
            
            # Check practices
            self._check_patterns(
                content, file_path, language,
                self.practice_patterns, "practices",
                {
                    'error_handling': "Error Handling",
                    'testing': "Automated Testing",
                    'logging': "Logging",
                    'type_hints': "Static Typing",
                    'async_programming': "Asynchronous Programming",
                    'documentation': "Code Documentation",
                }
            )
    
    def _check_patterns(
        self,
        content: str,
        file_path: str,
        language: str,
        pattern_dict: Dict,
        category: str,
        skill_mapping: Dict[str, str]
    ):
        """Check for patterns in code and add evidence."""
        
        for pattern_key, skill_name in skill_mapping.items():
            if pattern_key not in pattern_dict:
                continue
            
            patterns = pattern_dict[pattern_key].get(language, [])
            for pattern in patterns:
                matches = list(re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE))
                
                if matches:
                    # Get line number of first match
                    first_match = matches[0]
                    line_num = content[:first_match.start()].count('\n') + 1
                    
                    # Create evidence
                    evidence = SkillEvidence(
                        skill_name=skill_name,
                        evidence_type="code_pattern",
                        description=f"Uses {pattern_key.replace('_', ' ')} in {language}",
                        file_path=file_path,
                        line_number=line_num,
                        confidence=min(1.0, len(matches) * 0.3 + 0.4)
                    )
                    
                    # Add skill with evidence
                    description = self._get_skill_description(skill_name, category, pattern_key)
                    self._add_skill(skill_name, category, description, evidence)
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python',
            '.pyi': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.hpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
        }
        
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return None
    
    def _get_skill_description(self, skill_name: str, category: str, pattern_key: str) -> str:
        """Generate detailed description for a skill."""
        
        descriptions = {
            # OOP
            "Abstraction": "Defines abstract interfaces and base classes to hide implementation details",
            "Interface Design": "Designs clear interfaces for component interaction",
            "Inheritance": "Uses inheritance to create class hierarchies and code reuse",
            "Encapsulation": "Protects internal state using private fields and public methods",
            "Polymorphism": "Implements polymorphic behavior through method overriding",
            
            # Data Structures
            "Hash-based Data Structures": "Uses hash maps/sets for O(1) lookup performance",
            "Tree Data Structures": "Implements or uses tree structures for hierarchical data",
            "Graph Algorithms": "Works with graph data structures for network problems",
            "Queue Data Structure": "Uses queues for FIFO operations and BFS algorithms",
            "Stack Data Structure": "Uses stacks for LIFO operations and DFS algorithms",
            "Heap/Priority Queue": "Uses heaps for efficient priority-based operations",
            
            # Algorithms
            "Sorting Algorithms": "Implements or uses sorting algorithms effectively",
            "Search Algorithms": "Uses efficient search strategies including binary search",
            "Recursive Problem Solving": "Solves problems using recursive approaches",
            "Dynamic Programming": "Optimizes recursive solutions using memoization or tabulation",
            
            # Design Patterns
            "Singleton Pattern": "Ensures single instance using singleton pattern",
            "Factory Pattern": "Creates objects using factory pattern for flexibility",
            "Observer Pattern": "Implements event-driven architecture with observers",
            "Decorator Pattern": "Extends functionality using decorator pattern",
            "Strategy Pattern": "Encapsulates algorithms using strategy pattern",
            
            # Practices
            "Error Handling": "Implements robust error handling with try-catch blocks",
            "Automated Testing": "Writes unit tests to ensure code correctness",
            "Logging": "Adds logging for debugging and monitoring",
            "Static Typing": "Uses type hints/annotations for code safety",
            "Asynchronous Programming": "Implements async patterns for concurrent operations",
            "Code Documentation": "Documents code with comments and docstrings",
            "Version Control (Git)": "Uses Git for source code management",
            "Team Collaboration": "Collaborates with team members on shared codebase",
        }
        
        return descriptions.get(skill_name, f"Demonstrates {skill_name.lower()}")
    
    def _add_skill(self, name: str, category: str, description: str, evidence: SkillEvidence):
        """Add or update a skill with new evidence."""
        
        if name not in self.skills:
            self.skills[name] = Skill(
                name=name,
                category=category,
                description=description
            )
        
        self.skills[name].add_evidence(evidence)
    
    def get_skills_by_category(self) -> Dict[str, List[Skill]]:
        """Group skills by category."""
        
        categorized = defaultdict(list)
        for skill in self.skills.values():
            categorized[skill.category].append(skill)
        
        # Sort by proficiency within each category
        for category in categorized:
            categorized[category].sort(key=lambda s: s.proficiency_score, reverse=True)
        
        return dict(categorized)
    
    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Get top skills by proficiency score."""
        
        sorted_skills = sorted(
            self.skills.values(),
            key=lambda s: (s.proficiency_score, len(s.evidence)),
            reverse=True
        )
        
        return sorted_skills[:limit]
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export skills to dictionary format for JSON serialization."""
        
        return {
            "skills": [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "description": skill.description,
                    "proficiency_score": skill.proficiency_score,
                    "evidence_count": len(skill.evidence),
                    "evidence": [
                        {
                            "type": ev.evidence_type,
                            "description": ev.description,
                            "file": ev.file_path,
                            "line": ev.line_number,
                            "confidence": ev.confidence,
                        }
                        for ev in skill.evidence
                    ]
                }
                for skill in self.skills.values()
            ],
            "summary": {
                "total_skills": len(self.skills),
                "by_category": {
                    category: len(skills)
                    for category, skills in self.get_skills_by_category().items()
                },
                "top_skills": [
                    {"name": s.name, "score": s.proficiency_score}
                    for s in self.get_top_skills(5)
                ]
            }
        }
