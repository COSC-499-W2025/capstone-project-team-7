"""
Improved Compact Code Analyzer - Compatible with all tree-sitter module APIs
~450 lines with actionable insights for refactoring
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import time
import sys

# Add local lib directory to Python path
lib_path = Path(__file__).parent / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

try:
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Define placeholder for type hints when tree_sitter is not available
    if TYPE_CHECKING:
        from typing import Any as Node
    else:
        Node = None

# Try to import each language module separately
_language_modules = {}
if TREE_SITTER_AVAILABLE:
    try:
        import tree_sitter_python as tspython
        _language_modules['python'] = tspython
    except ImportError:
        pass
    
    try:
        import tree_sitter_javascript as tsjavascript
        _language_modules['javascript'] = tsjavascript
    except ImportError:
        pass
    
    try:
        import tree_sitter_typescript as tstypescript
        _language_modules['typescript'] = tstypescript
        _language_modules['tsx'] = tstypescript  # BOTH use same module!
    except ImportError:
        pass
    
    try:
        import tree_sitter_java as tsjava
        _language_modules['java'] = tsjava
    except ImportError:
        pass
    
    try:
        import tree_sitter_c as tsc
        _language_modules['c'] = tsc
    except ImportError:
        pass
    
    try:
        import tree_sitter_cpp as tscpp
        _language_modules['cpp'] = tscpp
    except ImportError:
        pass
    
    try:
        import tree_sitter_go as tsgo
        _language_modules['go'] = tsgo
    except ImportError:
        pass
    
    try:
        import tree_sitter_rust as tsrust
        _language_modules['rust'] = tsrust
    except ImportError:
        pass
    
    try:
        import tree_sitter_ruby as tsruby
        _language_modules['ruby'] = tsruby
    except ImportError:
        pass
    
    try:
        import tree_sitter_php as tsphp
        _language_modules['php'] = tsphp
    except ImportError:
        pass
    
    try:
        import tree_sitter_c_sharp as tscsharp
        _language_modules['csharp'] = tscsharp
    except ImportError:
        pass
    
    try:
        import tree_sitter_html as tshtml
        _language_modules['html'] = tshtml
    except ImportError:
        pass
    
    try:
        import tree_sitter_css as tscss
        _language_modules['css'] = tscss
    except ImportError:
        pass

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Language configuration with extensions and modules
SUPPORTED_LANGS = {
    'python': {'ext': ['.py', '.pyw'], 'mod': _language_modules.get('python')},
    'javascript': {'ext': ['.js', '.mjs'], 'mod': _language_modules.get('javascript')},
    'typescript': {'ext': ['.ts'], 'mod': _language_modules.get('typescript')},
    'tsx': {'ext': ['.tsx'], 'mod': _language_modules.get('tsx')},
    'java': {'ext': ['.java'], 'mod': _language_modules.get('java')},
    'c': {'ext': ['.c', '.h'], 'mod': _language_modules.get('c')},
    'cpp': {'ext': ['.cpp', '.cc', '.hpp'], 'mod': _language_modules.get('cpp')},
    'go': {'ext': ['.go'], 'mod': _language_modules.get('go')},
    'rust': {'ext': ['.rs'], 'mod': _language_modules.get('rust')},
    'ruby': {'ext': ['.rb'], 'mod': _language_modules.get('ruby')},
    'php': {'ext': ['.php', '.phtml'], 'mod': _language_modules.get('php')},
    'csharp': {'ext': ['.cs'], 'mod': _language_modules.get('csharp')},
    'html': {'ext': ['.html', '.htm'], 'mod': _language_modules.get('html')},
    'css': {'ext': ['.css', '.scss', '.sass'], 'mod': _language_modules.get('css')},
}

EXCLUDED_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist'}


def get_language(lang_name: str):
    """
    Get Language object from tree-sitter module.
    Handles different module APIs (language(), language_typescript(), language_tsx(), etc.)
    """
    if lang_name not in _language_modules or _language_modules[lang_name] is None:
        raise ValueError(f"Language module not available for {lang_name}")
    
    module = _language_modules[lang_name]
    
    # Try different API patterns
    try:
        # Pattern 1: module.language() - Most common
        if hasattr(module, 'language') and callable(module.language):
            return Language(module.language())
        
        # Pattern 2: module.language_<name>() - Used by TypeScript, TSX
        # TypeScript module has: language_typescript() and language_tsx()
        func_name = f'language_{lang_name}'
        if hasattr(module, func_name) and callable(getattr(module, func_name)):
            lang_func = getattr(module, func_name)
            return Language(lang_func())
        
        # Pattern 3: Check for PHP special case
        if lang_name == 'php' and hasattr(module, 'language_php'):
            return Language(module.language_php())
        
        # If we get here, we couldn't find the right function
        available_funcs = [name for name in dir(module) if name.startswith('language')]
        raise AttributeError(
            f"Could not find language function for {lang_name}. "
            f"Available: {available_funcs}"
        )
        
    except Exception as e:
        raise ValueError(f"Failed to load language {lang_name}: {e}")


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
        # Maintainability score calculation (0-100 scale):
        # Starts at 100, then subtracts penalties:
        # - Complexity penalty: min(40, complexity * 2) - up to 40 points
        # - Comment penalty: max(0, 20 - comment_ratio) - up to 20 points
        #   where comment_ratio = (comments / (code + comments)) * 100
        # - Length penalty: min(20, avg_func_length / 5) - up to 20 points
         # Score is clamped to 0-100 range
        # Higher scores indicate more maintainable code
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
        self.enabled_langs = languages or set(SUPPORTED_LANGS.keys())
        self.excluded_dirs = excluded or EXCLUDED_DIRS
        self.parsers = self._init_parsers()
    
    def _init_parsers(self):
        """
        Initialize parsers for all supported languages.
        Uses tree-sitter 0.21.0+ API: Parser(language)
        """
        parsers = {}
        for lang in SUPPORTED_LANGS:
            if lang not in self.enabled_langs:
                continue
            
            # Check if module is available
            if SUPPORTED_LANGS[lang]['mod'] is None:
                logger.debug(f"Skipping {lang}: module not imported")
                continue
            
            try:
                # Get language using our flexible loader
                language = get_language(lang)
                parser = Parser(language)
                parsers[lang] = parser
                logger.debug(f"Parser initialized for {lang}")
            except Exception as e:
                logger.warning(f"Failed parser for {lang}: {e}")
        return parsers
    
    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect language from extension"""
        ext = path.suffix.lower()
        for lang, config in SUPPORTED_LANGS.items():
            if ext in config['ext'] and lang in self.parsers:
                return lang
        return None
    
    def _get_function_info(self, node: Node, code: bytes) -> Optional[FunctionMetrics]:
        """Extract function metrics"""
        func_types = {'function_definition', 'function_declaration', 'method_definition', 
                      'function_item', 'function', 'method_declaration', 'arrow_function',
                      'function_expression'}
        if node.type not in func_types:
            return None
        
        # Get name
        name = "anonymous"
        for child in node.children:
            if child.type in {'identifier', 'property_identifier', 'field_identifier'}:
                name = code[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
                break
        
        # Calculate metrics
        lines = node.end_point[0] - node.start_point[0] + 1
        complexity = self._count_complexity(node)
        
        # Count parameters
        params = 0
        for child in node.children:
            if child.type in {'parameters', 'parameter_list', 'formal_parameters', 'required_parameters'}:
                params = sum(1 for c in child.children if c.type not in {',', '(', ')', 'required_parameter', 'optional_parameter'} and 'parameter' in c.type)
                if params == 0:  # Fallback counting
                    params = sum(1 for c in child.children if c.type in {'identifier', 'required_parameter', 'optional_parameter'})
                break
        
        return FunctionMetrics(name=name, lines=lines, complexity=complexity, params=params)
    
    def _count_complexity(self, node: Node) -> int:
        """Count cyclomatic complexity"""
        complexity = 1
        branch_nodes = {
            'if_statement', 'elif_clause', 'else_clause', 'for_statement', 'while_statement',
            'case_statement', 'catch_clause', 'except_clause', 'conditional_expression',
            'switch_statement', 'ternary_expression', 'match_statement'
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
        func_types = {'function_definition', 'function_declaration', 'method_definition', 
                      'function_item', 'function', 'method_declaration', 'arrow_function',
                      'function_expression'}
        
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
            class_types = {'class_definition', 'class_declaration', 'class_specifier'}
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
        for lang, config in SUPPORTED_LANGS.items():
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


if __name__ == "__main__":
    import sys
    
    print(f"\n{'='*70}")
    print("CODE ANALYZER - Testing Mode")
    print('='*70)
    
    # Get directory from command line or use current directory
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path(".")
    
    print(f"\n🔍 Target: {target_path.absolute()}")
    
    # Create analyzer with default settings
    print("\n⚙️  Initializing analyzer...")
    try:
        analyzer = CodeAnalyzer(
            max_file_mb=5.0,
            max_depth=10,
            excluded={'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist'}
        )
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Install required packages:")
        print("   pip install --target=lib tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
        sys.exit(1)
    
    print(f"   Languages enabled: {', '.join(sorted(analyzer.enabled_langs))}")
    print(f"   Parsers initialized: {len(analyzer.parsers)}")
    
    if len(analyzer.parsers) == 0:
        print("\n⚠️  WARNING: No parsers were initialized!")
        print("   Run: pip install --target=lib tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
        sys.exit(1)
    
    # Show which parsers loaded successfully
    print(f"   Successfully loaded: {', '.join(sorted(analyzer.parsers.keys()))}")
    
    # Analyze the directory
    print(f"\n📂 Analyzing directory...")
    result = analyzer.analyze_directory(target_path)
    
    # Display results
    print(f"\n{'='*70}")
    print("ANALYSIS RESULTS")
    print('='*70)
    
    print(f"\n📊 Files:")
    print(f"   Total found: {len(result.files)}")
    print(f"   Successfully analyzed: {result.successful}")
    print(f"   Failed: {result.failed}")
    
    if result.summary['languages']:
        print(f"\n🗂️  Languages Detected:")
        for lang, count in sorted(result.summary['languages'].items(), 
                                  key=lambda x: x[1], reverse=True):
            print(f"   {lang:15} {count:3} files")
    
    print(f"\n📈 Code Metrics:")
    print(f"   Total Lines:       {result.summary['total_lines']:,}")
    print(f"   Code Lines:        {result.summary['total_code']:,}")
    print(f"   Comment Lines:     {result.summary['total_comments']:,}")
    print(f"   Functions:         {result.summary['total_functions']}")
    print(f"   Classes:           {result.summary['total_classes']}")
    
    if result.successful > 0:
        print(f"\n🎯 Quality Metrics:")
        print(f"   Avg Maintainability: {result.summary['avg_maintainability']:.1f}/100")
        print(f"   Avg Complexity:      {result.summary['avg_complexity']:.1f}")
        
        # Quality assessment
        maintainability = result.summary['avg_maintainability']
        if maintainability >= 80:
            status = "✅ EXCELLENT"
            color_desc = "Highly maintainable code"
        elif maintainability >= 70:
            status = "✓  GOOD"
            color_desc = "Reasonably maintainable"
        elif maintainability >= 60:
            status = "⚠️  FAIR"
            color_desc = "Some areas need improvement"
        elif maintainability >= 50:
            status = "⚠️  NEEDS WORK"
            color_desc = "Consider refactoring"
        else:
            status = "❌ CRITICAL"
            color_desc = "Significant refactoring needed"
        
        print(f"   Overall Status:      {status}")
        print(f"   Assessment:          {color_desc}")
        
        print(f"\n⚠️  Issues Found:")
        print(f"   Security Issues:        {result.summary['security_issues']}")
        print(f"   TODOs/FIXMEs:          {result.summary['todos']}")
        print(f"   High Priority Files:    {result.summary['high_priority_files']}")
        print(f"   Functions Need Refactor: {result.summary['functions_needing_refactor']}")
        
        # Show top refactoring candidates
        candidates = result.get_refactor_candidates(5)
        if candidates:
            print(f"\n{'='*70}")
            print("TOP REFACTORING CANDIDATES")
            print('='*70)
            
            for i, file in enumerate(candidates, 1):
                file_name = Path(file.path).name
                try:
                    rel_path = Path(file.path).relative_to(target_path)
                except ValueError:
                    rel_path = Path(file.path)
                score = file.metrics.maintainability_score
                priority = file.metrics.refactor_priority
                
                print(f"\n{i}. {file_name}")
                print(f"   Path: {rel_path}")
                print(f"   Maintainability: {score:.0f}/100")
                print(f"   Priority: {priority}")
                print(f"   Lines: {file.metrics.lines} ({file.metrics.code_lines} code)")
                print(f"   Functions: {file.metrics.functions}")
                print(f"   Complexity: {file.metrics.complexity}")
                
                # Show problematic functions
                problem_funcs = [f for f in file.metrics.top_functions if f.needs_refactor]
                if problem_funcs:
                    print(f"   Complex functions:")
                    for func in problem_funcs[:3]:
                        print(f"      • {func.name}:")
                        print(f"        {func.lines} lines, complexity {func.complexity}, {func.params} params")
                
                # Show issues
                if file.metrics.security_issues:
                    print(f"   Security issues: {len(file.metrics.security_issues)}")
                    for issue in file.metrics.security_issues[:2]:
                        print(f"      • {issue}")
                
                if file.metrics.todos:
                    print(f"   TODOs: {len(file.metrics.todos)}")
        
        # Show some successful files
        print(f"\n{'='*70}")
        print("SAMPLE FILES ANALYZED")
        print('='*70)
        
        successful_files = [f for f in result.files if f.success][:5]
        for file in successful_files:
            try:
                rel_path = Path(file.path).relative_to(target_path)
            except ValueError:
                rel_path = Path(file.path)
            print(f"\n✓ {rel_path}")
            print(f"  Language: {file.language}")
            print(f"  Lines: {file.metrics.lines} ({file.metrics.code_lines} code)")
            print(f"  Functions: {file.metrics.functions}, Classes: {file.metrics.classes}")
            print(f"  Maintainability: {file.metrics.maintainability_score:.0f}/100")
    
    # Show failed files if any
    failed_files = [f for f in result.files if not f.success]
    if failed_files:
        print(f"\n{'='*70}")
        print("FAILED FILES")
        print('='*70)
        for file in failed_files[:10]:
            print(f"\n✗ {Path(file.path).name}")
            print(f"  Error: {file.error}")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    
    if result.successful > 0:
        maintainability = result.summary['avg_maintainability']
        if maintainability >= 70:
            status = "GOOD"
        elif maintainability >= 50:
            status = "FAIR"
        else:
            status = "NEEDS WORK"
            
        print(f"""
This analyzer found and processed {result.successful} files across 
{len(result.summary['languages'])} programming languages.

Key Takeaways:
• Overall maintainability is {maintainability:.1f}/100 ({status})
• {result.summary['high_priority_files']} files need immediate attention
• {result.summary['functions_needing_refactor']} functions should be refactored
• {result.summary['security_issues']} potential security issues found
• {result.summary['todos']} TODO/FIXME comments to address
""")
    else:
        print("\nNo files were successfully analyzed. Check the failed files list above.")
    
    print('='*70 + '\n')
