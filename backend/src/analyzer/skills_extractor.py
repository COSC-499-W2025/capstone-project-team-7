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
from datetime import datetime
import re
import logging
import subprocess

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
    timestamp: Optional[str] = None  # ISO format timestamp when skill was used
    
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
        self.file_timestamps: Dict[str, str] = {}  # Cache for file timestamps
        
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
        
        # Framework Patterns
        self.framework_patterns = {
            'react': {
                'javascript': [r'import.*from\s+["\']react["\']', r'useState', r'useEffect', r'React\.Component', r'\.jsx'],
                'typescript': [r'import.*from\s+["\']react["\']', r'useState', r'useEffect', r'FC<', r'\.tsx'],
            },
            'vue': {
                'javascript': [r'import.*from\s+["\']vue["\']', r'Vue\.component', r'v-if', r'v-for', r'\.vue'],
            },
            'angular': {
                'typescript': [r'@Component', r'@Injectable', r'@NgModule', r'import.*@angular'],
            },
            'django': {
                'python': [r'from\s+django', r'django\.db\.models', r'models\.Model', r'\.views', r'urlpatterns'],
            },
            'flask': {
                'python': [r'from\s+flask\s+import', r'@app\.route', r'Flask\(__name__\)', r'render_template'],
            },
            'express': {
                'javascript': [r'require\(["\']express["\']\)', r'express\(\)', r'app\.get\(', r'app\.post\('],
            },
            'spring': {
                'java': [r'@SpringBootApplication', r'@RestController', r'@Autowired', r'import.*springframework'],
            },
            'nextjs': {
                'javascript': [r'import.*from\s+["\']next', r'getServerSideProps', r'getStaticProps', r'next\.config'],
                'typescript': [r'import.*from\s+["\']next', r'getServerSideProps', r'getStaticProps'],
            },
        }
        
        # Database & ORM Patterns
        self.database_patterns = {
            'sql_queries': {
                'python': [r'SELECT\s+.*\s+FROM', r'INSERT\s+INTO', r'UPDATE\s+.*\s+SET', r'DELETE\s+FROM'],
                'java': [r'SELECT\s+.*\s+FROM', r'PreparedStatement', r'executeQuery'],
                'javascript': [r'SELECT\s+.*\s+FROM', r'\.query\('],
            },
            'orm': {
                'python': [r'from\s+sqlalchemy', r'from\s+django\.db', r'\.objects\.', r'\.filter\(', r'\.all\(\)'],
                'java': [r'@Entity', r'@Table', r'EntityManager', r'import.*javax\.persistence'],
            },
            'mongodb': {
                'python': [r'from\s+pymongo', r'MongoClient', r'\.find\(', r'\.insert_one'],
                'javascript': [r'require\(["\']mongoose["\']\)', r'\.find\(', r'\.save\(', r'Schema'],
            },
            'redis': {
                'python': [r'import\s+redis', r'Redis\(', r'\.get\(', r'\.set\('],
                'javascript': [r'require\(["\']redis["\']\)', r'createClient'],
            },
        }
        
        # Architecture & Security Patterns
        self.architecture_patterns = {
            'mvc': {
                'python': [r'class\s+\w+View', r'class\s+\w+Controller', r'render\s*\('],
                'java': [r'@Controller', r'ModelAndView', r'class\s+\w+Controller'],
            },
            'rest_api': {
                'python': [r'@app\.route', r'@api\.route', r'@get', r'@post', r'jsonify'],
                'java': [r'@RestController', r'@GetMapping', r'@PostMapping', r'@RequestMapping'],
                'javascript': [r'app\.get\(', r'app\.post\(', r'router\.', r'res\.json'],
            },
            'microservices': {
                'python': [r'import\s+consul', r'service\s+discovery', r'docker-compose'],
                'java': [r'@EnableDiscoveryClient', r'@FeignClient', r'import.*spring\.cloud'],
            },
            'authentication': {
                'python': [r'import\s+jwt', r'@login_required', r'authenticate', r'bcrypt', r'hash.*password'],
                'java': [r'@PreAuthorize', r'SecurityContext', r'BCryptPasswordEncoder'],
                'javascript': [r'passport', r'jwt\.sign', r'bcrypt\.hash', r'authenticate'],
            },
            'input_validation': {
                'python': [r'from\s+pydantic', r'validate', r'validator', r'ValidationError'],
                'java': [r'@Valid', r'@NotNull', r'@Pattern', r'javax\.validation'],
                'javascript': [r'joi\.', r'validator\.', r'express-validator'],
            },
            'middleware': {
                'python': [r'@middleware', r'def\s+\w+_middleware', r'MIDDLEWARE'],
                'javascript': [r'app\.use\(', r'function\s+\w+.*next\)'],
            },
        }
    
    def extract_skills(
        self,
        code_analysis: Optional[Dict] = None,
        git_analysis: Optional[Dict] = None,
        file_contents: Optional[Dict[str, str]] = None,
        repo_path: Optional[str] = None
    ) -> Dict[str, Skill]:
        """
        Extract skills from various analysis sources.
        
        Args:
            code_analysis: Results from CodeAnalyzer (metrics, complexity, etc.)
            git_analysis: Results from git repository analysis
            file_contents: Dictionary mapping file paths to their content
            repo_path: Path to git repository for extracting file timestamps
        
        Returns:
            Dictionary mapping skill names to Skill objects
        """
        self.skills = {}
        
        # Only reset timestamps if we're going to extract new ones
        if repo_path:
            self.file_timestamps = {}
            self._extract_git_timestamps(repo_path)
        
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
    
    def _extract_git_timestamps(self, repo_path: str):
        """Extract last modification timestamps for files in git repository."""
        try:
            # Get all tracked files with their last commit dates
            result = subprocess.run(
                ['git', 'ls-files', '-z'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            files = result.stdout.strip('\0').split('\0')
            files = [f for f in files if f]  # Remove empty strings
            
            for file_path in files:
                try:
                    # Get last commit date for this file
                    result = subprocess.run(
                        ['git', 'log', '-1', '--format=%cI', '--', file_path],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    timestamp = result.stdout.strip()
                    if timestamp:
                        # Normalize file path for matching
                        import os
                        full_path = os.path.join(repo_path, file_path)
                        self.file_timestamps[full_path] = timestamp
                        self.file_timestamps[file_path] = timestamp  # Also store relative path
                except subprocess.CalledProcessError:
                    continue
                    
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to extract git timestamps: {e}")
        except FileNotFoundError:
            self.logger.warning("Git not found in PATH")
        except (NotADirectoryError, OSError) as e:
            self.logger.warning(f"Invalid repository path: {e}")
    
    def _extract_from_git_analysis(self, git_analysis: Dict):
        """Extract skills from git repository analysis."""
        
        # Get most recent timestamp from timeline
        timeline = git_analysis.get('timeline', [])
        latest_timestamp = None
        if timeline:
            # Timeline is sorted by month, get the last one
            latest_month = timeline[-1]['month']
            latest_timestamp = f"{latest_month}-01T00:00:00Z"
        
        # Check for version control skills
        commit_count = git_analysis.get('commit_count', 0)
        if commit_count > 0:
            evidence = SkillEvidence(
                skill_name="Version Control (Git)",
                evidence_type="practice",
                description=f"Managed {commit_count} commits",
                file_path=git_analysis.get('path', 'repository'),
                confidence=0.8,
                timestamp=latest_timestamp
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
                confidence=0.9,
                timestamp=latest_timestamp
            )
            self._add_skill(
                "Team Collaboration",
                "practices",
                "Works effectively in team environments",
                evidence
            )
        
        # Check for consistent contribution
        if len(timeline) >= 3:
            evidence = SkillEvidence(
                skill_name="Consistent Development",
                evidence_type="practice",
                description=f"Active development across {len(timeline)} time periods",
                file_path=git_analysis.get('path', 'repository'),
                confidence=0.7,
                timestamp=latest_timestamp
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
            
            # Check frameworks
            self._check_patterns(
                content, file_path, language,
                self.framework_patterns, "frameworks",
                {
                    'react': "React Framework",
                    'vue': "Vue.js Framework",
                    'angular': "Angular Framework",
                    'django': "Django Framework",
                    'flask': "Flask Framework",
                    'express': "Express.js Framework",
                    'spring': "Spring Framework",
                    'nextjs': "Next.js Framework",
                }
            )
            
            # Check database patterns
            self._check_patterns(
                content, file_path, language,
                self.database_patterns, "databases",
                {
                    'sql_queries': "SQL Database Queries",
                    'orm': "Object-Relational Mapping (ORM)",
                    'mongodb': "MongoDB",
                    'redis': "Redis Caching",
                }
            )
            
            # Check architecture patterns
            self._check_patterns(
                content, file_path, language,
                self.architecture_patterns, "architecture",
                {
                    'mvc': "MVC Architecture",
                    'rest_api': "RESTful API Design",
                    'microservices': "Microservices Architecture",
                    'authentication': "Authentication & Authorization",
                    'input_validation': "Input Validation",
                    'middleware': "Middleware Pattern",
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
        
        # Get timestamp for this file
        timestamp = self._get_file_timestamp(file_path)
        
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
                        confidence=min(1.0, len(matches) * 0.3 + 0.4),
                        timestamp=timestamp
                    )
                    
                    # Add skill with evidence
                    description = self._get_skill_description(skill_name, category, pattern_key)
                    self._add_skill(skill_name, category, description, evidence)
    
    def _get_file_timestamp(self, file_path: str) -> Optional[str]:
        """Get the timestamp for a file from cache."""
        # Try exact match first
        if file_path in self.file_timestamps:
            return self.file_timestamps[file_path]
        
        # Try to find by basename match
        import os
        basename = os.path.basename(file_path)
        for cached_path, timestamp in self.file_timestamps.items():
            if os.path.basename(cached_path) == basename:
                return timestamp
        
        return None
    
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
            
            # Frameworks
            "React Framework": "Builds user interfaces with React component library",
            "Vue.js Framework": "Develops reactive web applications using Vue.js",
            "Angular Framework": "Creates enterprise-scale applications with Angular",
            "Django Framework": "Builds web applications with Django Python framework",
            "Flask Framework": "Develops lightweight web services with Flask",
            "Express.js Framework": "Creates Node.js web servers with Express",
            "Spring Framework": "Builds Java enterprise applications with Spring",
            "Next.js Framework": "Develops server-side rendered React applications",
            
            # Databases
            "SQL Database Queries": "Writes and optimizes SQL queries for relational databases",
            "Object-Relational Mapping (ORM)": "Uses ORM tools to interact with databases",
            "MongoDB": "Works with MongoDB NoSQL database",
            "Redis Caching": "Implements caching strategies with Redis",
            
            # Architecture
            "MVC Architecture": "Implements Model-View-Controller design pattern",
            "RESTful API Design": "Designs and implements RESTful web APIs",
            "Microservices Architecture": "Builds distributed systems with microservices",
            "Authentication & Authorization": "Implements secure authentication systems",
            "Input Validation": "Validates and sanitizes user input for security",
            "Middleware Pattern": "Uses middleware for request/response processing",
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
    
    def get_chronological_overview(self) -> List[Dict[str, Any]]:
        """Get chronological list of skills exercised over time.
        
        Returns a list of dictionaries with timestamp and skills exercised at that time,
        sorted from oldest to newest.
        """
        # Collect all evidence with timestamps
        timeline_entries = []
        
        for skill in self.skills.values():
            for evidence in skill.evidence:
                if evidence.timestamp:
                    timeline_entries.append({
                        'timestamp': evidence.timestamp,
                        'skill_name': skill.name,
                        'skill_category': skill.category,
                        'evidence_type': evidence.evidence_type,
                        'description': evidence.description,
                        'file_path': evidence.file_path,
                        'line_number': evidence.line_number,
                        'confidence': evidence.confidence
                    })
        
        # Sort by timestamp
        timeline_entries.sort(key=lambda x: x['timestamp'])
        
        # Group by time period (month) for overview
        from collections import defaultdict
        monthly_skills = defaultdict(lambda: {'skills': set(), 'details': []})
        
        for entry in timeline_entries:
            # Extract year-month from ISO timestamp
            period = entry['timestamp'][:7]  # Get YYYY-MM
            monthly_skills[period]['skills'].add(entry['skill_name'])
            monthly_skills[period]['details'].append(entry)
        
        # Format overview
        overview = []
        for period in sorted(monthly_skills.keys()):
            data = monthly_skills[period]
            overview.append({
                'period': period,
                'skills_exercised': sorted(data['skills']),
                'skill_count': len(data['skills']),
                'evidence_count': len(data['details']),
                'details': data['details']
            })
        
        return overview
    
    def get_skill_progression(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get skill progression over time showing how skills evolved.
        
        Returns a dictionary mapping skill names to their progression timeline.
        Each entry shows when the skill was used and at what level.
        """
        skill_timeline = defaultdict(list)
        
        for skill in self.skills.values():
            # Collect all dated evidence for this skill
            dated_evidence = [ev for ev in skill.evidence if ev.timestamp]
            
            if not dated_evidence:
                continue
            
            # Sort by timestamp
            dated_evidence.sort(key=lambda ev: ev.timestamp)
            
            # Track skill usage over time
            for i, evidence in enumerate(dated_evidence):
                period = evidence.timestamp[:7]  # YYYY-MM
                
                # Calculate proficiency at this point (cumulative)
                proficiency_at_time = min(1.0, (i + 1) * 0.2 + 0.2)
                
                skill_timeline[skill.name].append({
                    'period': period,
                    'timestamp': evidence.timestamp,
                    'proficiency': proficiency_at_time,
                    'evidence_count': i + 1,
                    'file': evidence.file_path,
                    'description': evidence.description
                })
        
        return dict(skill_timeline)
    
    def get_skill_adoption_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline showing when new skills were first adopted.
        
        Returns a list of skills with their first usage date, sorted chronologically.
        """
        skill_adoptions = []
        
        for skill in self.skills.values():
            # Find earliest evidence with timestamp
            dated_evidence = [ev for ev in skill.evidence if ev.timestamp]
            
            if not dated_evidence:
                continue
            
            earliest = min(dated_evidence, key=lambda ev: ev.timestamp)
            
            skill_adoptions.append({
                'skill_name': skill.name,
                'category': skill.category,
                'first_used': earliest.timestamp,
                'first_used_period': earliest.timestamp[:7],
                'file': earliest.file_path,
                'current_proficiency': skill.proficiency_score,
                'total_usage': len(skill.evidence)
            })
        
        # Sort by first usage
        skill_adoptions.sort(key=lambda x: x['first_used'])
        
        return skill_adoptions
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export skills to dictionary format for JSON serialization."""
        
        chronological = self.get_chronological_overview()
        skill_progression = self.get_skill_progression()
        skill_adoption = self.get_skill_adoption_timeline()
        
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
                            "timestamp": ev.timestamp,
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
            },
            "chronological_overview": chronological,
            "skill_progression": skill_progression,
            "skill_adoption_timeline": skill_adoption
        }
