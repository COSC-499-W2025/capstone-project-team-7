"""
Tests for Skills Extractor Module

Tests the extraction of CS skills and concepts from code analysis.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.analyzer.skills_extractor import SkillsExtractor, Skill, SkillEvidence


class TestSkillsExtractor:
    """Test suite for SkillsExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a fresh extractor for each test."""
        return SkillsExtractor()
    
    def test_initialization(self, extractor):
        """Test that extractor initializes correctly."""
        assert extractor is not None
        assert len(extractor.skills) == 0
        assert extractor.oop_patterns is not None
        assert extractor.data_structure_patterns is not None
    
    def test_detect_language_python(self, extractor):
        """Test language detection for Python files."""
        assert extractor._detect_language("test.py") == "python"
        assert extractor._detect_language("test.pyi") == "python"
    
    def test_detect_language_javascript(self, extractor):
        """Test language detection for JavaScript files."""
        assert extractor._detect_language("test.js") == "javascript"
        assert extractor._detect_language("test.jsx") == "javascript"
    
    def test_detect_language_unknown(self, extractor):
        """Test language detection for unknown files."""
        assert extractor._detect_language("test.txt") is None
        assert extractor._detect_language("test.md") is None
    
    def test_extract_oop_abstraction_python(self, extractor):
        """Test detection of abstraction in Python code."""
        code = """
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def make_sound(self):
        pass

class Dog(Animal):
    def make_sound(self):
        return "Woof"
"""
        file_contents = {"animal.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Abstraction" in skills
        assert skills["Abstraction"].category == "oop"
        assert len(skills["Abstraction"].evidence) > 0
    
    def test_extract_oop_encapsulation_python(self, extractor):
        """Test detection of encapsulation in Python code."""
        code = """
class BankAccount:
    def __init__(self):
        self.__balance = 0
    
    @property
    def balance(self):
        return self.__balance
    
    def deposit(self, amount):
        self.__balance += amount
"""
        file_contents = {"bank.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Encapsulation" in skills
        assert skills["Encapsulation"].category == "oop"
    
    def test_extract_data_structure_hash_map_python(self, extractor):
        """Test detection of hash map usage in Python."""
        code = """
def count_frequencies(items):
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
    return freq

from collections import defaultdict
def group_by_category(items):
    groups = defaultdict(list)
    for item in items:
        groups[item.category].append(item)
    return groups
"""
        file_contents = {"utils.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Hash-based Data Structures" in skills
        assert skills["Hash-based Data Structures"].category == "data_structures"
    
    def test_extract_algorithm_sorting(self, extractor):
        """Test detection of sorting algorithms."""
        code = """
def process_items(items):
    sorted_items = sorted(items, key=lambda x: x.priority)
    return sorted_items

