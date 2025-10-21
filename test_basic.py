"""Basic test to verify the sitecheck module can be imported and basic functionality works."""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        import sitecheck
        from sitecheck.main import SiteChecker
        from playwright.async_api import async_playwright
        import aiofiles
        from openai import AzureOpenAI
        from dotenv import load_dotenv
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_module_structure():
    """Test that the module has the expected structure."""
    print("\nTesting module structure...")
    from sitecheck.main import SiteChecker
    
    # Check that SiteChecker has expected methods
    expected_methods = ['read_urls', 'check_site', 'check_all_sites', 
                        'analyze_with_ai', 'generate_report', 'save_results']
    
    for method in expected_methods:
        if not hasattr(SiteChecker, method):
            print(f"✗ Missing method: {method}")
            return False
    
    print("✓ Module structure correct")
    return True

def test_urls_file_example():
    """Test that the example URLs file exists."""
    print("\nTesting example files...")
    example_file = Path("data/urls.txt.example")
    
    if not example_file.exists():
        print("✗ Example URLs file not found")
        return False
    
    print("✓ Example files exist")
    return True

def test_gitignore():
    """Test that .gitignore includes the necessary entries."""
    print("\nTesting .gitignore...")
    gitignore = Path(".gitignore")
    
    if not gitignore.exists():
        print("✗ .gitignore not found")
        return False
    
    content = gitignore.read_text()
    if "data/urls.txt" not in content:
        print("✗ data/urls.txt not in .gitignore")
        return False
    
    print("✓ .gitignore configured correctly")
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("SiteCheck Basic Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_module_structure,
        test_urls_file_example,
        test_gitignore,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
