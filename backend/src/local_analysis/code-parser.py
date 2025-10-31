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