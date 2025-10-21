"""Test the sitecheck tool with actual URL checking (without AI)."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sitecheck.main import SiteChecker
from playwright.async_api import async_playwright


async def test_url_reading():
    """Test that URLs can be read from a file."""
    print("Testing URL reading...")
    
    # Create a temporary test URLs file
    test_file = Path("/tmp/test_urls.txt")
    test_file.write_text("https://example.com\nhttps://httpbin.org\n# comment line\n")
    
    # Mock checker without API key requirement
    checker = SiteChecker.__new__(SiteChecker)
    checker.urls_file = test_file
    
    urls = await checker.read_urls()
    
    assert len(urls) == 2, f"Expected 2 URLs, got {len(urls)}"
    assert "example.com" in urls[0], "First URL should contain example.com"
    assert "httpbin.org" in urls[1], "Second URL should contain httpbin.org"
    
    print("✓ URL reading works correctly")
    return True


async def test_playwright_browser():
    """Test that Playwright can launch a browser."""
    print("\nTesting Playwright browser launch...")
    
    try:
        async with async_playwright() as p:
            # Try to use system chromium
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium-browser"
            )
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=10000)
            title = await page.title()
            await browser.close()
            
            assert "Example Domain" in title, f"Unexpected title: {title}"
            print(f"✓ Playwright works correctly (page title: {title})")
            return True
            
    except Exception as e:
        print(f"✗ Playwright test failed: {e}")
        return False


async def test_site_checking_without_ai():
    """Test site checking without AI analysis."""
    print("\nTesting site checking (without AI)...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium-browser"
            )
            
            # Create a minimal checker
            checker = SiteChecker.__new__(SiteChecker)
            checker.results = []
            
            # Test checking a single site
            result = await checker.check_site(browser, "https://example.com")
            
            await browser.close()
            
            assert result["url"] == "https://example.com"
            assert result["accessible"] == True, "example.com should be accessible"
            assert result["status_code"] == 200, f"Expected status 200, got {result['status_code']}"
            assert "Example Domain" in result.get("page_title", ""), "Should have correct title"
            
            print(f"✓ Site checking works (status: {result['status_code']}, title: {result['page_title']})")
            return True
            
    except Exception as e:
        print(f"✗ Site checking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all async tests."""
    print("=" * 60)
    print("SiteCheck Functional Tests (without AI)")
    print("=" * 60)
    
    tests = [
        test_url_reading(),
        test_playwright_browser(),
        test_site_checking_without_ai(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Check for exceptions
    passed = sum(1 for r in results if r is True)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All functional tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


def main():
    """Entry point."""
    return asyncio.run(run_all_tests())


if __name__ == "__main__":
    sys.exit(main())
