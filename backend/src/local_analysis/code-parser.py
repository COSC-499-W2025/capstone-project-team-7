"""
Improved Compact Code Analyzer - Sweet spot between size and insights
~450 lines with actionable insights for refactoring
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import time

try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    import tree_sitter_java as tsjava
    import tree_sitter_c as tsc
    import tree_sitter_cpp as tscpp
    import tree_sitter_go as tsgo
    import tree_sitter_rust as tsrust
    import tree_sitter_ruby as tsruby
    import tree_sitter_php as tsphp
    import tree_sitter_c_sharp as tscsharp
    import tree_sitter_html as tshtml
    import tree_sitter_css as tscss
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGUAGES = {
    'python': {'ext': ['.py', '.pyw'], 'mod': tspython if TREE_SITTER_AVAILABLE else None},
    'javascript': {'ext': ['.js', '.mjs'], 'mod': tsjavascript if TREE_SITTER_AVAILABLE else None},
    'typescript': {'ext': ['.ts'], 'mod': tstypescript if TREE_SITTER_AVAILABLE else None},
    'tsx': {'ext': ['.tsx'], 'mod': tstypescript if TREE_SITTER_AVAILABLE else None},
    'java': {'ext': ['.java'], 'mod': tsjava if TREE_SITTER_AVAILABLE else None},
    'c': {'ext': ['.c', '.h'], 'mod': tsc if TREE_SITTER_AVAILABLE else None},
    'cpp': {'ext': ['.cpp', '.cc', '.hpp'], 'mod': tscpp if TREE_SITTER_AVAILABLE else None},
    'go': {'ext': ['.go'], 'mod': tsgo if TREE_SITTER_AVAILABLE else None},
    'rust': {'ext': ['.rs'], 'mod': tsrust if TREE_SITTER_AVAILABLE else None},
    'ruby': {'ext': ['.rb'], 'mod': tsruby if TREE_SITTER_AVAILABLE else None},
    'php': {'ext': ['.php', '.phtml'], 'mod': tsphp if TREE_SITTER_AVAILABLE else None},
    'csharp': {'ext': ['.cs'], 'mod': tscsharp if TREE_SITTER_AVAILABLE else None},
    'html': {'ext': ['.html', '.htm'], 'mod': tshtml if TREE_SITTER_AVAILABLE else None},
    'css': {'ext': ['.css', '.scss', '.sass'], 'mod': tscss if TREE_SITTER_AVAILABLE else None},
}

EXCLUDED_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist'}


@dataclass
class FunctionMetrics:
    """Metrics for a single function"""
    name: str
    lines: int
    complexity: int
    params: int = 0
    
    @property
    def needs_refactor(self) -> bool:
        """Quick heuristic for refactoring need"""
        return self.lines > 50 or self.complexity > 10 or self.params > 5


@dataclass
class Metrics:
    """File-level metrics with actionable insights"""
    lines: int = 0
    code_lines: int = 0
    comments: int = 0
    functions: int = 0
    classes: int = 0
    complexity: int = 0
    
    # New: Top complex/long functions for targeting refactoring
    top_functions: List[FunctionMetrics] = field(default_factory=list)
    
    # Categorized issues
    security_issues: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def maintainability_score(self) -> float:
        """Simple 0-100 maintainability score"""
        if self.code_lines == 0:
            return 100.0
        
        # Penalty factors
        complexity_penalty = min(40, self.complexity * 2)
        comment_ratio = (self.comments / (self.code_lines + self.comments)) * 100
        comment_penalty = max(0, 20 - comment_ratio)
        
        avg_func_length = self.code_lines / max(1, self.functions)
        length_penalty = min(20, avg_func_length / 5)
        
        score = 100 - complexity_penalty - comment_penalty - length_penalty
        return max(0, min(100, score))
    
    @property
    def refactor_priority(self) -> str:
        """Priority level for refactoring"""
        score = self.maintainability_score
        needs_refactor = any(f.needs_refactor for f in self.top_functions)
        
        if score < 40 or (needs_refactor and score < 60):
            return "HIGH"
        elif score < 70 or needs_refactor:
            return "MEDIUM"
        return "LOW"


@dataclass
class FileResult:
    """Analysis result for a single file"""
    path: str
    language: str = ""
    success: bool = False
    metrics: Optional[Metrics] = None
    size_mb: float = 0.0
    time_ms: float = 0.0
    error: str = ""


@dataclass
class DirectoryResult:
    """Analysis result for directory"""
    path: str
    files: List[FileResult] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    
    @property
    def successful(self) -> int:
        return sum(1 for f in self.files if f.success)
    
    @property
    def failed(self) -> int:
        return sum(1 for f in self.files if not f.success)
    
    def get_refactor_candidates(self, limit: int = 10) -> List[FileResult]:
        """Get files that most need refactoring"""
        candidates = [f for f in self.files if f.success and f.metrics]
        candidates.sort(key=lambda f: f.metrics.maintainability_score)
        return candidates[:limit]
    
    
class CodeAnalyzer:
    """Improved compact analyzer with actionable insights"""
    
    def __init__(
        self,
        max_file_mb: float = 5.0,
        max_depth: int = 10,
        languages: Optional[Set[str]] = None,
        excluded: Optional[Set[str]] = None
    ):
        if not TREE_SITTER_AVAILABLE:
            raise ImportError("tree-sitter not available")
        
        self.max_file_mb = max_file_mb
        self.max_depth = max_depth
        self.enabled_langs = languages or set(LANGUAGES.keys())
        self.excluded_dirs = excluded or EXCLUDED_DIRS
        self.parsers = self._init_parsers()
    
    def _init_parsers(self) -> Dict[str, Parser]:
        """Initialize parsers"""
        parsers = {}
        for lang, config in LANGUAGES.items():
            if lang in self.enabled_langs and config['mod']:
                try:
                    language = Language(config['mod'].language())
                    parsers[lang] = Parser(language)
                except Exception as e:
                    logger.warning(f"Failed to init {lang}: {e}")
        return parsers
    
    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect language from extension"""
        ext = path.suffix.lower()
        for lang, config in LANGUAGES.items():
            if ext in config['ext'] and lang in self.parsers:
                return lang
        return None
    
    def _get_function_info(self, node: Node, code: bytes) -> Optional[FunctionMetrics]:
        """Extract function metrics"""
        func_types = {'function_definition', 'function_declaration', 'method_definition', 'function_item'}
        if node.type not in func_types:
            return None
        
        # Get name
        name = "anonymous"
        for child in node.children:
            if child.type in {'identifier', 'property_identifier'}:
                name = code[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
                break
        
        # Calculate metrics
        lines = node.end_point[0] - node.start_point[0] + 1
        complexity = self._count_complexity(node)
        
        # Count parameters
        params = 0
        for child in node.children:
            if child.type in {'parameters', 'parameter_list', 'formal_parameters'}:
                params = sum(1 for c in child.children if c.type not in {',', '(', ')'})
                break
        
        return FunctionMetrics(name=name, lines=lines, complexity=complexity, params=params)
    
    def _count_complexity(self, node: Node) -> int:
        """Count cyclomatic complexity"""
        complexity = 1
        branch_nodes = {
            'if_statement', 'elif_clause', 'else_clause', 'for_statement', 'while_statement',
            'case_statement', 'catch_clause', 'except_clause', 'conditional_expression'
        }
        
        def walk(n: Node):
            nonlocal complexity
            if n.type in branch_nodes:
                complexity += 1
            for child in n.children:
                walk(child)
        
        walk(node)
        return complexity
    
    def _find_functions(self, node: Node, code: bytes) -> List[FunctionMetrics]:
        """Find all functions with metrics"""
        functions = []
        func_types = {'function_definition', 'function_declaration', 'method_definition', 'function_item'}
        
        def walk(n: Node):
            if n.type in func_types:
                func = self._get_function_info(n, code)
                if func:
                    functions.append(func)
            for child in n.children:
                walk(child)
        
        walk(node)
        return functions
    
    
    def _count_nodes(self, node: Node, node_types: Set[str]) -> int:
        """Count nodes of specific types"""
        count = 0
        def walk(n: Node):
            nonlocal count
            if n.type in node_types:
                count += 1
            for child in n.children:
                walk(child)
        walk(node)
        return count
    
    def _count_lines(self, code: str, root: Node) -> Tuple[int, int]:
        """Count code and comment lines"""
        lines = code.split('\n')
        blank = sum(1 for line in lines if not line.strip())
        
        comments = 0
        comment_types = {'comment', 'line_comment', 'block_comment', 'documentation_comment'}
        
        def walk(node: Node):
            nonlocal comments
            if node.type in comment_types:
                comments += (node.end_point[0] - node.start_point[0] + 1)
            for child in node.children:
                walk(child)
        
        walk(root)
        code_lines = len(lines) - blank - comments
        return code_lines, comments
    
    def _find_issues(self, code: str) -> Tuple[List[str], List[str], List[str]]:
        """Categorize issues: security, todos, warnings"""
        lines = code.split('\n')
        security = []
        todos = []
        warnings = []
        
        # Security patterns
        sec_patterns = [
            ('exec(', 'Code execution'),
            ('eval(', 'Code execution'),
            ('password =', 'Hardcoded password'),
            ('api_key =', 'Hardcoded API key'),
            ('secret =', 'Hardcoded secret'),
            ('shell=True', 'Shell injection risk'),
        ]
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower().strip()
            
            # Skip comments
            if line_lower.startswith('#') or line_lower.startswith('//'):
                continue
            
            # Check security
            for pattern, desc in sec_patterns:
                if pattern in line_lower:
                    security.append(f"Line {i}: {desc}")
            
            # Check TODOs
            if any(marker in line.upper() for marker in ['TODO', 'FIXME', 'HACK', 'XXX']):
                todos.append(f"Line {i}: {line.strip()[:50]}")
        
        return security, todos, warnings
    
    def analyze_file(self, path: Path) -> FileResult:
        """Analyze a single file with actionable insights"""
        start = time.time()
        result = FileResult(path=str(path))
        
        try:
            lang = self._detect_language(path)
            if not lang:
                result.error = f"Unsupported: {path.suffix}"
                return result
            
            result.language = lang
            
            size_bytes = path.stat().st_size
            result.size_mb = size_bytes / (1024 * 1024)
            if result.size_mb > self.max_file_mb:
                result.error = f"Too large: {result.size_mb:.2f}MB"
                return result
            
            with open(path, 'rb') as f:
                code_bytes = f.read()
            
            code = code_bytes.decode('utf-8', errors='ignore')
            parser = self.parsers[lang]
            tree = parser.parse(code_bytes)
            root = tree.root_node
            
            # Extract metrics
            metrics = Metrics()
            metrics.lines = len(code.split('\n'))
            metrics.code_lines, metrics.comments = self._count_lines(code, root)
            
            # Count structures
            class_types = {'class_definition', 'class_declaration'}
            metrics.classes = self._count_nodes(root, class_types)
            
            # Get function details
            all_functions = self._find_functions(root, code_bytes)
            metrics.functions = len(all_functions)
            
            # Keep top 5 most problematic functions
            all_functions.sort(key=lambda f: (f.complexity * 2 + f.lines), reverse=True)
            metrics.top_functions = all_functions[:5]
            
            # Overall complexity
            metrics.complexity = self._count_complexity(root)
            
            # Categorize issues
            metrics.security_issues, metrics.todos, metrics.warnings = self._find_issues(code)
            
            if root.has_error:
                metrics.warnings.append("Syntax errors detected")
            
            result.metrics = metrics
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Error analyzing {path.name}: {e}")
        
        result.time_ms = (time.time() - start) * 1000
        return result
    
    def walk_directory(self, path: Path, depth: int = 0) -> List[Path]:
        """Recursively walk directory"""
        if depth >= self.max_depth:
            return []
        
        files = []
        supported_exts = set()
        for lang, config in LANGUAGES.items():
            if lang in self.enabled_langs:
                supported_exts.update(config['ext'])
        
        try:
            for item in path.iterdir():
                if item.is_dir():
                    if item.name not in self.excluded_dirs and not item.name.startswith('.'):
                        files.extend(self.walk_directory(item, depth + 1))
                elif item.is_file() and item.suffix.lower() in supported_exts:
                    files.append(item)
        except PermissionError:
            logger.warning(f"Permission denied: {path}")
        
        return files
    
    def analyze_directory(self, path: Path, recursive: bool = True) -> DirectoryResult:
        """Analyze directory with prioritized insights"""
        logger.info(f"Analyzing: {path}")
        result = DirectoryResult(path=str(path))
        
        if recursive:
            files = self.walk_directory(path)
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        logger.info(f"Found {len(files)} files")
        
        for file_path in files:
            file_result = self.analyze_file(file_path)
            result.files.append(file_result)
        
        result.summary = self._summarize(result.files)
        
        logger.info(f"Complete: {result.successful} analyzed")
        return result
    
    def _summarize(self, results: List[FileResult]) -> Dict:
        """Generate actionable summary"""
        summary = {
            'total_files': len(results),
            'successful': sum(1 for r in results if r.success),
            'languages': defaultdict(int),
            'total_lines': 0,
            'total_code': 0,
            'total_comments': 0,
            'total_functions': 0,
            'total_classes': 0,
            'avg_complexity': 0,
            'avg_maintainability': 0,
            'security_issues': 0,
            'todos': 0,
            'high_priority_files': 0,
            'functions_needing_refactor': 0,
        }
        
        complexities = []
        maintainability_scores = []
        
        for r in results:
            if r.success and r.metrics:
                m = r.metrics
                summary['languages'][r.language] += 1
                summary['total_lines'] += m.lines
                summary['total_code'] += m.code_lines
                summary['total_comments'] += m.comments
                summary['total_functions'] += m.functions
                summary['total_classes'] += m.classes
                summary['security_issues'] += len(m.security_issues)
                summary['todos'] += len(m.todos)
                
                complexities.append(m.complexity)
                maintainability_scores.append(m.maintainability_score)
                
                if m.refactor_priority == "HIGH":
                    summary['high_priority_files'] += 1
                
                summary['functions_needing_refactor'] += sum(
                    1 for f in m.top_functions if f.needs_refactor
                )
        
        if complexities:
            summary['avg_complexity'] = sum(complexities) / len(complexities)
        if maintainability_scores:
            summary['avg_maintainability'] = sum(maintainability_scores) / len(maintainability_scores)
        
        summary['languages'] = dict(summary['languages'])
        return summary
