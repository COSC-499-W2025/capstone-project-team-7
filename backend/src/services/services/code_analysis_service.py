from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from scanner.models import FileMetadata, ParseResult, ScanPreferences

try:  # tree-sitter / parser extras are optional
    from local_analysis.code_parser import (
        CodeAnalyzer,
        DirectoryResult,
        EXCLUDED_DIRS,
    )
except Exception:  # pragma: no cover - optional dependency tree
    CodeAnalyzer = None  # type: ignore[assignment]
    DirectoryResult = Any  # type: ignore[assignment]
    EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "build", "dist"}


CODE_FILE_EXTENSIONS: Tuple[str, ...] = (
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".jsx",
)


class CodeAnalysisError(RuntimeError):
    """Base error for the code analysis helpers."""


class CodeAnalysisUnavailableError(CodeAnalysisError):
    """Raised when the local code analysis dependencies are missing."""


AnalyzerBuilder = Callable[..., Any]


class CodeAnalysisService:
    """Bridge between the backend API and the tree-sitter powered analyzer.
    
    Provides access to rich code analysis features:
    - Dead code detection
    - Duplicate code detection
    - Call graph analysis
    - Magic value detection
    - Error handling quality
    - Naming convention consistency
    - Nesting depth analysis
    - Data structure usage
    """

    def __init__(self, analyzer_builder: Optional[AnalyzerBuilder] = None) -> None:
        self._analyzer_builder = analyzer_builder

    # --- Detection helpers -------------------------------------------------

    def code_file_candidates(self, parse_result: Optional[ParseResult]) -> List[FileMetadata]:
        """Return files from the scan that look like source code."""
        if not parse_result:
            return []
        candidates: List[FileMetadata] = []
        for meta in parse_result.files:
            suffix = Path(meta.path).suffix.lower()
            if suffix in CODE_FILE_EXTENSIONS:
                candidates.append(meta)
        return candidates
    
    
    

    # --- Execution helpers -------------------------------------------------

    
    
    def run_analysis(
        self,
        target: Path,
        preferences: Optional[ScanPreferences] = None,
    ) -> DirectoryResult:
        """Analyze the provided directory and return the raw DirectoryResult."""
        analyzer = self._create_analyzer(preferences)
        try:
            return analyzer.analyze_directory(target)
        except CodeAnalysisError:
            raise
        except Exception as exc:  # pragma: no cover - analyzer specific failures
            raise CodeAnalysisError(f"Code analysis failed: {exc}") from exc

    def _create_analyzer(self, preferences: Optional[ScanPreferences]):
        analyzer_kwargs = self._build_analyzer_kwargs(preferences)
        builder = self._analyzer_builder
        if builder is None:
            if CodeAnalyzer is None:
                raise CodeAnalysisUnavailableError(
                    "Code analysis requires tree-sitter language bindings. "
                    "Install the optional dependencies listed in README.md."
                )
            builder = CodeAnalyzer
        try:
            return builder(**analyzer_kwargs)
        except ImportError as exc:  # pragma: no cover - missing deps bubble up
            raise CodeAnalysisUnavailableError(str(exc)) from exc
        except CodeAnalysisUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - builder specific failure
            raise CodeAnalysisError(f"Unable to initialize code analyzer: {exc}") from exc

    def _build_analyzer_kwargs(self, preferences: Optional[ScanPreferences]) -> Dict[str, Any]:
        max_file_mb = 5.0
        if preferences and preferences.max_file_size_bytes:
            max_file_mb = max(0.5, preferences.max_file_size_bytes / (1024 * 1024))

        excluded = set(EXCLUDED_DIRS)
        if preferences and preferences.excluded_dirs:
            excluded.update({entry for entry in preferences.excluded_dirs if entry})

        return {
            "max_file_mb": max_file_mb,
            "max_depth": 10,
            "excluded": excluded,
        }

    # --- Formatting helpers ------------------------------------------------

    def format_summary(self, result: DirectoryResult) -> str:
        """Return a multi-line string summarizing analyzer output."""
        summary = getattr(result, "summary", None) or {}
        lines: List[str] = []
        lines.append("[b]Code Analysis[/b]")
        lines.append("")
        
        # Overview section
        lines.append("[b]📊 Overview[/b]")
        lines.append(f"Target: {getattr(result, 'path', 'unknown')}")

        total_files = summary.get("total_files", len(getattr(result, "files", [])))
        successful = summary.get("successful", 0)
        failed = summary.get("failed", max(total_files - successful, 0))
        lines.append(f"Files analyzed: {successful}/{total_files} (failed: {failed})")
        lines.append(f"Total lines: {summary.get('total_lines', 0):,} ({summary.get('total_code', 0):,} code, {summary.get('total_comments', 0):,} comments)")
        lines.append(f"Functions: {summary.get('total_functions', 0)}")

        # Languages
        languages = summary.get("languages", {})
        if languages:
            lang_str = ", ".join(f"{lang}: {count}" for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:5])
            lines.append(f"Languages: {lang_str}")

        # Maintainability
        maintainability = summary.get("avg_maintainability")
        if maintainability is not None:
            lines.append("")
            lines.append(f"[b]📈 Maintainability: {maintainability:.1f}/100[/b] {self._quality_label(maintainability)}")

        # Dead Code section
        dead_code = summary.get("dead_code", {})
        dead_total = dead_code.get("total", 0)
        if dead_total > 0:
            lines.append("")
            lines.append(f"[b]💀 Dead Code ({dead_total} items)[/b]")
            lines.append(f"• Unused functions: {dead_code.get('unused_functions', 0)}")
            lines.append(f"• Unused imports: {dead_code.get('unused_imports', 0)}")
            lines.append(f"• Unused variables: {dead_code.get('unused_variables', 0)}")
            
            # Show examples
            dead_items = self._get_dead_code_examples(result)
            for item in dead_items[:3]:
                lines.append(f"  → {item}")

        # Duplicate Code section
        duplicates = summary.get("duplicates", {})
        dup_total = duplicates.get("within_file", 0) + duplicates.get("cross_file", 0)
        if dup_total > 0:
            lines.append("")
            lines.append(f"[b]🔁 Duplicate Code ({dup_total} blocks)[/b]")
            lines.append(f"• Within-file: {duplicates.get('within_file', 0)} blocks")
            lines.append(f"• Cross-file: {duplicates.get('cross_file', 0)} blocks")
            lines.append(f"• Duplicate lines: ~{duplicates.get('total_duplicate_lines', 0)}")

        # Call Graph section
        call_graph_edges = summary.get("call_graph_edges", 0)
        if call_graph_edges > 0:
            lines.append("")
            lines.append(f"[b]📞 Call Graph ({call_graph_edges} relationships)[/b]")
            call_examples = self._get_call_graph_examples(result)
            for ex in call_examples[:3]:
                lines.append(f"  {ex}")

        # Magic Values section
        magic_count = summary.get("magic_values", 0)
        if magic_count > 0:
            lines.append("")
            lines.append(f"[b]🔢 Magic Values ({magic_count} found)[/b]")
            magic_examples = self._get_magic_value_examples(result)
            for ex in magic_examples[:4]:
                lines.append(f"  {ex}")

        # Error Handling section
        error_handling = summary.get("error_handling_issues", {})
        error_total = error_handling.get("total", 0)
        if error_total > 0:
            lines.append("")
            lines.append(f"[b]🚨 Error Handling Issues ({error_total})[/b]")
            lines.append(f"• Critical: {error_handling.get('critical', 0)}")
            lines.append(f"• Warnings: {error_handling.get('warning', 0)}")
            error_examples = self._get_error_handling_examples(result)
            for ex in error_examples[:3]:
                lines.append(f"  → {ex}")

        # Naming Issues section
        naming_count = summary.get("naming_issues", 0)
        if naming_count > 0:
            lines.append("")
            lines.append(f"[b]📝 Naming Issues ({naming_count})[/b]")
            naming_examples = self._get_naming_examples(result)
            for ex in naming_examples[:3]:
                lines.append(f"  {ex}")

        # Nesting Issues section
        nesting_count = summary.get("nesting_issues", 0)
        if nesting_count > 0:
            lines.append("")
            lines.append(f"[b]🪆 Deep Nesting ({nesting_count} functions)[/b]")
            nesting_examples = self._get_nesting_examples(result)
            for ex in nesting_examples[:3]:
                lines.append(f"  {ex}")

        # Data Structures section
        data_structures = summary.get("data_structures", {})
        if data_structures:
            lines.append("")
            lines.append("[b]📦 Data Structures[/b]")
            ds_sorted = sorted(data_structures.items(), key=lambda x: -x[1])[:6]
            ds_str = ", ".join(f"{ds}: {count}" for ds, count in ds_sorted)
            lines.append(f"  {ds_str}")

        return "\n".join(lines).strip()

    # --- Example extraction helpers ----------------------------------------

    def _get_dead_code_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted dead code examples."""
        examples = []
        getter = getattr(result, "get_all_dead_code", None)
        if not callable(getter):
            return examples
        
        for item in getter("high")[:5]:
            name = Path(item.get("file", "unknown")).name
            line = item.get("line", 0)
            item_type = item.get("type", "item")
            item_name = item.get("name", "unknown")
            examples.append(f"[{name}:{line}] {item_type}: {item_name}")
        
        return examples

    def _get_call_graph_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted call graph examples."""
        examples = []
        getter = getattr(result, "get_call_graph", None)
        if not callable(getter):
            return examples
        
        call_graph = getter()
        for caller, callees in list(call_graph.items())[:5]:
            callee_names = list(set(c["callee"] for c in callees))[:3]
            examples.append(f"{caller} → {', '.join(callee_names)}")
        
        return examples

    def _get_magic_value_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted magic value examples."""
        examples = []
        getter = getattr(result, "get_all_magic_values", None)
        if not callable(getter):
            return examples
        
        for item in getter()[:6]:
            name = Path(item.get("file", "unknown")).name
            line = item.get("line", 0)
            value = item.get("value", "")[:20]
            suggested = item.get("suggested_name", "CONSTANT")
            examples.append(f"[{name}:{line}] {value} → {suggested}")
        
        return examples

    def _get_error_handling_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted error handling issue examples."""
        examples = []
        getter = getattr(result, "get_error_handling_issues", None)
        if not callable(getter):
            return examples
        
        for item in getter("critical")[:5]:
            name = Path(item.get("file", "unknown")).name
            line = item.get("line", 0)
            issue_type = item.get("type", "issue").replace("_", " ")
            examples.append(f"[{name}:{line}] {issue_type}")
        
        return examples

    def _get_naming_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted naming issue examples."""
        examples = []
        getter = getattr(result, "get_naming_issues", None)
        if not callable(getter):
            return examples
        
        for item in getter()[:5]:
            name = Path(item.get("file", "unknown")).name
            line = item.get("line", 0)
            item_name = item.get("name", "")
            expected = item.get("expected_style", "")
            examples.append(f"[{name}:{line}] '{item_name}' → {expected}")
        
        return examples

    def _get_nesting_examples(self, result: DirectoryResult) -> List[str]:
        """Get formatted nesting issue examples."""
        examples = []
        getter = getattr(result, "get_nesting_issues", None)
        if not callable(getter):
            return examples
        
        for item in getter()[:5]:
            func_name = item.get("function", "unknown")
            depth = item.get("max_depth", 0)
            path = " → ".join(item.get("nesting_path", [])[:4])
            examples.append(f"{func_name} (depth {depth}): {path}")
        
        return examples

    # --- Detailed section formatters ---------------------------------------

    def format_dead_code_section(self, result: DirectoryResult) -> str:
        """Format detailed dead code section."""
        lines = ["[b]💀 Dead Code Analysis[/b]", ""]
        
        getter = getattr(result, "get_all_dead_code", None)
        if not callable(getter):
            lines.append("Dead code detection not available")
            return "\n".join(lines)
        
        items = getter()
        if not items:
            lines.append("No dead code detected! ✅")
            return "\n".join(lines)
        
        # Group by confidence
        high_conf = [i for i in items if i.get("confidence") == "high"]
        med_conf = [i for i in items if i.get("confidence") == "medium"]
        
        if high_conf:
            lines.append("[b]High Confidence (definitely unused in this file)[/b]")
            for item in high_conf[:10]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('type', '')}: {item.get('name', '')}")
                lines.append(f"  Code: {item.get('code_snippet', '')[:60]}")
                lines.append(f"  Reason: {item.get('reason', '')}")
                lines.append("")
        
        if med_conf:
            lines.append("[b]Medium Confidence (may be used externally)[/b]")
            for item in med_conf[:8]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('type', '')}: {item.get('name', '')}")
        
        return "\n".join(lines)

    def format_duplicates_section(self, result: DirectoryResult) -> str:
        """Format detailed duplicate code section."""
        lines = ["[b]🔁 Duplicate Code Analysis[/b]", ""]
        
        getter = getattr(result, "get_all_duplicates", None)
        if not callable(getter):
            lines.append("Duplicate detection not available")
            return "\n".join(lines)
        
        duplicates = getter()
        if not duplicates:
            lines.append("No duplicate code detected! ✅")
            return "\n".join(lines)
        
        for i, dup in enumerate(duplicates[:8], 1):
            locs = dup.get("locations", [])
            is_cross = dup.get("cross_file", False)
            
            lines.append(f"[b]{i}. {'Cross-file ' if is_cross else ''}{dup.get('line_count', 0)} lines × {len(locs)} occurrences[/b]")
            
            for loc in locs[:4]:
                file_name = Path(loc.get("file", "unknown")).name
                lines.append(f"   • {file_name}: lines {loc.get('start', 0)}-{loc.get('end', 0)}")
            
            sample = dup.get("sample_code", "")[:80]
            if sample:
                lines.append(f"   Sample: {sample.split(chr(10))[0]}")
            
            lines.append("   → Extract to shared function/module")
            lines.append("")
        
        return "\n".join(lines)

    def format_call_graph_section(self, result: DirectoryResult) -> str:
        """Format detailed call graph section."""
        lines = ["[b]📞 Call Graph Analysis[/b]", ""]
        
        getter = getattr(result, "get_call_graph", None)
        if not callable(getter):
            lines.append("Call graph analysis not available")
            return "\n".join(lines)
        
        call_graph = getter()
        if not call_graph:
            lines.append("No internal function calls detected")
            return "\n".join(lines)
        
        # Find most called functions
        callee_counts: Dict[str, int] = {}
        for caller, callees in call_graph.items():
            for c in callees:
                callee_counts[c["callee"]] = callee_counts.get(c["callee"], 0) + 1
        
        if callee_counts:
            lines.append("[b]Most Called Functions[/b]")
            for callee, count in sorted(callee_counts.items(), key=lambda x: -x[1])[:8]:
                lines.append(f"  • {callee}: called {count} times")
            lines.append("")
        
        lines.append("[b]Call Relationships[/b]")
        for caller, callees in list(call_graph.items())[:12]:
            callee_names = list(set(c["callee"] for c in callees))[:5]
            lines.append(f"  {caller} → {', '.join(callee_names)}")
        
        return "\n".join(lines)

    def format_magic_values_section(self, result: DirectoryResult) -> str:
        """Format detailed magic values section."""
        lines = ["[b]🔢 Magic Values Analysis[/b]", ""]
        
        getter = getattr(result, "get_all_magic_values", None)
        if not callable(getter):
            lines.append("Magic value detection not available")
            return "\n".join(lines)
        
        items = getter()
        if not items:
            lines.append("No magic values detected! ✅")
            return "\n".join(lines)
        
        # Group by type
        numbers = [i for i in items if i.get("type") == "number"]
        strings = [i for i in items if i.get("type") == "string"]
        
        if numbers:
            lines.append("[b]Magic Numbers[/b]")
            for item in numbers[:10]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('value', '')}")
                lines.append(f"  Code: {item.get('code_snippet', '')[:50]}")
                lines.append(f"  → Extract as: {item.get('suggested_name', 'CONSTANT')}")
                lines.append("")
        
        if strings:
            lines.append("[b]Hardcoded Strings/URLs[/b]")
            for item in strings[:8]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('value', '')[:40]}")
                lines.append(f"  → Extract as: {item.get('suggested_name', 'CONSTANT')}")
                lines.append("")
        
        return "\n".join(lines)

    def format_error_handling_section(self, result: DirectoryResult) -> str:
        """Format detailed error handling section."""
        lines = ["[b]🚨 Error Handling Analysis[/b]", ""]
        
        getter = getattr(result, "get_error_handling_issues", None)
        if not callable(getter):
            lines.append("Error handling analysis not available")
            return "\n".join(lines)
        
        items = getter()
        if not items:
            lines.append("No error handling issues detected! ✅")
            return "\n".join(lines)
        
        critical = [i for i in items if i.get("severity") == "critical"]
        warnings = [i for i in items if i.get("severity") == "warning"]
        
        if critical:
            lines.append("[b]Critical Issues[/b]")
            for item in critical[:8]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('type', '').replace('_', ' ').upper()}")
                lines.append(f"  Code: {item.get('code_snippet', '')[:50]}")
                lines.append(f"  Problem: {item.get('description', '')}")
                lines.append(f"  → Fix: {item.get('suggestion', '')}")
                lines.append("")
        
        if warnings:
            lines.append("[b]Warnings[/b]")
            for item in warnings[:6]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('type', '')}: {item.get('description', '')[:40]}")
        
        return "\n".join(lines)

    def format_naming_section(self, result: DirectoryResult) -> str:
        """Format detailed naming conventions section."""
        lines = ["[b]📝 Naming Convention Analysis[/b]", ""]
        
        getter = getattr(result, "get_naming_issues", None)
        if not callable(getter):
            lines.append("Naming analysis not available")
            return "\n".join(lines)
        
        items = getter()
        if not items:
            lines.append("No naming issues detected! ✅")
            return "\n".join(lines)
        
        # Group by type
        style_issues = [i for i in items if i.get("type") == "inconsistent_style"]
        short_issues = [i for i in items if i.get("type") == "too_short"]
        
        if style_issues:
            lines.append("[b]Inconsistent Naming Styles[/b]")
            for item in style_issues[:10]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] {item.get('item_type', '')} '{item.get('name', '')}'")
                lines.append(f"  Current: {item.get('actual_style', '')} → Expected: {item.get('expected_style', '')}")
                lines.append(f"  {item.get('suggestion', '')}")
                lines.append("")
        
        if short_issues:
            lines.append("[b]Names Too Short[/b]")
            for item in short_issues[:6]:
                name = Path(item.get("file", "unknown")).name
                lines.append(f"• [{name}:{item.get('line', 0)}] '{item.get('name', '')}' - {item.get('suggestion', '')}")
        
        return "\n".join(lines)

    def format_nesting_section(self, result: DirectoryResult) -> str:
        """Format detailed nesting depth section."""
        lines = ["[b]🪆 Deep Nesting Analysis[/b]", ""]
        
        getter = getattr(result, "get_nesting_issues", None)
        if not callable(getter):
            lines.append("Nesting analysis not available")
            return "\n".join(lines)
        
        items = getter()
        if not items:
            lines.append("No deep nesting issues detected! ✅")
            return "\n".join(lines)
        
        for item in items[:10]:
            name = Path(item.get("file", "unknown")).name
            func_name = item.get("function", "unknown")
            depth = item.get("max_depth", 0)
            path = " → ".join(item.get("nesting_path", []))
            
            lines.append(f"[b]{func_name}[/b] ({name}:{item.get('line', 0)})")
            lines.append(f"  Max depth: {depth} levels")
            lines.append(f"  Path: {path}")
            lines.append(f"  → {item.get('suggestion', 'Reduce nesting')}")
            lines.append("")
        
        return "\n".join(lines)

    def format_data_structures_section(self, result: DirectoryResult) -> str:
        """Format detailed data structures section."""
        lines = ["[b]📦 Data Structures Used[/b]", ""]
        
        summary = getattr(result, "summary", None) or {}
        data_structures = summary.get("data_structures", {})
        
        if not data_structures:
            lines.append("No data structures detected")
            return "\n".join(lines)
        
        lines.append("[b]Usage Counts[/b]")
        for ds_type, count in sorted(data_structures.items(), key=lambda x: -x[1]):
            lines.append(f"  • {ds_type}: {count}")
        
        # Get examples
        getter = getattr(result, "get_data_structure_summary", None)
        if callable(getter):
            examples = getter()
            if examples:
                lines.append("")
                lines.append("[b]Examples[/b]")
                for ds_type, items in list(examples.items())[:5]:
                    if items:
                        lines.append(f"  {ds_type}:")
                        for ex in items[:2]:
                            lines.append(f"    [{ex.get('file', '')}:{ex.get('line', 0)}] {ex.get('context', '')} = {ex.get('example', '')[:40]}")
        
        return "\n".join(lines)

    @staticmethod
    def _quality_label(score: float) -> str:
        if score >= 80:
            return "[green]excellent[/green]"
        if score >= 70:
            return "[green]good[/green]"
        if score >= 60:
            return "[yellow]fair[/yellow]"
        if score >= 50:
            return "[#f97316]needs work[/#f97316]"
        return "[red]critical[/red]"
