"""
Code Analysis CLI Tool - Interactive
Greets user and prompts for path to analyze
"""
import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import code analysis module
from code_parser import CodeAnalyzer


def get_path_from_user():
    """Prompt user for path to analyze"""
    print("\n" + "="*80)
    print("  WELCOME TO CODE ANALYZER")
    print("="*80)
    print("\nThis tool will analyze your codebase and provide insights on:")
    print("  • Code quality and maintainability")
    print("  • Complex functions that need refactoring")
    print("  • Security issues and potential vulnerabilities")
    print("  • TODOs and FIXMEs")
    print("  • Overall project health\n")
    
    print("="*80)
    print("\nPlease enter the path to your project:")
    print("  Examples:")
    print("    • Current directory: .")
    print("    • Relative path: ./my-project")
    print("    • Absolute path: C:\\Users\\Aaron\\Projects\\MyApp")
    print("    • Or just drag and drop the folder here!")
    print("\n" + "="*80)
    
    while True:
        try:
            path_input = input("\n📁 Path: ").strip()
            
            # Handle empty input
            if not path_input:
                print("⚠️  Please enter a valid path")
                continue
            
            # Remove quotes if user added them
            path_input = path_input.strip('"').strip("'")
            
            # Convert to Path object
            path = Path(path_input)
            
            # Check if path exists
            if not path.exists():
                print(f"✗ Path not found: {path}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    return None
                continue
            
            return path
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Cancelled by user")
            return None
        except Exception as e:
            print(f"✗ Invalid path: {e}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return None


def main():
    """Main CLI entry point"""
    # Check if path was provided as command line argument
    if len(sys.argv) > 1:
        path_input = sys.argv[1].strip('"').strip("'")
        path = Path(path_input)
        
        if not path.exists():
            print(f"\n✗ Error: Path not found: {path}")
            return 1
    else:
        # Interactive mode - prompt user
        path = get_path_from_user()
        if path is None:
            return 1
    
    print(f"\n{'='*80}")
    print(f"  STARTING ANALYSIS")
    print(f"{'='*80}\n")
    
    print(f"🔍 Target: {path.absolute()}\n")
    
    # Initialize analyzer
    print("⚙️  Initializing analyzer...")
    try:
        analyzer = CodeAnalyzer(
            max_file_mb=5.0,
            max_depth=10,
            excluded={'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist'}
        )
    except ImportError as e:
        print(f"\n✗ Error: {e}")
        print("\n💡 Install required packages:")
        print("   pip install --target=lib tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
        input("\nPress Enter to exit...")
        return 1
    
    if len(analyzer.parsers) == 0:
        print("\n⚠️  WARNING: No parsers were initialized!")
        print("   Run: pip install --target=lib tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
        input("\nPress Enter to exit...")
        return 1
    
    print(f"   Parsers loaded: {len(analyzer.parsers)} ({', '.join(sorted(analyzer.parsers.keys()))})\n")
    
    # Analyze
    print("📂 Analyzing... (this may take a moment)")
    
    if path.is_file():
        # Single file analysis
        result = analyzer.analyze_file(path)
        
        if not result.success:
            print(f"\n✗ Failed to analyze: {result.error}")
            input("\nPress Enter to exit...")
            return 1
        
        # Display single file results
        print(f"\n{'='*80}")
        print(f"  ANALYSIS RESULTS")
        print(f"{'='*80}\n")
        
        print(f"📄 File: {result.path}")
        print(f"   Language: {result.language}")
        print(f"   Size: {result.size_mb:.2f} MB")
        print(f"   Analysis time: {result.time_ms:.2f}ms\n")
        
        if result.metrics:
            m = result.metrics
            print(f"📊 Metrics:")
            print(f"   Total lines:        {m.lines:,}")
            print(f"   Code lines:         {m.code_lines:,}")
            print(f"   Comment lines:      {m.comments:,}")
            print(f"   Functions:          {m.functions}")
            print(f"   Classes:            {m.classes}")
            print(f"   Complexity:         {m.complexity}")
            print(f"   Maintainability:    {m.maintainability_score:.1f}/100")
            print(f"   Refactor Priority:  {m.refactor_priority}\n")
            
            if m.top_functions:
                print(f"🔍 Top Complex Functions:")
                for func in m.top_functions[:5]:
                    status = "⚠️ " if func.needs_refactor else "✓ "
                    print(f"   {status}{func.name}:")
                    print(f"      {func.lines} lines, complexity {func.complexity}, {func.params} params")
                print()
            
            if m.security_issues:
                print(f"🔒 Security Issues ({len(m.security_issues)}):")
                for issue in m.security_issues[:5]:
                    print(f"   • {issue}")
                print()
            
            if m.todos:
                print(f"📝 TODOs/FIXMEs ({len(m.todos)}):")
                for todo in m.todos[:5]:
                    print(f"   • {todo}")
                print()
    
    else:
        # Directory analysis
        result = analyzer.analyze_directory(path)
        
        # Display results
        print(f"\n{'='*80}")
        print(f"  ANALYSIS RESULTS")
        print(f"{'='*80}\n")
        
        print(f"📊 Files:")
        print(f"   Total found:           {len(result.files)}")
        print(f"   Successfully analyzed: {result.successful}")
        print(f"   Failed:                {result.failed}\n")
        
        if result.summary['languages']:
            print(f"🗂️  Languages Detected:")
            for lang, count in sorted(result.summary['languages'].items(), key=lambda x: x[1], reverse=True):
                print(f"   {lang:15} {count:3} files")
            print()
        
        print(f"📈 Code Metrics:")
        print(f"   Total Lines:        {result.summary['total_lines']:,}")
        print(f"   Code Lines:         {result.summary['total_code']:,}")
        print(f"   Comment Lines:      {result.summary['total_comments']:,}")
        print(f"   Functions:          {result.summary['total_functions']}")
        print(f"   Classes:            {result.summary['total_classes']}\n")
        
        if result.successful > 0:
            maintainability = result.summary['avg_maintainability']
            
            print(f"🎯 Quality Metrics:")
            print(f"   Avg Maintainability: {maintainability:.1f}/100")
            print(f"   Avg Complexity:      {result.summary['avg_complexity']:.1f}")
            
            # Quality assessment
            if maintainability >= 80:
                status = "✅ EXCELLENT - Highly maintainable code"
            elif maintainability >= 70:
                status = "✓  GOOD - Reasonably maintainable"
            elif maintainability >= 60:
                status = "⚠️  FAIR - Some areas need improvement"
            elif maintainability >= 50:
                status = "⚠️  NEEDS WORK - Consider refactoring"
            else:
                status = "❌ CRITICAL - Significant refactoring needed"
            
            print(f"   Overall Status:      {status}\n")
            
            print(f"⚠️  Issues Found:")
            print(f"   Security Issues:        {result.summary['security_issues']}")
            print(f"   TODOs/FIXMEs:          {result.summary['todos']}")
            print(f"   High Priority Files:    {result.summary['high_priority_files']}")
            print(f"   Functions Need Refactor: {result.summary['functions_needing_refactor']}\n")
            
            # Show all functions that need refactoring
            all_problem_functions = []
            for file in result.files:
                if file.success and file.metrics:
                    for func in file.metrics.top_functions:
                        if func.needs_refactor:
                            all_problem_functions.append({
                                'file': Path(file.path).name,
                                'path': file.path,
                                'function': func
                            })
            
            if all_problem_functions:
                print(f"{'='*80}")
                print(f"  FUNCTIONS REQUIRING REFACTORING ({len(all_problem_functions)} total)")
                print(f"{'='*80}\n")
                
                # Sort by complexity (most complex first)
                all_problem_functions.sort(key=lambda x: x['function'].complexity, reverse=True)
                
                # Show top 15 most complex functions
                for i, item in enumerate(all_problem_functions[:15], 1):
                    func = item['function']
                    try:
                        rel_path = Path(item['path']).relative_to(path)
                    except ValueError:
                        rel_path = Path(item['path'])
                    
                    print(f"{i}. {func.name}")
                    print(f"   File: {item['file']} ({rel_path})")
                    print(f"   Lines: {func.lines}, Complexity: {func.complexity}, Params: {func.params}")
                    
                    # Show why it needs refactoring
                    reasons = []
                    if func.lines > 50:
                        reasons.append(f"Too long ({func.lines} lines)")
                    if func.complexity > 10:
                        reasons.append(f"Too complex (complexity {func.complexity})")
                    if func.params > 5:
                        reasons.append(f"Too many parameters ({func.params})")
                    
                    if reasons:
                        print(f"   Issues: {', '.join(reasons)}")
                    print()
                
                if len(all_problem_functions) > 15:
                    print(f"   ... and {len(all_problem_functions) - 15} more functions\n")
            
            # Show top refactoring candidates
            candidates = result.get_refactor_candidates(5)
            if candidates:
                print(f"{'='*80}")
                print(f"  TOP REFACTORING CANDIDATES (Files)")
                print(f"{'='*80}\n")
                
                for i, file in enumerate(candidates, 1):
                    file_name = Path(file.path).name
                    try:
                        rel_path = Path(file.path).relative_to(path)
                    except ValueError:
                        rel_path = Path(file.path)
                    score = file.metrics.maintainability_score
                    priority = file.metrics.refactor_priority
                    
                    print(f"{i}. {file_name}")
                    print(f"   Path: {rel_path}")
                    print(f"   Maintainability: {score:.0f}/100")
                    print(f"   Priority: {priority}")
                    print(f"   Lines: {file.metrics.lines} ({file.metrics.code_lines} code)")
                    print(f"   Functions: {file.metrics.functions}, Classes: {file.metrics.classes}")
                    print(f"   Complexity: {file.metrics.complexity}")
                    
                    # Show problematic functions
                    problem_funcs = [f for f in file.metrics.top_functions if f.needs_refactor]
                    if problem_funcs:
                        print(f"   ⚠️  Complex functions:")
                        for func in problem_funcs[:3]:
                            print(f"      • {func.name}: {func.lines} lines, complexity {func.complexity}")
                    
                    # Show issues
                    if file.metrics.security_issues:
                        print(f"   🔒 Security issues: {len(file.metrics.security_issues)}")
                        for issue in file.metrics.security_issues[:2]:
                            print(f"      • {issue}")
                    
                    if file.metrics.todos:
                        print(f"   📝 TODOs: {len(file.metrics.todos)}")
                    
                    print()
            
            # Summary
            print(f"{'='*80}")
            print(f"  SUMMARY")
            print(f"{'='*80}\n")
            
            if maintainability >= 70:
                status_word = "GOOD"
            elif maintainability >= 50:
                status_word = "FAIR"
            else:
                status_word = "NEEDS WORK"
            
            print(f"Analyzed {result.successful} files across {len(result.summary['languages'])} languages.\n")
            print(f"Key Takeaways:")
            print(f"  • Overall maintainability: {maintainability:.1f}/100 ({status_word})")
            print(f"  • {result.summary['high_priority_files']} files need immediate attention")
            print(f"  • {result.summary['functions_needing_refactor']} functions should be refactored")
            print(f"  • {result.summary['security_issues']} potential security issues")
            print(f"  • {result.summary['todos']} TODO/FIXME comments\n")
        else:
            print("\n⚠️  No files were successfully analyzed.\n")
            
            # Show why files failed
            failed_files = [f for f in result.files if not f.success]
            if failed_files:
                print(f"Failed Files (showing first 5):")
                for file in failed_files[:5]:
                    print(f"   ✗ {Path(file.path).name}: {file.error}")
                print()
    
    print(f"{'='*80}\n")
    
    # Wait for user before exiting (only in interactive mode)
    if len(sys.argv) == 1:
        input("Press Enter to exit...")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis cancelled by user\n")
        if len(sys.argv) == 1:
            input("Press Enter to exit...")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        if len(sys.argv) == 1:
            input("Press Enter to exit...")
        sys.exit(1)
        