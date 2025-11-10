"""
Tests for Code Analyzer
Focused test suite using fixture files (14 core tests)
"""
import pytest
from pathlib import Path
from conftest import import_from_local_analysis

code_parser = import_from_local_analysis("code_parser")

CodeAnalyzer = code_parser.CodeAnalyzer


class TestAnalyzerSetup:
    """Test analyzer initialization"""
    
    def test_analyzer_creates_with_defaults(self):
        """Test creating analyzer with default configuration"""
        analyzer = CodeAnalyzer()
        assert analyzer.max_file_mb == 5.0
        assert analyzer.max_depth == 10
        assert len(analyzer.parsers) > 0


class TestBadPythonFile:
    """Test bad_code.py analysis"""
    
    def test_bad_file_analyzed_successfully(self, analyzed_bad_file):
        """Test that bad Python file is analyzed"""
        assert analyzed_bad_file.success is True
        assert analyzed_bad_file.language == "python"
    
    def test_bad_file_has_security_issues(self, analyzed_bad_file):
        """Test security issues detected (API_KEY, PASSWORD, eval, exec)"""
        # Detects: API_KEY, PASSWORD, eval, exec (4 total)
        assert len(analyzed_bad_file.metrics.security_issues) >= 4
    
    def test_bad_file_has_functions_needing_refactor(self, analyzed_bad_file):
        """Test complex functions flagged (long, many params, high complexity)"""
        needs_refactor = any(f.needs_refactor for f in analyzed_bad_file.metrics.top_functions)
        assert needs_refactor is True
        
        # Check for long function (>50 lines)
        long_funcs = [f for f in analyzed_bad_file.metrics.top_functions if f.lines > 50]
        assert len(long_funcs) >= 1
        
        # Check for too many params (>5)
        many_params = [f for f in analyzed_bad_file.metrics.top_functions if f.params > 5]
        assert len(many_params) >= 1
    
    def test_bad_file_low_maintainability(self, analyzed_bad_file):
        """Test bad code has low maintainability score"""
        score = analyzed_bad_file.metrics.maintainability_score
        assert score < 60


class TestGoodPythonFile:
    """Test good_code.py analysis"""
    
    def test_good_file_analyzed_successfully(self, analyzed_good_file):
        """Test that good Python file is analyzed"""
        assert analyzed_good_file.success is True
        assert analyzed_good_file.language == "python"
    
    def test_good_file_no_security_issues(self, analyzed_good_file):
        """Test good code has no security issues"""
        assert len(analyzed_good_file.metrics.security_issues) == 0
    
    def test_good_file_high_maintainability(self, analyzed_good_file):
        """Test good code has reasonable maintainability score"""
        score = analyzed_good_file.metrics.maintainability_score
        # Good code should be at least 65 (actual: ~68.88)
        assert score >= 65
    
    def test_good_code_better_than_bad_code(self, analyzed_good_file, analyzed_bad_file):
        """Test that good code scores higher than bad code"""
        good_score = analyzed_good_file.metrics.maintainability_score
        bad_score = analyzed_bad_file.metrics.maintainability_score
        assert good_score > bad_score


class TestJavaScriptFile:
    """Test medium_quality.js analysis"""
    
    def test_js_file_analyzed_successfully(self, analyzed_js_file):
        """Test JavaScript file analyzed with security issues"""
        assert analyzed_js_file.success is True
        assert analyzed_js_file.language == "javascript"
        # Detects: API_KEY, SECRET, eval (3 total)
        assert len(analyzed_js_file.metrics.security_issues) >= 2
    
    def test_js_file_has_complex_functions(self, analyzed_js_file):
        """Test JavaScript has long complex functions"""
        # processOrderData is 67 lines
        long_funcs = [f for f in analyzed_js_file.metrics.top_functions if f.lines > 50]
        assert len(long_funcs) >= 1
        
        # Has functions with many params (calculateShipping: 7 params, createUser: 6 params)
        many_params = [f for f in analyzed_js_file.metrics.top_functions if f.params > 5]
        assert len(many_params) >= 1


class TestDirectoryAnalysis:
    """Test directory-level analysis"""
    
    def test_directory_analyzes_files(self, analyzed_directory):
        """Test fixture files analyzed successfully"""
        # May have extra files like consent_test_data.json
        assert analyzed_directory.successful >= 3
        assert len(analyzed_directory.files) >= 3
    
    def test_directory_detects_multiple_languages(self, analyzed_directory):
        """Test multiple languages detected (Python, JS)"""
        languages = analyzed_directory.summary['languages']
        assert 'python' in languages
        assert languages['python'] == 2
        assert 'javascript' in languages
    
    def test_directory_aggregates_security_issues(self, analyzed_directory):
        """Test security issues aggregated across files"""
        summary = analyzed_directory.summary
        # bad_code.py (4) + medium_quality.js (3) = 7 security issues
        assert summary['security_issues'] >= 7
        assert summary['functions_needing_refactor'] >= 3
    
    def test_refactor_candidates_sorted(self, analyzed_directory):
        """Test bad_code.py appears in refactor candidates (worst first)"""
        candidates = analyzed_directory.get_refactor_candidates(5)
        assert len(candidates) > 0
        
        candidate_names = [Path(c.path).name for c in candidates]
        assert 'bad_code.py' in candidate_names
        
        # Verify sorted by maintainability (worst first)
        if len(candidates) > 1:
            assert candidates[0].metrics.maintainability_score <= candidates[1].metrics.maintainability_score


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=code_parser", "--cov-report=html"])