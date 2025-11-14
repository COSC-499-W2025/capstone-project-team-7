"""
Test script to verify skills analysis integration.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from src.cli.services.skills_analysis_service import SkillsAnalysisService
from src.cli.state import ScanState

def test_service_initialization():
    """Test that the skills analysis service can be initialized."""
    print("Testing SkillsAnalysisService initialization...")
    service = SkillsAnalysisService()
    print("✅ SkillsAnalysisService initialized successfully")
    return service

def test_skills_extraction():
    """Test skills extraction on a simple project."""
    print("\nTesting skills extraction...")
    service = SkillsAnalysisService()
    
    # Create a test directory with some code
    test_code = {
        "test.py": """
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        return f"Hello, I'm {self.name}"

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

# Using a hash map
cache = {}
cache['key'] = 'value'
result = cache.get('key', 'default')
"""
    }
    
    try:
        # Extract skills from the test code
        skills = service.extract_skills(
            target_path=Path("."),
            file_contents=test_code
        )
        
        print(f"✅ Extracted {len(skills)} skills")
        
        # Test formatting
        summary = service.format_summary(skills)
        print(f"\n{summary}")
        
        # Test export
        export_data = service.export_skills_data(skills)
        print(f"\n✅ Export data contains {export_data['total_skills']} skills")
        print(f"   Categories: {list(export_data['skills_by_category'].keys())}")
        
        return True
    except Exception as exc:
        print(f"❌ Skills extraction failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

def test_scan_state_integration():
    """Test that ScanState has the skills fields."""
    print("\nTesting ScanState integration...")
    state = ScanState()
    
    # Check that skills fields exist
    assert hasattr(state, 'skills_analysis_result'), "Missing skills_analysis_result field"
    assert hasattr(state, 'skills_analysis_error'), "Missing skills_analysis_error field"
    
    print("✅ ScanState has skills_analysis_result and skills_analysis_error fields")
    return True

def main():
    print("=" * 60)
    print("Skills Analysis Integration Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Service initialization
    try:
        test_service_initialization()
        results.append(("Service Initialization", True))
    except Exception as exc:
        print(f"❌ Service initialization failed: {exc}")
        results.append(("Service Initialization", False))
    
    # Test 2: Skills extraction
    try:
        success = test_skills_extraction()
        results.append(("Skills Extraction", success))
    except Exception as exc:
        print(f"❌ Skills extraction test failed: {exc}")
        results.append(("Skills Extraction", False))
    
    # Test 3: ScanState integration
    try:
        success = test_scan_state_integration()
        results.append(("ScanState Integration", success))
    except Exception as exc:
        print(f"❌ ScanState integration test failed: {exc}")
        results.append(("ScanState Integration", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
