"""
Test the skills summary functionality
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.cli.services.skills_analysis_service import SkillsAnalysisService

def test_skills_summary():
    print("=" * 70)
    print("Testing Skills Summary Display")
    print("=" * 70)
    
    service = SkillsAnalysisService()
    
    # Test code with various skills
    test_code = {
        "example.py": """
from abc import ABC, abstractmethod
from typing import List, Dict
import logging

class DataProcessor(ABC):
    @abstractmethod
    def process(self, data: List) -> Dict:
        pass

class HashMapProcessor(DataProcessor):
    def __init__(self):
        self.cache = {}
        self.logger = logging.getLogger(__name__)
    
    def process(self, data: List) -> Dict:
        try:
            result = {}
            for item in data:
                result[item.id] = item
            return result
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise

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

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def fibonacci(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    return memo[n]
"""
    }
    
    print("\n1. Extracting skills...")
    skills = service.extract_skills(
        target_path=Path("."),
        file_contents=test_code
    )
    print(f"   ✅ Extracted {len(skills)} skills\n")
    
    print("2. Testing format_skills_summary()...")
    summary = service.format_skills_summary(skills)
    print("\n" + "-" * 70)
    print(summary)
    print("-" * 70)
    
    print("\n3. Testing format_summary() (detailed)...")
    detailed = service.format_summary(skills)
    print("\n" + "-" * 70)
    print(detailed)
    print("-" * 70)
    
    print("\n4. Testing format_skills_paragraph() (narrative)...")
    paragraph = service.format_skills_paragraph(skills)
    print("\n" + "-" * 70)
    print(paragraph)
    print("-" * 70)
    
    print("\n5. Testing combined output (as shown in CLI)...")
    combined = "[Summary]\n" + paragraph + "\n\n" + "=" * 60 + "\n\n" + summary + "\n\n" + "=" * 60 + "\n\n" + detailed
    print("\n" + "-" * 70)
    print(combined)
    print("-" * 70)
    
    print("\n" + "=" * 70)
    print("✅ Skills summary test PASSED")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_skills_summary()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