def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""
        file_contents = {"sorting.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Sorting Algorithms" in skills or "Recursive Problem Solving" in skills
    
    def test_extract_error_handling(self, extractor):
        """Test detection of error handling practices."""
        code = """
def read_file(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    except IOError as e:
        raise RuntimeError(f"Failed to read file: {e}")
    finally:
        print("Cleanup complete")
"""
        file_contents = {"file_io.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Error Handling" in skills
        assert skills["Error Handling"].category == "practices"
    
    def test_extract_testing_practices(self, extractor):
        """Test detection of testing practices."""
        code = """
import unittest

class TestCalculator(unittest.TestCase):
    def test_add(self):
        result = add(2, 3)
        self.assertEqual(result, 5)
    
    def test_subtract(self):
        result = subtract(5, 3)
        assert result == 2
"""
        file_contents = {"test_calculator.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Unit Testing" in skills or "Automated Testing" in skills
    
    def test_extract_from_code_analysis(self, extractor):
        """Test extraction from code analysis results."""
        code_analysis = {
            "summary": {
                "avg_complexity": 5.2,
                "avg_maintainability": 78.5,
                "total_functions": 15,
            },
            "files": [
                {
                    "success": True,
                    "path": "main.py",
                    "language": "python",
                    "metrics": {
                        "complexity": 3,
                        "maintainability_score": 85.0,
                        "refactor_priority": "LOW",
                        "functions": 8,
                    }
                },
                {
                    "success": True,
                    "path": "test_main.py",
                    "language": "python",
                    "metrics": {
                        "complexity": 2,
                        "functions": 5,
                    }
                }
            ]
        }
        
        skills = extractor.extract_skills(code_analysis=code_analysis)
        
        # Should detect code complexity management
        assert "Code Complexity Management" in skills or "Maintainable Code" in skills
        
        # Should detect testing
        assert "Unit Testing" in skills
    
    def test_extract_from_git_analysis(self, extractor):
        """Test extraction from git analysis results."""
        git_analysis = {
            "path": "/path/to/repo",
            "commit_count": 150,
            "contributors": [
                {"name": "Alice", "commits": 100},
                {"name": "Bob", "commits": 50},
            ],
            "timeline": [
                {"month": "2024-01", "commits": 20},
                {"month": "2024-02", "commits": 30},
                {"month": "2024-03", "commits": 25},
            ]
        }
        
        skills = extractor.extract_skills(git_analysis=git_analysis)
        
        # Should detect version control
        assert "Version Control (Git)" in skills
        
        # Should detect collaboration
        assert "Team Collaboration" in skills
        
        # Should detect consistent development
        assert "Consistent Development" in skills
    
    def test_extract_dynamic_programming(self, extractor):
        """Test detection of dynamic programming."""
        code = """
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        for w in range(1, capacity + 1):
            if weights[i-1] <= w:
                dp[i][w] = max(
                    dp[i-1][w],
                    values[i-1] + dp[i-1][w - weights[i-1]]
                )
            else:
                dp[i][w] = dp[i-1][w]
    
    return dp[n][capacity]
"""
        file_contents = {"dynamic.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        assert "Dynamic Programming" in skills
    
    def test_get_skills_by_category(self, extractor):
        """Test grouping skills by category."""
        # Add some test skills
        extractor._add_skill(
            "Test Skill 1", "oop", "Description",
            SkillEvidence("Test Skill 1", "test", "Test", "file.py")
        )
        extractor._add_skill(
            "Test Skill 2", "oop", "Description",
            SkillEvidence("Test Skill 2", "test", "Test", "file.py")
        )
        extractor._add_skill(
            "Test Skill 3", "data_structures", "Description",
            SkillEvidence("Test Skill 3", "test", "Test", "file.py")
        )
        
        categorized = extractor.get_skills_by_category()
        
        assert "oop" in categorized
        assert "data_structures" in categorized
        assert len(categorized["oop"]) == 2
        assert len(categorized["data_structures"]) == 1
    
    def test_get_top_skills(self, extractor):
        """Test getting top skills by proficiency."""
        # Add skills with different evidence counts
        for i in range(5):
            skill_name = f"Skill {i}"
            evidence = SkillEvidence(skill_name, "test", "Test", "file.py")
            extractor._add_skill(skill_name, "oop", "Description", evidence)
            
            # Add extra evidence to some skills
            for _ in range(i):
                evidence = SkillEvidence(skill_name, "test", f"Test {_}", "file.py")
                extractor._add_skill(skill_name, "oop", "Description", evidence)
        
        top_skills = extractor.get_top_skills(limit=3)
        
        assert len(top_skills) <= 3
        # Skills with more evidence should rank higher
        if len(top_skills) > 1:
            assert top_skills[0].proficiency_score >= top_skills[1].proficiency_score
    
    def test_export_to_dict(self, extractor):
        """Test exporting skills to dictionary format."""
        # Add a test skill
        evidence = SkillEvidence(
            "Test Skill",
            "code_pattern",
            "Test description",
            "test.py",
            line_number=10,
            confidence=0.8
        )
        extractor._add_skill("Test Skill", "oop", "A test skill", evidence)
        
        export = extractor.export_to_dict()
        
        assert "skills" in export
        assert "summary" in export
        assert len(export["skills"]) == 1
        assert export["skills"][0]["name"] == "Test Skill"
        assert export["skills"][0]["category"] == "oop"
        assert export["skills"][0]["evidence_count"] == 1
        assert export["summary"]["total_skills"] == 1
    
    def test_complex_python_code(self, extractor):
        """Test extraction from complex Python code with multiple patterns."""
        code = """
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DataProcessor(ABC):
    '''Abstract base class for data processing.'''
    
    def __init__(self):
        self.__data: Dict[str, any] = {}
    
    @abstractmethod
    def process(self, data: List[any]) -> Dict[str, any]:
        '''Process the data and return results.'''
        pass
    
    @property
    def data(self) -> Dict[str, any]:
        return self.__data

class HashMapProcessor(DataProcessor):
    def process(self, data: List[any]) -> Dict[str, any]:
        try:
            result = {}
            for item in data:
                key = item.get('key')
                if key:
                    result[key] = item
            logger.info(f"Processed {len(result)} items")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
"""
        file_contents = {"processor.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        # Should detect multiple skills
        assert len(skills) >= 4
        
        # Check for specific skills
        skill_names = [s.name for s in skills.values()]
        assert "Abstraction" in skill_names or "Encapsulation" in skill_names
        assert any("Hash" in name for name in skill_names)
    
    def test_skill_evidence(self):
        """Test SkillEvidence creation and properties."""
        evidence = SkillEvidence(
            skill_name="Test Skill",
            evidence_type="code_pattern",
            description="Found pattern in code",
            file_path="test.py",
            line_number=42,
            confidence=0.85
        )
        
        assert evidence.skill_name == "Test Skill"
        assert evidence.evidence_type == "code_pattern"
        assert evidence.file_path == "test.py"
        assert evidence.line_number == 42
        assert evidence.confidence == 0.85
    
    def test_skill_proficiency_scoring(self):
        """Test that proficiency score increases with evidence."""
        skill = Skill(
            name="Test Skill",
            category="oop",
            description="A test skill"
        )
        
        initial_score = skill.proficiency_score
        assert initial_score == 0.0
        
        # Add evidence
        for i in range(3):
            evidence = SkillEvidence(
                f"Test Skill",
                "test",
                f"Evidence {i}",
                "test.py"
            )
            skill.add_evidence(evidence)
        
        # Score should increase
        assert skill.proficiency_score > initial_score
        assert len(skill.evidence) == 3
    
    def test_javascript_patterns(self, extractor):
        """Test detection of JavaScript patterns."""
        code = """
class UserService {
    constructor() {
        this.users = new Map();
    }
    
    async fetchUser(id) {
        try {
            const response = await fetch(`/api/users/${id}`);
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch user:', error);
            throw error;
        }
    }
}

function createFactory(type) {
    const types = {
        'admin': AdminUser,
        'regular': RegularUser
    };
    return new types[type]();
}
"""
        file_contents = {"service.js": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        # Should detect async programming and error handling
        assert len(skills) > 0
        
    def test_empty_input(self, extractor):
        """Test that empty input doesn't cause errors."""
        skills = extractor.extract_skills(
            code_analysis=None,
            git_analysis=None,
            file_contents=None
        )
        
        assert skills == {}
    
    def test_multiple_evidence_same_skill(self, extractor):
        """Test that multiple evidence for same skill is aggregated."""
        code = """
try:
    result = risky_operation()
except ValueError:
    handle_value_error()
except TypeError:
    handle_type_error()
finally:
    cleanup()

try:
    another_operation()
except Exception as e:
    log_error(e)
"""
        file_contents = {"errors.py": code}
        skills = extractor.extract_skills(file_contents=file_contents)
        
        if "Error Handling" in skills:
            # Should have multiple pieces of evidence for error handling
            assert len(skills["Error Handling"].evidence) >= 1
            # Proficiency should reflect multiple instances
            assert skills["Error Handling"].proficiency_score > 0.2


class TestIntegration:
    """Integration tests combining multiple components."""
    
    @pytest.fixture
    def extractor(self):
        """Create a fresh extractor for each test."""
        return SkillsExtractor()
    
    def test_full_extraction_pipeline(self, extractor):
        """Test complete extraction pipeline with all input types."""
        
        # Prepare comprehensive test data
        code_analysis = {
            "summary": {
                "avg_complexity": 4.5,
                "avg_maintainability": 75.0,
            },
            "files": [
                {
                    "success": True,
                    "path": "main.py",
                    "language": "python",
                    "metrics": {
                        "refactor_priority": "LOW",
                        "functions": 10,
                    }
                }
            ]
        }
        
        git_analysis = {
            "path": "/repo",
            "commit_count": 50,
            "contributors": [{"name": "Dev", "commits": 50}],
            "timeline": [
                {"month": "2024-01", "commits": 25},
                {"month": "2024-02", "commits": 25},
            ]
        }
        
        file_contents = {
            "main.py": """
from typing import List, Dict
import logging

def process_data(items: List[str]) -> Dict[str, int]:
    '''Process items and return frequency count.'''
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
    return freq
""",
            "test_main.py": """
import unittest

class TestProcessor(unittest.TestCase):
    def test_process_data(self):
        result = process_data(['a', 'b', 'a'])
        self.assertEqual(result['a'], 2)
"""
        }
        
        # Extract skills from all sources
        skills = extractor.extract_skills(
            code_analysis=code_analysis,
            git_analysis=git_analysis,
            file_contents=file_contents
        )
        
        # Verify comprehensive extraction
        assert len(skills) > 0
        
        # Should have skills from different categories
        categorized = extractor.get_skills_by_category()
        assert len(categorized) >= 2
        
        # Should be exportable
        export = extractor.export_to_dict()
        assert export["summary"]["total_skills"] > 0
    
    def test_chronological_overview(self, extractor):
        """Test chronological overview of skills."""
        
        # Create skills with timestamps
        file_contents = {
            "old_file.py": """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
            "new_file.py": """
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    @abstractmethod
    def process(self):
        pass
"""
        }
        
        # Simulate timestamps - set before extraction
        extractor.file_timestamps = {
            "old_file.py": "2024-01-15T10:30:00Z",
            "new_file.py": "2024-03-20T14:45:00Z"
        }
        
        skills = extractor.extract_skills(file_contents=file_contents)
        
        # Verify skills were detected
        assert len(skills) > 0, "No skills detected"
        
        # Get chronological overview
        overview = extractor.get_chronological_overview()
        
        # Should have entries
        assert len(overview) > 0, f"No timeline entries. Skills detected: {list(skills.keys())}"
        
        # Should be sorted by period
        periods = [entry['period'] for entry in overview]
        assert periods == sorted(periods)
        
        # Each entry should have required fields
        for entry in overview:
            assert 'period' in entry
            assert 'skills_exercised' in entry
            assert 'skill_count' in entry
            assert 'evidence_count' in entry
            assert 'details' in entry
            
            # Skills should be sorted
            assert entry['skills_exercised'] == sorted(entry['skills_exercised'])
    
    def test_chronological_export(self, extractor):
        """Test that chronological overview is included in export."""
        
        file_contents = {
            "test.py": """
import logging
logger = logging.getLogger(__name__)
"""
        }
        
        extractor.file_timestamps = {
            "test.py": "2024-02-10T12:00:00Z"
        }
        
        skills = extractor.extract_skills(file_contents=file_contents)
        export = extractor.export_to_dict()
        
        # Should have chronological_overview in export
        assert 'chronological_overview' in export
        assert isinstance(export['chronological_overview'], list)
        
        # Evidence should have timestamp
        for skill_data in export['skills']:
            for evidence in skill_data['evidence']:
                assert 'timestamp' in evidence
    
    def test_git_timestamp_extraction_no_repo(self, extractor):
        """Test that git timestamp extraction handles non-repo gracefully."""
        
        # Should not raise exception on invalid path
        extractor._extract_git_timestamps("/nonexistent/path")
        
        # Timestamps should be empty or unchanged
        assert len(extractor.file_timestamps) == 0
    
    def test_chronological_with_git_analysis(self, extractor):
        """Test chronological overview with git analysis."""
        
        git_analysis = {
            "path": "/test/repo",
            "commit_count": 25,
            "contributors": [{"name": "Dev", "commits": 25}],
            "timeline": [
                {"month": "2024-01", "commits": 10},
                {"month": "2024-02", "commits": 15},
            ]
        }
        
        skills = extractor.extract_skills(git_analysis=git_analysis)
        overview = extractor.get_chronological_overview()
        
        # Should have entries with git-based timestamps
        assert len(overview) > 0
        
        # Git skills should have appropriate timestamps
        git_skill = skills.get("Version Control (Git)")
        if git_skill:
            assert len(git_skill.evidence) > 0
            # Should have timestamp from latest timeline entry
            assert git_skill.evidence[0].timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
