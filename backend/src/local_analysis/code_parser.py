"""
Enhanced Code Analyzer - Rich Actionable Insights
Provides specific, line-level findings with code examples.
No AI required - pure static analysis with tree-sitter.

Features:
- Dead code detection (unused functions, variables, imports)
- Duplicate/similar code detection
- Call graph analysis
- Magic numbers/strings detection
- Error handling quality analysis
- Naming convention consistency
- Nesting depth analysis
- Data structure usage tracking
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import logging
import time
import sys
import re

# Add local lib directory to Python path
lib_path = Path(__file__).parent / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

try:
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
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
        _language_modules['tsx'] = tstypescript
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
    """Get Language object from tree-sitter module."""
    if lang_name not in _language_modules or _language_modules[lang_name] is None:
        raise ValueError(f"Language module not available for {lang_name}")
    
    module = _language_modules[lang_name]
    
    try:
        if hasattr(module, 'language') and callable(module.language):
            return Language(module.language())
        
        func_name = f'language_{lang_name}'
        if hasattr(module, func_name) and callable(getattr(module, func_name)):
            lang_func = getattr(module, func_name)
            return Language(lang_func())
        
        if lang_name == 'php' and hasattr(module, 'language_php'):
            return Language(module.language_php())
        
        available_funcs = [name for name in dir(module) if name.startswith('language')]
        raise AttributeError(f"Could not find language function for {lang_name}. Available: {available_funcs}")
        
    except Exception as e:
        raise ValueError(f"Failed to load language {lang_name}: {e}")


# =============================================================================
# DATA CLASSES FOR RICH INSIGHTS
# =============================================================================

@dataclass
class DeadCodeItem:
    """Detected unused/dead code"""
    item_type: str  # "function", "variable", "import", "class", "parameter"
    name: str
    line: int
    code_snippet: str
    reason: str  # "never_called", "never_used", "never_imported", etc.
    confidence: str  # "high", "medium" - high means definitely unused in this file
    
    def to_dict(self) -> Dict:
        return {
            'type': self.item_type,
            'name': self.name,
            'line': self.line,
            'code_snippet': self.code_snippet,
            'reason': self.reason,
            'confidence': self.confidence
        }


@dataclass
class DuplicateBlock:
    """Detected duplicate/similar code block"""
    block_hash: str
    locations: List[Tuple[int, int, str]]  # [(start_line, end_line, file), ...]
    line_count: int
    sample_code: str
    similarity: float  # 1.0 = exact duplicate, 0.8+ = similar
    
    def to_dict(self) -> Dict:
        return {
            'locations': [{'start': s, 'end': e, 'file': f} for s, e, f in self.locations],
            'line_count': self.line_count,
            'sample_code': self.sample_code,
            'similarity': self.similarity,
            'occurrence_count': len(self.locations)
        }


@dataclass
class CallGraphEdge:
    """A call relationship between functions"""
    caller: str
    caller_line: int
    callee: str
    call_line: int
    
    def to_dict(self) -> Dict:
        return {
            'caller': self.caller,
            'caller_line': self.caller_line,
            'callee': self.callee,
            'call_line': self.call_line
        }


@dataclass
class MagicValue:
    """Hardcoded magic number or string"""
    value_type: str  # "number", "string"
    value: str
    line: int
    code_snippet: str
    context: str  # What it's used for (if detectable)
    suggested_name: str  # Suggested constant name
    
    def to_dict(self) -> Dict:
        return {
            'type': self.value_type,
            'value': self.value,
            'line': self.line,
            'code_snippet': self.code_snippet,
            'context': self.context,
            'suggested_name': self.suggested_name
        }


@dataclass
class ErrorHandlingIssue:
    """Issue with error/exception handling"""
    issue_type: str  # "empty_catch", "swallowed_exception", "broad_except", "no_finally", "missing_catch"
    line: int
    code_snippet: str
    description: str
    suggestion: str
    severity: str  # "critical", "warning", "info"
    
    def to_dict(self) -> Dict:
        return {
            'type': self.issue_type,
            'line': self.line,
            'code_snippet': self.code_snippet,
            'description': self.description,
            'suggestion': self.suggestion,
            'severity': self.severity
        }


@dataclass
class NamingIssue:
    """Naming convention inconsistency"""
    issue_type: str  # "inconsistent_style", "too_short", "too_long", "misleading"
    name: str
    expected_style: str  # "snake_case", "camelCase", "PascalCase", "SCREAMING_SNAKE"
    actual_style: str
    line: int
    item_type: str  # "function", "variable", "class", "constant"
    suggestion: str
    
    def to_dict(self) -> Dict:
        return {
            'type': self.issue_type,
            'name': self.name,
            'expected_style': self.expected_style,
            'actual_style': self.actual_style,
            'line': self.line,
            'item_type': self.item_type,
            'suggestion': self.suggestion
        }


@dataclass
class NestingInfo:
    """Deep nesting information"""
    function_name: str
    line: int
    max_depth: int
    nesting_path: List[str]  # ["if", "for", "try", "if"] - what creates the nesting
    code_snippet: str
    suggestion: str
    
    def to_dict(self) -> Dict:
        return {
            'function': self.function_name,
            'line': self.line,
            'max_depth': self.max_depth,
            'nesting_path': self.nesting_path,
            'code_snippet': self.code_snippet,
            'suggestion': self.suggestion
        }


@dataclass
class DataStructureUsage:
    """Track data structure usage with examples"""
    structure_type: str  # "list", "dict", "set", "array", "map", etc.
    line: int
    example: str
    context: str  # Variable name or usage context
    
    def to_dict(self) -> Dict:
        return {
            'type': self.structure_type,
            'line': self.line,
            'example': self.example,
            'context': self.context
        }


@dataclass
class FunctionInfo:
    """Basic function information for call graph and dead code detection"""
    name: str
    start_line: int
    end_line: int
    parameters: List[str]
    calls: List[str]  # Functions this function calls
    is_exported: bool  # Is this function exported/public?
    decorators: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'parameters': self.parameters,
            'calls': self.calls[:15],
            'is_exported': self.is_exported,
            'decorators': self.decorators
        }


@dataclass
class ImportInfo:
    """Import statement information"""
    line: int
    module: str
    names: List[str]  # Specific imports
    alias: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            'line': self.line,
            'module': self.module,
            'names': self.names,
            'alias': self.alias
        }


@dataclass
class Metrics:
    """Comprehensive file metrics with rich insights"""
    # Basic counts
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    
    # Structural counts
    function_count: int = 0
    class_count: int = 0
    
    # Functions for call graph
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    
    # NEW: Rich analysis results
    dead_code: List[DeadCodeItem] = field(default_factory=list)
    duplicates: List[DuplicateBlock] = field(default_factory=list)
    call_graph: List[CallGraphEdge] = field(default_factory=list)
    magic_values: List[MagicValue] = field(default_factory=list)
    error_handling_issues: List[ErrorHandlingIssue] = field(default_factory=list)
    naming_issues: List[NamingIssue] = field(default_factory=list)
    nesting_issues: List[NestingInfo] = field(default_factory=list)
    data_structures: List[DataStructureUsage] = field(default_factory=list)
    
    # Legacy compatibility
    @property
    def lines(self) -> int:
        return self.total_lines
    
    @property
    def maintainability_score(self) -> float:
        """Calculate maintainability based on issues found"""
        if self.code_lines == 0:
            return 100.0
        
        # Deductions for issues
        dead_code_penalty = min(15, len(self.dead_code) * 3)
        duplicate_penalty = min(20, len(self.duplicates) * 5)
        magic_penalty = min(10, len(self.magic_values) * 0.5)
        error_penalty = min(20, sum(5 if e.severity == 'critical' else 2 for e in self.error_handling_issues))
        naming_penalty = min(10, len(self.naming_issues) * 1)
        nesting_penalty = min(15, len(self.nesting_issues) * 3)
        
        score = 100 - dead_code_penalty - duplicate_penalty - magic_penalty - error_penalty - naming_penalty - nesting_penalty
        return max(0, min(100, score))
    
    def get_summary(self) -> Dict:
        """Get a summary dict of key metrics"""
        return {
            'lines': {
                'total': self.total_lines,
                'code': self.code_lines,
                'comments': self.comment_lines,
                'blank': self.blank_lines
            },
            'structure': {
                'functions': self.function_count,
                'classes': self.class_count,
                'imports': len(self.imports)
            },
            'analysis': {
                'dead_code_items': len(self.dead_code),
                'duplicate_blocks': len(self.duplicates),
                'call_graph_edges': len(self.call_graph),
                'magic_values': len(self.magic_values),
                'error_handling_issues': len(self.error_handling_issues),
                'naming_issues': len(self.naming_issues),
                'deep_nesting': len(self.nesting_issues),
                'data_structures': len(self.data_structures)
            },
            'maintainability_score': round(self.maintainability_score, 1)
        }


@dataclass
class FileResult:
    """Analysis result for a single file"""
    path: str
    language: str = ""
    success: bool = False
    metrics: Optional[Metrics] = None
    size_bytes: int = 0
    analysis_time_ms: float = 0.0
    error: str = ""
    
    def to_dict(self) -> Dict:
        result = {
            'path': self.path,
            'language': self.language,
            'success': self.success,
            'size_bytes': self.size_bytes,
            'analysis_time_ms': round(self.analysis_time_ms, 2),
            'error': self.error
        }
        if self.metrics:
            result['metrics'] = self.metrics.get_summary()
            result['dead_code'] = [d.to_dict() for d in self.metrics.dead_code[:15]]
            result['duplicates'] = [d.to_dict() for d in self.metrics.duplicates[:10]]
            result['call_graph'] = [c.to_dict() for c in self.metrics.call_graph[:30]]
            result['magic_values'] = [m.to_dict() for m in self.metrics.magic_values[:20]]
            result['error_handling'] = [e.to_dict() for e in self.metrics.error_handling_issues[:15]]
            result['naming_issues'] = [n.to_dict() for n in self.metrics.naming_issues[:15]]
            result['nesting_issues'] = [n.to_dict() for n in self.metrics.nesting_issues[:10]]
            result['data_structures'] = [d.to_dict() for d in self.metrics.data_structures[:20]]
        return result


@dataclass
class DirectoryResult:
    """Analysis result for a directory"""
    path: str
    files: List[FileResult] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    
    # Cross-file analysis
    cross_file_duplicates: List[DuplicateBlock] = field(default_factory=list)
    global_call_graph: Dict[str, List[str]] = field(default_factory=dict)
    
    @property
    def successful(self) -> int:
        return sum(1 for f in self.files if f.success)
    
    @property
    def failed(self) -> int:
        return sum(1 for f in self.files if not f.success)
    
    def get_all_dead_code(self, confidence: Optional[str] = None) -> List[Dict]:
        """Get all dead code items across files"""
        items = []
        for f in self.files:
            if f.success and f.metrics:
                for item in f.metrics.dead_code:
                    if confidence is None or item.confidence == confidence:
                        items.append({'file': f.path, **item.to_dict()})
        return items
    
    def get_all_duplicates(self) -> List[Dict]:
        """Get all duplicate code blocks"""
        all_dups = []
        for f in self.files:
            if f.success and f.metrics:
                for dup in f.metrics.duplicates:
                    all_dups.append({'file': f.path, **dup.to_dict()})
        # Add cross-file duplicates
        for dup in self.cross_file_duplicates:
            all_dups.append({'cross_file': True, **dup.to_dict()})
        return all_dups
    
    def get_call_graph(self) -> Dict[str, List[Dict]]:
        """Get aggregated call graph"""
        graph = defaultdict(list)
        for f in self.files:
            if f.success and f.metrics:
                for edge in f.metrics.call_graph:
                    graph[edge.caller].append({
                        'callee': edge.callee,
                        'file': Path(f.path).name,
                        'line': edge.call_line
                    })
        return dict(graph)
    
    def get_all_magic_values(self) -> List[Dict]:
        """Get all magic values across files"""
        items = []
        for f in self.files:
            if f.success and f.metrics:
                for item in f.metrics.magic_values:
                    items.append({'file': f.path, **item.to_dict()})
        return items
    
    def get_error_handling_issues(self, severity: Optional[str] = None) -> List[Dict]:
        """Get all error handling issues"""
        items = []
        for f in self.files:
            if f.success and f.metrics:
                for item in f.metrics.error_handling_issues:
                    if severity is None or item.severity == severity:
                        items.append({'file': f.path, **item.to_dict()})
        items.sort(key=lambda x: {'critical': 0, 'warning': 1, 'info': 2}.get(x['severity'], 3))
        return items
    
    def get_naming_issues(self) -> List[Dict]:
        """Get all naming convention issues"""
        items = []
        for f in self.files:
            if f.success and f.metrics:
                for item in f.metrics.naming_issues:
                    items.append({'file': f.path, **item.to_dict()})
        return items
    
    def get_nesting_issues(self) -> List[Dict]:
        """Get all deep nesting issues sorted by depth"""
        items = []
        for f in self.files:
            if f.success and f.metrics:
                for item in f.metrics.nesting_issues:
                    items.append({'file': f.path, **item.to_dict()})
        items.sort(key=lambda x: x['max_depth'], reverse=True)
        return items
    
    def get_data_structure_summary(self) -> Dict[str, List[Dict]]:
        """Summarize data structure usage with examples"""
        by_type = defaultdict(list)
        for f in self.files:
            if f.success and f.metrics:
                for ds in f.metrics.data_structures:
                    by_type[ds.structure_type].append({
                        'file': Path(f.path).name,
                        'line': ds.line,
                        'example': ds.example,
                        'context': ds.context
                    })
        return {k: v[:10] for k, v in by_type.items()}


# =============================================================================
# CODE ANALYZER
# =============================================================================

class CodeAnalyzer:
    """Enhanced analyzer providing rich, actionable insights"""
    
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
        
        # For cross-file analysis
        self._all_code_blocks: Dict[str, List[Tuple[str, int, int]]] = {}  # hash -> [(file, start, end)]
        self._all_function_defs: Dict[str, str] = {}  # func_name -> file
        self._all_function_calls: Dict[str, List[str]] = {}  # func_name -> [files where called]
    
    def _init_parsers(self):
        """Initialize parsers for all supported languages"""
        parsers = {}
        for lang in SUPPORTED_LANGS:
            if lang not in self.enabled_langs:
                continue
            if SUPPORTED_LANGS[lang]['mod'] is None:
                continue
            try:
                language = get_language(lang)
                parser = Parser(language)
                parsers[lang] = parser
            except Exception as e:
                logger.warning(f"Failed parser for {lang}: {e}")
        return parsers
    
    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect language from file extension"""
        ext = path.suffix.lower()
        for lang, config in SUPPORTED_LANGS.items():
            if ext in config['ext'] and lang in self.parsers:
                return lang
        return None
    
    def _get_node_text(self, node: Node, code: bytes) -> str:
        """Extract text from a node"""
        return code[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
    
    def _get_line_text(self, lines: List[str], line_num: int) -> str:
        """Get text of a specific line (1-indexed)"""
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1].strip()
        return ""
    
    # =========================================================================
    # DEAD CODE DETECTION
    # =========================================================================
    
    def _detect_dead_code(self, root: Node, code: bytes, lines: List[str], language: str) -> Tuple[List[DeadCodeItem], List[FunctionInfo]]:
        """Detect unused functions, variables, and imports"""
        dead_code = []
        functions = []
        
        # Collect all definitions and usages
        defined_funcs = {}  # name -> (line, snippet, is_exported)
        defined_vars = {}   # name -> (line, snippet)
        defined_imports = {}  # name -> (line, snippet, module)
        all_identifiers = set()  # All identifiers used in code
        function_calls = set()   # All function calls
        
        # Patterns for export detection
        export_decorators = {'@app.route', '@router', '@api', '@export', '@public', 'export'}
        
        def is_exported(node: Node) -> bool:
            """Check if a function/class is exported or has decorators suggesting it's used externally"""
            # Check parent for 'export' keyword
            parent = node.parent
            if parent:
                parent_text = self._get_node_text(parent, code)
                if parent_text.strip().startswith('export'):
                    return True
            
            # Check decorators (for Python)
            prev_sibling = node.prev_sibling
            while prev_sibling:
                if prev_sibling.type == 'decorator':
                    dec_text = self._get_node_text(prev_sibling, code)
                    for exp_dec in export_decorators:
                        if exp_dec in dec_text:
                            return True
                prev_sibling = prev_sibling.prev_sibling
            
            return False
        
        def collect_definitions(node: Node, current_func: Optional[str] = None):
            """Collect all definitions in the code"""
            # Function definitions
            if node.type in {'function_definition', 'function_declaration', 'method_definition', 'arrow_function'}:
                name = None
                params = []
                for child in node.children:
                    if child.type in {'identifier', 'property_identifier', 'name'}:
                        name = self._get_node_text(child, code)
                        break
                    if child.type == 'variable_declarator':
                        for c in child.children:
                            if c.type == 'identifier':
                                name = self._get_node_text(c, code)
                                break
                    if child.type in {'parameters', 'formal_parameters'}:
                        for param in child.children:
                            if param.type in {'identifier', 'required_parameter', 'optional_parameter'}:
                                param_name = self._get_node_text(param, code).split(':')[0].strip()
                                if param_name not in {'(', ')', ',', 'self', 'cls', 'this'}:
                                    params.append(param_name)
                
                if name and name not in {'anonymous', 'constructor', '__init__'}:
                    line = node.start_point[0] + 1
                    snippet = self._get_line_text(lines, line)
                    is_exp = is_exported(node)
                    defined_funcs[name] = (line, snippet, is_exp)
                    
                    # Collect calls within this function
                    calls = []
                    def find_calls(n: Node):
                        if n.type in {'call', 'call_expression'}:
                            for c in n.children:
                                if c.type in {'identifier', 'property_identifier'}:
                                    call_name = self._get_node_text(c, code)
                                    if call_name:
                                        calls.append(call_name)
                                        function_calls.add(call_name)
                                    break
                        for child in n.children:
                            find_calls(child)
                    find_calls(node)
                    
                    functions.append(FunctionInfo(
                        name=name,
                        start_line=line,
                        end_line=node.end_point[0] + 1,
                        parameters=params,
                        calls=list(set(calls)),
                        is_exported=is_exp,
                        decorators=[]
                    ))
                    
                    current_func = name
            
            # Variable definitions (top-level only for now)
            if node.type in {'assignment', 'variable_declaration', 'lexical_declaration'}:
                for child in node.children:
                    if child.type in {'identifier', 'variable_declarator'}:
                        if child.type == 'variable_declarator':
                            for c in child.children:
                                if c.type == 'identifier':
                                    var_name = self._get_node_text(c, code)
                                    if var_name and len(var_name) > 1:
                                        defined_vars[var_name] = (node.start_point[0] + 1, self._get_line_text(lines, node.start_point[0] + 1))
                                    break
                        else:
                            var_name = self._get_node_text(child, code)
                            if var_name and len(var_name) > 1:
                                defined_vars[var_name] = (node.start_point[0] + 1, self._get_line_text(lines, node.start_point[0] + 1))
            
            # Import definitions
            if node.type in {'import_statement', 'import_from_statement', 'import_declaration'}:
                line = node.start_point[0] + 1
                import_text = self._get_node_text(node, code)
                
                # Extract imported names
                for child in node.children:
                    if child.type in {'dotted_name', 'aliased_import', 'import_specifier', 'identifier'}:
                        imp_name = self._get_node_text(child, code)
                        if ' as ' in imp_name:
                            imp_name = imp_name.split(' as ')[1].strip()
                        if imp_name and imp_name not in {'from', 'import', '*'}:
                            defined_imports[imp_name] = (line, import_text.strip()[:60], '')
            
            # Collect all identifier usages
            if node.type == 'identifier':
                name = self._get_node_text(node, code)
                all_identifiers.add(name)
            
            # Recurse
            for child in node.children:
                collect_definitions(child, current_func)
        
        collect_definitions(root)
        
        # Find unused functions (not called and not exported)
        for func_name, (line, snippet, is_exp) in defined_funcs.items():
            if not is_exp and func_name not in function_calls:
                # Check if it's not a special method
                if not func_name.startswith('_') or func_name.startswith('__'):
                    if func_name.startswith('__') and func_name.endswith('__'):
                        continue  # Skip dunder methods
                    dead_code.append(DeadCodeItem(
                        item_type='function',
                        name=func_name,
                        line=line,
                        code_snippet=snippet,
                        reason='never_called',
                        confidence='medium' if not is_exp else 'low'
                    ))
        
        # Find unused imports
        for imp_name, (line, snippet, module) in defined_imports.items():
            if imp_name not in all_identifiers and imp_name not in function_calls:
                dead_code.append(DeadCodeItem(
                    item_type='import',
                    name=imp_name,
                    line=line,
                    code_snippet=snippet,
                    reason='never_used',
                    confidence='high'
                ))
        
        return dead_code, functions
    
    # =========================================================================
    # DUPLICATE CODE DETECTION
    # =========================================================================
    
    def _detect_duplicates(self, lines: List[str], file_path: str, min_lines: int = 4) -> List[DuplicateBlock]:
        """Detect duplicate code blocks within a file"""
        duplicates = []
        seen_blocks = {}  # hash -> [(start_line, end_line)]
        
        # Normalize lines (strip whitespace, ignore empty)
        normalized = [(i, line.strip()) for i, line in enumerate(lines, 1) if line.strip()]
        
        # Sliding window to find duplicate blocks
        for window_size in range(min_lines, min(20, len(normalized) // 2)):
            for i in range(len(normalized) - window_size + 1):
                block_lines = [normalized[i + j][1] for j in range(window_size)]
                block_text = '\n'.join(block_lines)
                
                # Skip blocks that are mostly braces or simple
                if all(len(l) < 5 for l in block_lines):
                    continue
                
                block_hash = hashlib.md5(block_text.encode()).hexdigest()
                start_line = normalized[i][0]
                end_line = normalized[i + window_size - 1][0]
                
                if block_hash in seen_blocks:
                    # Check for overlap with existing
                    overlaps = False
                    for existing_start, existing_end in seen_blocks[block_hash]:
                        if not (end_line < existing_start or start_line > existing_end):
                            overlaps = True
                            break
                    
                    if not overlaps:
                        seen_blocks[block_hash].append((start_line, end_line))
                else:
                    seen_blocks[block_hash] = [(start_line, end_line)]
        
        # Create DuplicateBlock for blocks with multiple occurrences
        for block_hash, locations in seen_blocks.items():
            if len(locations) >= 2:
                # Get sample code from first occurrence
                start, end = locations[0]
                sample = '\n'.join(lines[start-1:end])[:200]
                
                duplicates.append(DuplicateBlock(
                    block_hash=block_hash,
                    locations=[(s, e, file_path) for s, e in locations],
                    line_count=end - start + 1,
                    sample_code=sample,
                    similarity=1.0
                ))
        
        # Store for cross-file detection
        for block_hash, locations in seen_blocks.items():
            if block_hash not in self._all_code_blocks:
                self._all_code_blocks[block_hash] = []
            for start, end in locations:
                self._all_code_blocks[block_hash].append((file_path, start, end))
        
        return duplicates[:10]  # Limit to top 10
    
    # =========================================================================
    # CALL GRAPH
    # =========================================================================
    
    def _build_call_graph(self, functions: List[FunctionInfo]) -> List[CallGraphEdge]:
        """Build call graph from function information"""
        edges = []
        func_names = {f.name for f in functions}
        
        for func in functions:
            for call in func.calls:
                if call in func_names:  # Only internal calls
                    edges.append(CallGraphEdge(
                        caller=func.name,
                        caller_line=func.start_line,
                        callee=call,
                        call_line=func.start_line  # Approximate
                    ))
        
        return edges
    
    # =========================================================================
    # MAGIC VALUE DETECTION
    # =========================================================================
    
    def _detect_magic_values(self, lines: List[str], language: str) -> List[MagicValue]:
        """Detect hardcoded magic numbers and strings"""
        magic_values = []
        
        # Patterns for magic numbers (excluding common ones)
        safe_numbers = {'0', '1', '2', '-1', '100', '1000', '60', '24', '365', '360', '180', '90', '255', '256', '1024', '2048', '4096'}
        safe_contexts = {'range', 'enumerate', 'len', 'index', 'slice', 'padding', 'margin', 'width', 'height', 'size', 'timeout'}
        
        # Patterns for magic strings
        url_pattern = re.compile(r'https?://[^\s"\'\)]+')
        path_pattern = re.compile(r'["\'][/\\][a-zA-Z][^"\']*["\']')
        config_pattern = re.compile(r'["\'][A-Z][A-Z0-9_]{3,}["\']')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Magic numbers
            number_pattern = re.compile(r'(?<![a-zA-Z_\d\.])(\d+\.?\d*)(?![a-zA-Z_\d])')
            for match in number_pattern.finditer(stripped):
                num = match.group(1)
                
                # Skip safe numbers
                if num in safe_numbers or num.startswith('0x') or num.startswith('0b'):
                    continue
                
                # Skip if it's a small number (likely index or count)
                try:
                    if float(num) < 10 and '.' not in num:
                        continue
                except ValueError:
                    continue
                
                # Check context
                context = stripped[:match.start()].lower()
                if any(c in context for c in safe_contexts):
                    continue
                
                # Generate suggested name
                try:
                    num_val = float(num)
                    if num_val == int(num_val):
                        suggested = f"CONST_{int(num_val)}"
                    else:
                        suggested = f"VALUE_{num.replace('.', '_')}"
                except:
                    suggested = "MAGIC_NUMBER"
                
                # Try to infer context
                if 'timeout' in context.lower():
                    suggested = 'TIMEOUT_MS'
                elif 'port' in context.lower():
                    suggested = 'PORT_NUMBER'
                elif 'max' in context.lower():
                    suggested = 'MAX_VALUE'
                elif 'retry' in context.lower():
                    suggested = 'MAX_RETRIES'
                
                magic_values.append(MagicValue(
                    value_type='number',
                    value=num,
                    line=i,
                    code_snippet=stripped[:80],
                    context=context[:30] if context else 'unknown',
                    suggested_name=suggested
                ))
            
            # Magic URLs (hardcoded endpoints)
            for match in url_pattern.finditer(stripped):
                url = match.group(0)
                if 'localhost' not in url and 'example.com' not in url:
                    magic_values.append(MagicValue(
                        value_type='string',
                        value=url[:50],
                        line=i,
                        code_snippet=stripped[:80],
                        context='hardcoded_url',
                        suggested_name='API_ENDPOINT or BASE_URL'
                    ))
            
            # Magic paths
            for match in path_pattern.finditer(stripped):
                path = match.group(0)
                if not any(x in path.lower() for x in ['node_modules', 'test', 'mock', 'fixture']):
                    magic_values.append(MagicValue(
                        value_type='string',
                        value=path[:50],
                        line=i,
                        code_snippet=stripped[:80],
                        context='hardcoded_path',
                        suggested_name='FILE_PATH or CONFIG_PATH'
                    ))
        
        return magic_values[:30]  # Limit results
    
    # =========================================================================
    # ERROR HANDLING ANALYSIS
    # =========================================================================
    
    def _analyze_error_handling(self, root: Node, code: bytes, lines: List[str], language: str) -> List[ErrorHandlingIssue]:
        """Analyze quality of error handling"""
        issues = []
        
        def analyze_node(node: Node):
            # Try-catch/except blocks
            if node.type in {'try_statement', 'try_expression'}:
                has_handler = False
                has_finally = False
                
                for child in node.children:
                    if child.type in {'except_clause', 'catch_clause'}:
                        has_handler = True
                        handler_text = self._get_node_text(child, code)
                        line = child.start_point[0] + 1
                        snippet = self._get_line_text(lines, line)
                        
                        # Check for bare except
                        if child.type == 'except_clause':
                            # Python bare except: just "except:"
                            if re.search(r'except\s*:', handler_text) and 'Exception' not in handler_text:
                                issues.append(ErrorHandlingIssue(
                                    issue_type='broad_except',
                                    line=line,
                                    code_snippet=snippet,
                                    description='Bare except catches all exceptions including KeyboardInterrupt',
                                    suggestion='Catch specific exceptions: except ValueError: or except Exception:',
                                    severity='warning'
                                ))
                        
                        # Check for empty catch body
                        body = None
                        for c in child.children:
                            if c.type in {'block', 'statement_block'}:
                                body = c
                                break
                        
                        if body:
                            body_text = self._get_node_text(body, code).strip()
                            # Check if body is just pass or empty or just comment
                            if body_text in {'pass', '{}', ''} or (body_text.startswith('#') and '\n' not in body_text):
                                issues.append(ErrorHandlingIssue(
                                    issue_type='empty_catch',
                                    line=line,
                                    code_snippet=snippet,
                                    description='Empty catch block silently swallows exceptions',
                                    suggestion='Log the error or re-raise: except ValueError as e: logger.error(e)',
                                    severity='critical'
                                ))
                            
                            # Check for swallowed exception (no re-raise, no logging)
                            body_lower = body_text.lower()
                            if 'pass' in body_lower and 'log' not in body_lower and 'print' not in body_lower and 'raise' not in body_lower:
                                issues.append(ErrorHandlingIssue(
                                    issue_type='swallowed_exception',
                                    line=line,
                                    code_snippet=snippet,
                                    description='Exception caught but not logged or re-raised',
                                    suggestion='At minimum log the error: logger.exception("Error occurred")',
                                    severity='warning'
                                ))
                    
                    if child.type in {'finally_clause', 'finally'}:
                        has_finally = True
                
                # Check for try without handler
                if not has_handler:
                    line = node.start_point[0] + 1
                    issues.append(ErrorHandlingIssue(
                        issue_type='missing_catch',
                        line=line,
                        code_snippet=self._get_line_text(lines, line),
                        description='try block without exception handler',
                        suggestion='Add appropriate exception handling',
                        severity='warning'
                    ))
            
            # Check for unhandled promises (JS/TS)
            if language in {'javascript', 'typescript', 'tsx'}:
                if node.type == 'call_expression':
                    call_text = self._get_node_text(node, code)
                    if '.then(' in call_text and '.catch(' not in call_text:
                        # Check if parent handles it
                        parent = node.parent
                        if parent and parent.type not in {'await_expression', 'return_statement'}:
                            line = node.start_point[0] + 1
                            issues.append(ErrorHandlingIssue(
                                issue_type='unhandled_promise',
                                line=line,
                                code_snippet=self._get_line_text(lines, line)[:60],
                                description='Promise chain without .catch() handler',
                                suggestion='Add .catch(err => handleError(err)) or use try/await',
                                severity='warning'
                            ))
            
            for child in node.children:
                analyze_node(child)
        
        analyze_node(root)
        return issues
    
    # =========================================================================
    # NAMING CONVENTION ANALYSIS
    # =========================================================================
    
    def _analyze_naming(self, root: Node, code: bytes, lines: List[str], language: str) -> List[NamingIssue]:
        """Analyze naming convention consistency"""
        issues = []
        
        # Naming style patterns
        patterns = {
            'snake_case': re.compile(r'^[a-z][a-z0-9_]*$'),
            'camelCase': re.compile(r'^[a-z][a-zA-Z0-9]*$'),
            'PascalCase': re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
            'SCREAMING_SNAKE': re.compile(r'^[A-Z][A-Z0-9_]*$'),
        }
        
        # Language conventions
        conventions = {
            'python': {
                'function': 'snake_case',
                'variable': 'snake_case',
                'class': 'PascalCase',
                'constant': 'SCREAMING_SNAKE',
            },
            'javascript': {
                'function': 'camelCase',
                'variable': 'camelCase',
                'class': 'PascalCase',
                'constant': 'SCREAMING_SNAKE',
            },
            'typescript': {
                'function': 'camelCase',
                'variable': 'camelCase',
                'class': 'PascalCase',
                'constant': 'SCREAMING_SNAKE',
            },
            'tsx': {
                'function': 'camelCase',
                'variable': 'camelCase',
                'class': 'PascalCase',
                'constant': 'SCREAMING_SNAKE',
            },
            'java': {
                'function': 'camelCase',
                'variable': 'camelCase',
                'class': 'PascalCase',
                'constant': 'SCREAMING_SNAKE',
            },
        }
        
        lang_conv = conventions.get(language, conventions['python'])
        
        def detect_style(name: str) -> str:
            """Detect the naming style of an identifier"""
            for style, pattern in patterns.items():
                if pattern.match(name):
                    return style
            if '_' in name and name != name.lower() and name != name.upper():
                return 'mixed_case'
            return 'unknown'
        
        def check_naming(name: str, item_type: str, line: int):
            """Check if naming follows convention"""
            if len(name) < 2 or name.startswith('_'):
                return
            
            expected = lang_conv.get(item_type)
            if not expected:
                return
            
            actual = detect_style(name)
            
            if actual != expected and actual != 'unknown':
                # Generate suggestion
                if expected == 'snake_case':
                    # Convert to snake_case
                    suggested = re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')
                elif expected == 'camelCase':
                    # Convert to camelCase
                    parts = name.split('_')
                    suggested = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
                elif expected == 'PascalCase':
                    parts = name.split('_')
                    suggested = ''.join(p.capitalize() for p in parts)
                else:
                    suggested = name.upper().replace('-', '_')
                
                issues.append(NamingIssue(
                    issue_type='inconsistent_style',
                    name=name,
                    expected_style=expected,
                    actual_style=actual,
                    line=line,
                    item_type=item_type,
                    suggestion=f"Rename to '{suggested}' to follow {expected} convention"
                ))
            
            # Check for too short names (except i, j, k, x, y, z)
            if len(name) <= 2 and name not in {'i', 'j', 'k', 'x', 'y', 'z', 'id', 'db', 'io'}:
                issues.append(NamingIssue(
                    issue_type='too_short',
                    name=name,
                    expected_style='descriptive',
                    actual_style='abbreviation',
                    line=line,
                    item_type=item_type,
                    suggestion=f"Use a more descriptive name than '{name}'"
                ))
        
        def analyze_node(node: Node):
            # Functions
            if node.type in {'function_definition', 'function_declaration', 'method_definition'}:
                for child in node.children:
                    if child.type in {'identifier', 'property_identifier', 'name'}:
                        name = self._get_node_text(child, code)
                        if name and not name.startswith('__'):
                            check_naming(name, 'function', node.start_point[0] + 1)
                        break
            
            # Classes
            if node.type in {'class_definition', 'class_declaration'}:
                for child in node.children:
                    if child.type in {'identifier', 'type_identifier', 'name'}:
                        name = self._get_node_text(child, code)
                        if name:
                            check_naming(name, 'class', node.start_point[0] + 1)
                        break
            
            # Variables
            if node.type in {'assignment', 'variable_declaration', 'lexical_declaration'}:
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, code)
                        line = node.start_point[0] + 1
                        line_text = self._get_line_text(lines, line).upper()
                        
                        # Check if it's a constant (all caps value or const declaration)
                        if 'CONST ' in line_text or name.isupper():
                            check_naming(name, 'constant', line)
                        else:
                            check_naming(name, 'variable', line)
                        break
                    elif child.type == 'variable_declarator':
                        for c in child.children:
                            if c.type == 'identifier':
                                name = self._get_node_text(c, code)
                                check_naming(name, 'variable', node.start_point[0] + 1)
                                break
                        break
            
            for child in node.children:
                analyze_node(child)
        
        analyze_node(root)
        return issues[:20]  # Limit results
    
    # =========================================================================
    # NESTING DEPTH ANALYSIS
    # =========================================================================
    
    def _analyze_nesting(self, root: Node, code: bytes, lines: List[str], max_allowed: int = 4) -> List[NestingInfo]:
        """Analyze code nesting depth"""
        nesting_issues = []
        
        nesting_types = {
            'if_statement': 'if',
            'for_statement': 'for',
            'while_statement': 'while',
            'try_statement': 'try',
            'with_statement': 'with',
            'switch_statement': 'switch',
            'match_statement': 'match',
        }
        
        def analyze_function(func_node: Node, func_name: str):
            """Analyze nesting within a function"""
            max_depth = 0
            max_depth_line = func_node.start_point[0] + 1
            deepest_path = []
            
            def walk(node: Node, depth: int, path: List[str]):
                nonlocal max_depth, max_depth_line, deepest_path
                
                if node.type in nesting_types:
                    new_depth = depth + 1
                    new_path = path + [nesting_types[node.type]]
                    
                    if new_depth > max_depth:
                        max_depth = new_depth
                        max_depth_line = node.start_point[0] + 1
                        deepest_path = new_path.copy()
                    
                    for child in node.children:
                        walk(child, new_depth, new_path)
                else:
                    for child in node.children:
                        walk(child, depth, path)
            
            walk(func_node, 0, [])
            
            if max_depth > max_allowed:
                snippet = self._get_line_text(lines, max_depth_line)
                
                # Generate suggestion based on nesting pattern
                if len(deepest_path) >= 2 and deepest_path.count('if') >= 2:
                    suggestion = "Use early returns or guard clauses to reduce if nesting"
                elif 'for' in deepest_path and 'for' in deepest_path[deepest_path.index('for')+1:]:
                    suggestion = "Consider extracting nested loop to separate function"
                else:
                    suggestion = f"Extract deeply nested code (depth {max_depth}) to a separate function"
                
                nesting_issues.append(NestingInfo(
                    function_name=func_name,
                    line=max_depth_line,
                    max_depth=max_depth,
                    nesting_path=deepest_path,
                    code_snippet=snippet,
                    suggestion=suggestion
                ))
        
        # Find all functions and analyze nesting
        def find_functions(node: Node):
            if node.type in {'function_definition', 'function_declaration', 'method_definition', 'arrow_function'}:
                name = 'anonymous'
                for child in node.children:
                    if child.type in {'identifier', 'property_identifier', 'name'}:
                        name = self._get_node_text(child, code)
                        break
                analyze_function(node, name)
            
            for child in node.children:
                find_functions(child)
        
        find_functions(root)
        return nesting_issues
    
    # =========================================================================
    # DATA STRUCTURE DETECTION
    # =========================================================================
    
    def _detect_data_structures(self, code: str, lines: List[str], language: str) -> List[DataStructureUsage]:
        """Detect data structure usage with examples"""
        structures = []
        
        patterns = {
            'python': {
                'list': (r'(\w+)\s*=\s*\[', r'\[.*?\]'),
                'dict': (r'(\w+)\s*=\s*\{[^}]*:[^}]*\}', r'\{[^}]+\}'),
                'set': (r'(\w+)\s*=\s*set\s*\(|(\w+)\s*=\s*\{[^:}]+\}', r'set\s*\([^)]*\)'),
                'tuple': (r'(\w+)\s*=\s*\([^)]+,', r'\([^)]+,.*?\)'),
                'deque': (r'deque\s*\(', r'deque\s*\([^)]*\)'),
                'defaultdict': (r'defaultdict\s*\(', r'defaultdict\s*\([^)]*\)'),
                'Counter': (r'Counter\s*\(', r'Counter\s*\([^)]*\)'),
                'namedtuple': (r'namedtuple\s*\(', r'namedtuple\s*\([^)]*\)'),
            },
            'javascript': {
                'Array': (r'(\w+)\s*=\s*\[', r'\[.*?\]'),
                'Object': (r'(\w+)\s*=\s*\{', r'\{[^}]+\}'),
                'Map': (r'new\s+Map\s*\(', r'new\s+Map\s*\([^)]*\)'),
                'Set': (r'new\s+Set\s*\(', r'new\s+Set\s*\([^)]*\)'),
                'WeakMap': (r'new\s+WeakMap', r'new\s+WeakMap'),
                'WeakSet': (r'new\s+WeakSet', r'new\s+WeakSet'),
            },
            'typescript': {
                'Array': (r'(\w+)\s*[=:]\s*\[', r'\[.*?\]'),
                'Object': (r'(\w+)\s*[=:]\s*\{', r'\{[^}]+\}'),
                'Map': (r'new\s+Map\s*[<(]', r'new\s+Map'),
                'Set': (r'new\s+Set\s*[<(]', r'new\s+Set'),
                'Record': (r'Record\s*<', r'Record<[^>]+>'),
                'interface': (r'interface\s+\w+', r'interface\s+\w+'),
                'type': (r'^type\s+\w+\s*=', r'type\s+\w+'),
            },
        }
        
        lang_patterns = patterns.get(language, patterns.get('python', {}))
        
        for i, line in enumerate(lines, 1):
            for struct_type, (detect_pattern, example_pattern) in lang_patterns.items():
                if re.search(detect_pattern, line):
                    var_match = re.search(r'(\w+)\s*[=:]', line)
                    context = var_match.group(1) if var_match else 'inline'
                    
                    example_match = re.search(example_pattern, line)
                    example = example_match.group(0)[:60] if example_match else line.strip()[:60]
                    
                    structures.append(DataStructureUsage(
                        structure_type=struct_type,
                        line=i,
                        example=example,
                        context=context
                    ))
        
        return structures
    
    # =========================================================================
    # LINE COUNTING
    # =========================================================================
    
    def _count_lines(self, code: str, root: Node) -> Tuple[int, int, int, int]:
        """Count total, code, comment, and blank lines"""
        lines = code.split('\n')
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        
        comment_lines = set()
        comment_types = {'comment', 'line_comment', 'block_comment', 'documentation_comment'}
        
        def walk(node: Node):
            if node.type in comment_types:
                for ln in range(node.start_point[0], node.end_point[0] + 1):
                    comment_lines.add(ln)
            for child in node.children:
                walk(child)
        
        walk(root)
        comments = len(comment_lines)
        code_lines = total - blank - comments
        
        return total, max(0, code_lines), comments, blank
    
    # =========================================================================
    # MAIN ANALYSIS
    # =========================================================================
    
    def analyze_file(self, path: Path) -> FileResult:
        """Analyze a single file with rich insights"""
        start = time.time()
        result = FileResult(path=str(path))
        
        try:
            lang = self._detect_language(path)
            if not lang:
                result.error = f"Unsupported extension: {path.suffix}"
                return result
            
            result.language = lang
            result.size_bytes = path.stat().st_size
            
            if result.size_bytes / (1024 * 1024) > self.max_file_mb:
                result.error = f"File too large: {result.size_bytes / (1024*1024):.2f}MB"
                return result
            
            with open(path, 'rb') as f:
                code_bytes = f.read()
            
            code = code_bytes.decode('utf-8', errors='ignore')
            lines = code.split('\n')
            
            parser = self.parsers[lang]
            tree = parser.parse(code_bytes)
            root = tree.root_node
            
            # Build metrics
            metrics = Metrics()
            
            # Line counts
            metrics.total_lines, metrics.code_lines, metrics.comment_lines, metrics.blank_lines = \
                self._count_lines(code, root)
            
            # Dead code detection (also extracts functions)
            metrics.dead_code, metrics.functions = self._detect_dead_code(root, code_bytes, lines, lang)
            metrics.function_count = len(metrics.functions)
            
            # Build call graph
            metrics.call_graph = self._build_call_graph(metrics.functions)
            
            # Duplicate detection
            metrics.duplicates = self._detect_duplicates(lines, str(path))
            
            # Magic values
            metrics.magic_values = self._detect_magic_values(lines, lang)
            
            # Error handling analysis
            metrics.error_handling_issues = self._analyze_error_handling(root, code_bytes, lines, lang)
            
            # Naming convention analysis
            metrics.naming_issues = self._analyze_naming(root, code_bytes, lines, lang)
            
            # Nesting depth analysis
            metrics.nesting_issues = self._analyze_nesting(root, code_bytes, lines)
            
            # Data structure detection
            metrics.data_structures = self._detect_data_structures(code, lines, lang)
            
            result.metrics = metrics
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.exception(f"Error analyzing {path}")
        
        result.analysis_time_ms = (time.time() - start) * 1000
        return result
    
    def walk_directory(self, path: Path, depth: int = 0) -> List[Path]:
        """Recursively find analyzable files"""
        if depth >= self.max_depth:
            return []
        
        files = []
        supported_exts = set()
        for lang, config in SUPPORTED_LANGS.items():
            if lang in self.parsers:
                supported_exts.update(config['ext'])
        
        try:
            for item in path.iterdir():
                if item.is_file() and item.suffix.lower() in supported_exts:
                    files.append(item)
                elif item.is_dir() and item.name not in self.excluded_dirs:
                    files.extend(self.walk_directory(item, depth + 1))
        except PermissionError:
            pass
        
        return files
    
    def _detect_cross_file_duplicates(self) -> List[DuplicateBlock]:
        """Detect duplicate code across multiple files"""
        cross_file_dups = []
        
        for block_hash, locations in self._all_code_blocks.items():
            # Get unique files
            unique_files = set(loc[0] for loc in locations)
            
            if len(unique_files) >= 2:
                # This block appears in multiple files
                sample_file, sample_start, sample_end = locations[0]
                try:
                    with open(sample_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    sample = ''.join(lines[sample_start-1:sample_end])[:200]
                except:
                    sample = "[Could not read sample]"
                
                cross_file_dups.append(DuplicateBlock(
                    block_hash=block_hash,
                    locations=[(f, s, e) for f, s, e in locations],
                    line_count=sample_end - sample_start + 1,
                    sample_code=sample,
                    similarity=1.0
                ))
        
        return cross_file_dups[:20]
    
    def analyze_directory(self, path: Path, recursive: bool = True) -> DirectoryResult:
        """Analyze a directory with comprehensive insights"""
        logger.info(f"Analyzing: {path}")
        
        # Reset cross-file tracking
        self._all_code_blocks = {}
        self._all_function_defs = {}
        self._all_function_calls = {}
        
        result = DirectoryResult(path=str(path))
        
        if recursive:
            files = self.walk_directory(path)
        else:
            supported_exts = set()
            for config in SUPPORTED_LANGS.values():
                supported_exts.update(config['ext'])
            files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]
        
        logger.info(f"Found {len(files)} files")
        
        for file_path in files:
            file_result = self.analyze_file(file_path)
            result.files.append(file_result)
        
        # Cross-file duplicate detection
        result.cross_file_duplicates = self._detect_cross_file_duplicates()
        
        result.summary = self._build_summary(result)
        logger.info(f"Complete: {result.successful} analyzed, {result.failed} failed")
        
        return result
    
    def _build_summary(self, result: DirectoryResult) -> Dict:
        """Build comprehensive summary"""
        summary = {
            'total_files': len(result.files),
            'successful': result.successful,
            'failed': result.failed,
            'languages': defaultdict(int),
            'total_lines': 0,
            'total_code': 0,
            'total_comments': 0,
            'total_functions': 0,
            'total_classes': 0,
            
            # Analysis totals
            'dead_code': {
                'unused_functions': 0,
                'unused_imports': 0,
                'unused_variables': 0,
                'total': 0
            },
            'duplicates': {
                'within_file': 0,
                'cross_file': len(result.cross_file_duplicates),
                'total_duplicate_lines': 0
            },
            'call_graph_edges': 0,
            'magic_values': 0,
            'error_handling_issues': {
                'critical': 0,
                'warning': 0,
                'total': 0
            },
            'naming_issues': 0,
            'nesting_issues': 0,
            'data_structures': defaultdict(int),
            
            'avg_maintainability': 0.0,
        }
        
        maintainability_scores = []
        
        for f in result.files:
            if not f.success or not f.metrics:
                continue
            
            m = f.metrics
            summary['languages'][f.language] += 1
            summary['total_lines'] += m.total_lines
            summary['total_code'] += m.code_lines
            summary['total_comments'] += m.comment_lines
            summary['total_functions'] += m.function_count
            
            # Dead code
            for dc in m.dead_code:
                summary['dead_code']['total'] += 1
                if dc.item_type == 'function':
                    summary['dead_code']['unused_functions'] += 1
                elif dc.item_type == 'import':
                    summary['dead_code']['unused_imports'] += 1
                elif dc.item_type == 'variable':
                    summary['dead_code']['unused_variables'] += 1
            
            # Duplicates
            summary['duplicates']['within_file'] += len(m.duplicates)
            for dup in m.duplicates:
                summary['duplicates']['total_duplicate_lines'] += dup.line_count * (len(dup.locations) - 1)
            
            summary['call_graph_edges'] += len(m.call_graph)
            summary['magic_values'] += len(m.magic_values)
            
            for eh in m.error_handling_issues:
                summary['error_handling_issues']['total'] += 1
                if eh.severity == 'critical':
                    summary['error_handling_issues']['critical'] += 1
                else:
                    summary['error_handling_issues']['warning'] += 1
            
            summary['naming_issues'] += len(m.naming_issues)
            summary['nesting_issues'] += len(m.nesting_issues)
            
            for ds in m.data_structures:
                summary['data_structures'][ds.structure_type] += 1
            
            maintainability_scores.append(m.maintainability_score)
        
        if maintainability_scores:
            summary['avg_maintainability'] = sum(maintainability_scores) / len(maintainability_scores)
        
        # Convert for JSON
        summary['languages'] = dict(summary['languages'])
        summary['data_structures'] = dict(summary['data_structures'])
        
        return summary


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import json
    
    print(f"\n{'='*70}")
    print("ENHANCED CODE ANALYZER - Rich Insights")
    print('='*70)
    
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path(".")
    
    print(f"\n🔍 Target: {target_path.absolute()}")
    
    try:
        analyzer = CodeAnalyzer(
            max_file_mb=5.0,
            max_depth=10,
            excluded={'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist', '.next'}
        )
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    print(f"   Parsers: {', '.join(sorted(analyzer.parsers.keys()))}")
    
    result = analyzer.analyze_directory(target_path)
    s = result.summary
    
    print(f"\n📊 OVERVIEW")
    print(f"   Files: {s['successful']}/{s['total_files']} analyzed")
    print(f"   Lines: {s['total_lines']:,} ({s['total_code']:,} code, {s['total_comments']:,} comments)")
    print(f"   Functions: {s['total_functions']}")
    print(f"   Languages: {dict(s['languages'])}")
    
    print(f"\n💀 DEAD CODE ({s['dead_code']['total']} items)")
    print(f"   Unused functions: {s['dead_code']['unused_functions']}")
    print(f"   Unused imports: {s['dead_code']['unused_imports']}")
    dead_items = result.get_all_dead_code('high')[:5]
    for item in dead_items:
        print(f"   [{Path(item['file']).name}:{item['line']}] {item['type']}: {item['name']}")
        print(f"      {item['code_snippet'][:60]}")
    
    print(f"\n🔁 DUPLICATE CODE ({s['duplicates']['within_file']} blocks, ~{s['duplicates']['total_duplicate_lines']} duplicate lines)")
    for dup in result.get_all_duplicates()[:3]:
        locs = dup.get('locations', [])
        if len(locs) >= 2:
            print(f"   {dup['line_count']} lines appear {len(locs)} times")
            print(f"   Sample: {dup['sample_code'][:60]}...")
    
    print(f"\n📞 CALL GRAPH ({s['call_graph_edges']} edges)")
    cg = result.get_call_graph()
    for caller, callees in list(cg.items())[:5]:
        callee_names = [c['callee'] for c in callees[:3]]
        print(f"   {caller} → {', '.join(callee_names)}")
    
    print(f"\n🔢 MAGIC VALUES ({s['magic_values']} found)")
    for mv in result.get_all_magic_values()[:5]:
        print(f"   [{Path(mv['file']).name}:{mv['line']}] {mv['value']} → {mv['suggested_name']}")
        print(f"      {mv['code_snippet'][:50]}")
    
    print(f"\n🚨 ERROR HANDLING ({s['error_handling_issues']['total']} issues)")
    for eh in result.get_error_handling_issues('critical')[:3]:
        print(f"   [{Path(eh['file']).name}:{eh['line']}] {eh['type']}")
        print(f"      {eh['description']}")
        print(f"      → {eh['suggestion']}")
    
    print(f"\n📝 NAMING ISSUES ({s['naming_issues']} found)")
    for ni in result.get_naming_issues()[:5]:
        print(f"   [{Path(ni['file']).name}:{ni['line']}] {ni['name']}: {ni['actual_style']} → {ni['expected_style']}")
    
    print(f"\n🪆 DEEP NESTING ({s['nesting_issues']} functions)")
    for nest in result.get_nesting_issues()[:3]:
        print(f"   {nest['function']} (depth {nest['max_depth']}): {' → '.join(nest['nesting_path'])}")
        print(f"      → {nest['suggestion']}")
    
    if s['data_structures']:
        print(f"\n📦 DATA STRUCTURES")
        for ds_type, count in sorted(s['data_structures'].items(), key=lambda x: -x[1])[:8]:
            print(f"   {ds_type}: {count}")
    
    print(f"\n📈 MAINTAINABILITY: {s['avg_maintainability']:.1f}/100")
    print(f"\n{'='*70}\n")
