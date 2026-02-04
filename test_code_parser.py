#!/usr/bin/env python3
"""
Test script for Enhanced Code Parser
Demonstrates rich, actionable insights:
- Dead code detection
- Duplicate code detection
- Call graph analysis
- Magic numbers/strings
- Error handling quality
- Naming convention consistency
- Nesting depth analysis
- Data structure usage
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import importlib.util

# Direct import to avoid __init__.py issues
def load_code_parser():
    parser_path = Path(__file__).parent / "backend" / "src" / "local_analysis" / "code_parser.py"
    spec = importlib.util.spec_from_file_location("code_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

try:
    code_parser = load_code_parser()
    CodeAnalyzer = code_parser.CodeAnalyzer
    DirectoryResult = code_parser.DirectoryResult
except Exception as e:
    print(f"❌ Error importing code_parser: {e}")
    print("\nMake sure tree-sitter dependencies are installed:")
    print("  pip install tree-sitter")
    print("  pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
    sys.exit(1)


def print_banner(text: str):
    print(f"\n{'='*80}")
    print(f"  {text}")
    print('='*80)


def print_section(title: str):
    print(f"\n{title}")
    print('-' * len(title))


def print_detailed_results(result: DirectoryResult):
    """Print comprehensive analysis with code examples"""
    print_banner("ENHANCED CODE ANALYSIS RESULTS")
    
    s = result.summary
    
    # =========================================================================
    # OVERVIEW
    # =========================================================================
    print_section("📊 OVERVIEW")
    print(f"  Target: {result.path}")
    print(f"  Files analyzed: {s['successful']}/{s['total_files']} ({s['failed']} failed)")
    print(f"  Total lines: {s['total_lines']:,} ({s['total_code']:,} code, {s['total_comments']:,} comments)")
    print(f"  Functions: {s['total_functions']}")
    
    if s.get('languages'):
        print(f"\n  Languages:")
        for lang, count in sorted(s['languages'].items(), key=lambda x: -x[1]):
            print(f"    • {lang}: {count} files")
    
    # =========================================================================
    # DEAD CODE
    # =========================================================================
    print_section(f"💀 DEAD CODE ({s['dead_code']['total']} items found)")
    print(f"  Unused functions: {s['dead_code']['unused_functions']}")
    print(f"  Unused imports: {s['dead_code']['unused_imports']}")
    print(f"  Unused variables: {s['dead_code']['unused_variables']}")
    
    dead_items = result.get_all_dead_code()
    high_conf = [d for d in dead_items if d['confidence'] == 'high'][:8]
    if high_conf:
        print(f"\n  High confidence unused items:")
        for item in high_conf:
            file_name = Path(item['file']).name
            print(f"\n    [{file_name}:{item['line']}] {item['type'].upper()}: {item['name']}")
            print(f"    Code: {item['code_snippet'][:70]}")
            print(f"    Reason: {item['reason']}")
    
    med_conf = [d for d in dead_items if d['confidence'] == 'medium'][:5]
    if med_conf:
        print(f"\n  Medium confidence (may be used externally):")
        for item in med_conf:
            file_name = Path(item['file']).name
            print(f"    [{file_name}:{item['line']}] {item['type']}: {item['name']}")
    
    # =========================================================================
    # DUPLICATE CODE
    # =========================================================================
    total_dups = s['duplicates']['within_file'] + s['duplicates']['cross_file']
    print_section(f"🔁 DUPLICATE CODE ({total_dups} blocks, ~{s['duplicates']['total_duplicate_lines']} duplicate lines)")
    
    all_dups = result.get_all_duplicates()
    for i, dup in enumerate(all_dups[:5], 1):
        locs = dup.get('locations', [])
        is_cross = dup.get('cross_file', False)
        
        print(f"\n  {i}. {'CROSS-FILE: ' if is_cross else ''}{dup['line_count']} lines × {len(locs)} occurrences")
        print(f"     Locations:")
        for loc in locs[:4]:
            file_name = Path(loc['file']).name if isinstance(loc.get('file'), str) else loc.get('file', 'unknown')
            print(f"       • {file_name}: lines {loc['start']}-{loc['end']}")
        
        sample = dup.get('sample_code', '')[:100]
        if sample:
            print(f"     Sample:")
            for line in sample.split('\n')[:3]:
                print(f"       {line.strip()}")
        print(f"     → Suggestion: Extract to shared function/module")
    
    # =========================================================================
    # CALL GRAPH
    # =========================================================================
    print_section(f"📞 CALL GRAPH ({s['call_graph_edges']} relationships)")
    
    call_graph = result.get_call_graph()
    
    # Find most called functions
    callee_counts = {}
    for caller, callees in call_graph.items():
        for c in callees:
            callee_counts[c['callee']] = callee_counts.get(c['callee'], 0) + 1
    
    if callee_counts:
        print(f"\n  Most called functions:")
        for callee, count in sorted(callee_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"    • {callee}: called {count} times")
    
    print(f"\n  Call relationships:")
    for caller, callees in list(call_graph.items())[:8]:
        callee_names = list(set(c['callee'] for c in callees))[:5]
        print(f"    {caller} → {', '.join(callee_names)}")
    
    # =========================================================================
    # MAGIC VALUES
    # =========================================================================
    print_section(f"🔢 MAGIC VALUES ({s['magic_values']} found)")
    
    magic_vals = result.get_all_magic_values()
    numbers = [m for m in magic_vals if m['type'] == 'number'][:6]
    strings = [m for m in magic_vals if m['type'] == 'string'][:4]
    
    if numbers:
        print(f"\n  Magic numbers:")
        for mv in numbers:
            file_name = Path(mv['file']).name
            print(f"\n    [{file_name}:{mv['line']}] {mv['value']}")
            print(f"    Code: {mv['code_snippet'][:60]}")
            print(f"    → Extract as: {mv['suggested_name']}")
    
    if strings:
        print(f"\n  Hardcoded strings/URLs:")
        for mv in strings:
            file_name = Path(mv['file']).name
            print(f"\n    [{file_name}:{mv['line']}] {mv['value'][:40]}")
            print(f"    → Extract as: {mv['suggested_name']}")
    
    # =========================================================================
    # ERROR HANDLING
    # =========================================================================
    print_section(f"🚨 ERROR HANDLING ISSUES ({s['error_handling_issues']['total']} found)")
    print(f"  Critical: {s['error_handling_issues']['critical']}")
    print(f"  Warnings: {s['error_handling_issues']['warning']}")
    
    critical_issues = result.get_error_handling_issues('critical')[:5]
    if critical_issues:
        print(f"\n  Critical issues:")
        for issue in critical_issues:
            file_name = Path(issue['file']).name
            print(f"\n    [{file_name}:{issue['line']}] {issue['type'].replace('_', ' ').upper()}")
            print(f"    Code: {issue['code_snippet'][:60]}")
            print(f"    Problem: {issue['description']}")
            print(f"    → Fix: {issue['suggestion']}")
    
    warning_issues = result.get_error_handling_issues('warning')[:3]
    if warning_issues:
        print(f"\n  Warnings:")
        for issue in warning_issues:
            file_name = Path(issue['file']).name
            print(f"    [{file_name}:{issue['line']}] {issue['type']}: {issue['description'][:50]}")
    
    # =========================================================================
    # NAMING CONVENTIONS
    # =========================================================================
    print_section(f"📝 NAMING CONVENTION ISSUES ({s['naming_issues']} found)")
    
    naming_issues = result.get_naming_issues()
    
    # Group by type
    style_issues = [n for n in naming_issues if n['type'] == 'inconsistent_style'][:6]
    short_issues = [n for n in naming_issues if n['type'] == 'too_short'][:4]
    
    if style_issues:
        print(f"\n  Inconsistent naming styles:")
        for ni in style_issues:
            file_name = Path(ni['file']).name
            print(f"    [{file_name}:{ni['line']}] {ni['item_type']} '{ni['name']}'")
            print(f"      Current: {ni['actual_style']} → Expected: {ni['expected_style']}")
            print(f"      {ni['suggestion']}")
    
    if short_issues:
        print(f"\n  Names too short:")
        for ni in short_issues:
            file_name = Path(ni['file']).name
            print(f"    [{file_name}:{ni['line']}] {ni['item_type']} '{ni['name']}' - {ni['suggestion']}")
    
    # =========================================================================
    # NESTING DEPTH
    # =========================================================================
    print_section(f"🪆 DEEP NESTING ({s['nesting_issues']} functions exceed threshold)")
    
    nesting_issues = result.get_nesting_issues()[:6]
    for nest in nesting_issues:
        file_name = Path(nest['file']).name
        path_str = ' → '.join(nest['nesting_path'])
        
        print(f"\n  {nest['function']} ({file_name}:{nest['line']})")
        print(f"    Max depth: {nest['max_depth']} levels")
        print(f"    Path: {path_str}")
        print(f"    Code: {nest['code_snippet'][:50]}")
        print(f"    → {nest['suggestion']}")
    
    # =========================================================================
    # DATA STRUCTURES
    # =========================================================================
    print_section("📦 DATA STRUCTURES USED")
    
    if s['data_structures']:
        print(f"\n  Usage counts:")
        for ds_type, count in sorted(s['data_structures'].items(), key=lambda x: -x[1]):
            print(f"    • {ds_type}: {count}")
    
    ds_summary = result.get_data_structure_summary()
    if ds_summary:
        print(f"\n  Examples:")
        for ds_type, examples in list(ds_summary.items())[:4]:
            if examples:
                print(f"\n    {ds_type}:")
                for ex in examples[:2]:
                    print(f"      [{ex['file']}:{ex['line']}] {ex['context']} = {ex['example'][:45]}")
    
    # =========================================================================
    # QUALITY SUMMARY
    # =========================================================================
    print_section("📈 QUALITY SUMMARY")
    print(f"  Average maintainability: {s.get('avg_maintainability', 0):.1f}/100")
    print(f"\n  Issue breakdown:")
    print(f"    • Dead code items: {s['dead_code']['total']}")
    print(f"    • Duplicate code blocks: {total_dups}")
    print(f"    • Magic values: {s['magic_values']}")
    print(f"    • Error handling issues: {s['error_handling_issues']['total']}")
    print(f"    • Naming issues: {s['naming_issues']}")
    print(f"    • Deep nesting: {s['nesting_issues']}")


def print_compact_results(result: DirectoryResult):
    """Print compact summary"""
    print_banner("CODE ANALYSIS SUMMARY")
    
    s = result.summary
    
    print(f"\n📂 {result.path}")
    print(f"📊 {s['successful']}/{s['total_files']} files | {s['total_lines']:,} lines | {s['total_functions']} functions")
    print(f"   Languages: {dict(s['languages'])}")
    
    print(f"\n💀 Dead Code: {s['dead_code']['total']} items")
    print(f"   {s['dead_code']['unused_functions']} unused functions, {s['dead_code']['unused_imports']} unused imports")
    
    print(f"\n🔁 Duplicates: {s['duplicates']['within_file']} blocks (~{s['duplicates']['total_duplicate_lines']} lines)")
    
    print(f"\n🔢 Magic Values: {s['magic_values']}")
    
    print(f"\n🚨 Error Handling: {s['error_handling_issues']['critical']} critical, {s['error_handling_issues']['warning']} warnings")
    
    print(f"\n📝 Naming Issues: {s['naming_issues']}")
    
    print(f"\n🪆 Deep Nesting: {s['nesting_issues']} functions")
    
    print(f"\n📈 Maintainability: {s.get('avg_maintainability', 0):.1f}/100")
    
    # Top issues
    print(f"\n🔴 Top Issues:")
    
    dead = result.get_all_dead_code('high')[:2]
    for d in dead:
        print(f"   Dead: {d['type']} '{d['name']}' never used [{Path(d['file']).name}:{d['line']}]")
    
    errors = result.get_error_handling_issues('critical')[:2]
    for e in errors:
        print(f"   Error handling: {e['type']} [{Path(e['file']).name}:{e['line']}]")
    
    nesting = result.get_nesting_issues()[:2]
    for n in nesting:
        print(f"   Nesting: {n['function']} has depth {n['max_depth']}")


def save_json_results(result: DirectoryResult, output_path: Path):
    """Save comprehensive JSON results using DirectoryResult.to_dict()"""
    data = {
        'timestamp': datetime.now().isoformat(),
        **result.to_dict()  # Use the new to_dict() method
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enhanced Code Parser - Rich Actionable Insights',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Features:
  • Dead code detection (unused functions, imports, variables)
  • Duplicate/similar code detection with examples
  • Call graph analysis (what calls what)
  • Magic numbers/strings detection with suggested names
  • Error handling quality analysis
  • Naming convention consistency checking
  • Deep nesting detection with refactor suggestions
  • Data structure usage tracking

Examples:
  python test_code_parser.py                              # Analyze default directory
  python test_code_parser.py ./backend/src                # Analyze specific directory  
  python test_code_parser.py ./project --detailed         # Full detailed output
  python test_code_parser.py ./project --json out.json    # Save to JSON
  python test_code_parser.py ./project --dead-code        # Show only dead code
  python test_code_parser.py ./project --duplicates       # Show only duplicates
  python test_code_parser.py ./project --errors           # Show only error handling
        """
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default=r'C:\Users\Aaron\OneDrive\Desktop\ai-interview-assistant',
        help='Directory to analyze'
    )
    parser.add_argument('--detailed', action='store_true', help='Show detailed output')
    parser.add_argument('--json', metavar='FILE', help='Save results to JSON file')
    parser.add_argument('--dead-code', action='store_true', help='Show only dead code')
    parser.add_argument('--duplicates', action='store_true', help='Show only duplicates')
    parser.add_argument('--call-graph', action='store_true', help='Show only call graph')
    parser.add_argument('--magic', action='store_true', help='Show only magic values')
    parser.add_argument('--errors', action='store_true', help='Show only error handling issues')
    parser.add_argument('--naming', action='store_true', help='Show only naming issues')
    parser.add_argument('--nesting', action='store_true', help='Show only nesting issues')
    parser.add_argument('--max-file-mb', type=float, default=5.0, help='Max file size in MB')
    parser.add_argument('--max-depth', type=int, default=10, help='Max directory depth')
    
    args = parser.parse_args()
    
    target = Path(args.directory).resolve()
    if not target.exists():
        print(f"❌ Directory not found: {target}")
        sys.exit(1)
    
    print_banner("ENHANCED CODE PARSER")
    print(f"\n🔍 Target: {target}")
    
    # Initialize
    try:
        analyzer = CodeAnalyzer(
            max_file_mb=args.max_file_mb,
            max_depth=args.max_depth,
            excluded={'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist', '.pytest_cache', '.next', 'coverage', '.turbo', 'out'}
        )
    except ImportError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    print(f"   Parsers: {', '.join(sorted(analyzer.parsers.keys()))}")
    
    # Analyze
    print(f"\n⏳ Analyzing...")
    result = analyzer.analyze_directory(target)
    
    # Output based on options
    if args.dead_code:
        print_section("💀 DEAD CODE")
        for item in result.get_all_dead_code()[:30]:
            file_name = Path(item['file']).name
            conf_icon = '🔴' if item['confidence'] == 'high' else '🟡'
            print(f"\n{conf_icon} [{file_name}:{item['line']}] {item['type'].upper()}: {item['name']}")
            print(f"   {item['code_snippet'][:70]}")
            print(f"   Reason: {item['reason']} (confidence: {item['confidence']})")
    
    elif args.duplicates:
        print_section("🔁 DUPLICATE CODE")
        for dup in result.get_all_duplicates()[:20]:
            locs = dup.get('locations', [])
            print(f"\n{dup['line_count']} lines × {len(locs)} occurrences:")
            for loc in locs:
                print(f"   • {Path(loc['file']).name}: lines {loc['start']}-{loc['end']}")
            print(f"   Sample: {dup['sample_code'][:80]}")
    
    elif args.call_graph:
        print_section("📞 CALL GRAPH")
        for caller, callees in result.get_call_graph().items():
            callee_names = list(set(c['callee'] for c in callees))
            print(f"\n{caller}:")
            for name in callee_names[:10]:
                print(f"   → {name}")
    
    elif args.magic:
        print_section("🔢 MAGIC VALUES")
        for mv in result.get_all_magic_values()[:30]:
            file_name = Path(mv['file']).name
            type_icon = '🔢' if mv['type'] == 'number' else '📝'
            print(f"\n{type_icon} [{file_name}:{mv['line']}] {mv['value']}")
            print(f"   {mv['code_snippet'][:60]}")
            print(f"   → Extract as: {mv['suggested_name']}")
    
    elif args.errors:
        print_section("🚨 ERROR HANDLING ISSUES")
        for issue in result.get_error_handling_issues()[:30]:
            file_name = Path(issue['file']).name
            sev_icon = '🔴' if issue['severity'] == 'critical' else '🟡'
            print(f"\n{sev_icon} [{file_name}:{issue['line']}] {issue['type'].upper()}")
            print(f"   {issue['code_snippet'][:60]}")
            print(f"   Problem: {issue['description']}")
            print(f"   → {issue['suggestion']}")
    
    elif args.naming:
        print_section("📝 NAMING ISSUES")
        for ni in result.get_naming_issues()[:30]:
            file_name = Path(ni['file']).name
            print(f"\n[{file_name}:{ni['line']}] {ni['item_type']} '{ni['name']}'")
            print(f"   Style: {ni['actual_style']} → Expected: {ni['expected_style']}")
            print(f"   {ni['suggestion']}")
    
    elif args.nesting:
        print_section("🪆 DEEP NESTING")
        for nest in result.get_nesting_issues()[:20]:
            file_name = Path(nest['file']).name
            print(f"\n{nest['function']} ({file_name}:{nest['line']})")
            print(f"   Depth: {nest['max_depth']} levels")
            print(f"   Path: {' → '.join(nest['nesting_path'])}")
            print(f"   → {nest['suggestion']}")
    
    elif args.detailed:
        print_detailed_results(result)
    
    else:
        print_compact_results(result)
    
    # Save JSON if requested
    if args.json:
        save_json_results(result, Path(args.json))
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
