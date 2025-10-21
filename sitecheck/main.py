"""Main module for SiteCheck - analyze URLs for security and accessibility."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import aiofiles
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from anthropic import Anthropic


class SiteChecker:
    """Asynchronously checks sites for accessibility and security issues."""
    
    def __init__(self, urls_file: str = "data/urls.txt", api_key: str = None):
        """Initialize the site checker.
        
        Args:
            urls_file: Path to the file containing URLs (one per line)
            api_key: Anthropic API key for AI analysis (or set ANTHROPIC_API_KEY env var)
        """
        self.urls_file = Path(urls_file)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = Anthropic(api_key=self.api_key)
        self.results: List[Dict[str, Any]] = []
    
    async def read_urls(self) -> List[str]:
        """Read URLs from the input file.
        
        Returns:
            List of URLs to check
        """
        if not self.urls_file.exists():
            raise FileNotFoundError(
                f"URLs file not found: {self.urls_file}\n"
                "Please create data/urls.txt with one URL per line."
            )
        
        async with aiofiles.open(self.urls_file, 'r') as f:
            content = await f.read()
            urls = [
                line.strip() 
                for line in content.splitlines() 
                if line.strip() and not line.strip().startswith('#')
            ]
        
        return urls
    
    async def check_site(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Check a single site for accessibility and security issues.
        
        Args:
            browser: Playwright browser instance
            url: URL to check
            
        Returns:
            Dictionary containing check results
        """
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "status_code": None,
            "error": None,
            "page_title": None,
            "page_content": None,
            "ai_analysis": None,
        }
        
        page: Page = None
        try:
            page = await browser.new_page()
            
            # Set a reasonable timeout
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response:
                result["status_code"] = response.status
                result["accessible"] = response.ok
            
            # Get page title
            result["page_title"] = await page.title()
            
            # Get page content (limit to avoid huge payloads)
            content = await page.content()
            result["page_content"] = content[:10000]  # First 10KB
            
            # Get visible text for AI analysis
            visible_text = await page.evaluate("""
                () => {
                    return document.body.innerText.substring(0, 5000);
                }
            """)
            
            # Analyze with AI if accessible
            if result["accessible"]:
                result["ai_analysis"] = await self.analyze_with_ai(url, visible_text, result["page_title"])
            
        except PlaywrightTimeout:
            result["error"] = "Timeout accessing the site"
        except Exception as e:
            result["error"] = f"Error: {str(e)}"
        finally:
            if page:
                await page.close()
        
        return result
    
    async def analyze_with_ai(self, url: str, content: str, title: str) -> Dict[str, Any]:
        """Use AI to analyze the site for security and information exposure.
        
        Args:
            url: The URL being analyzed
            content: Visible page content
            title: Page title
            
        Returns:
            Dictionary with AI analysis results
        """
        prompt = f"""You are a security analyst reviewing a corporate website deployed in Azure.

URL: {url}
Title: {title}

Page Content:
{content}

Please analyze this site and provide:
1. A brief description of what the site appears to do (1-2 sentences)
2. Whether the site is properly secured (requires authentication, has proper access controls)
3. Whether it exposes any potentially sensitive information such as:
   - Internal system details
   - Database connection strings or credentials
   - API keys or secrets
   - Internal network information
   - Employee or customer data
   - Development/debugging information
   - Directory listings or file paths
4. Risk level: LOW, MEDIUM, HIGH, or CRITICAL
5. Specific recommendations for securing this site

Provide your response in JSON format with the following structure:
{{
    "description": "Brief description of the site",
    "is_secured": true/false,
    "sensitive_info_exposed": true/false,
    "sensitive_details": ["list of specific issues found"],
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "recommendations": ["list of specific recommendations"]
}}
"""
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the response text
            response_text = message.content[0].text
            
            # Parse JSON from response (handle markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            analysis = json.loads(response_text)
            return analysis
            
        except Exception as e:
            return {
                "error": f"AI analysis failed: {str(e)}",
                "description": "Analysis unavailable",
                "is_secured": None,
                "sensitive_info_exposed": None,
                "risk_level": "UNKNOWN"
            }
    
    async def check_all_sites(self):
        """Check all sites from the URLs file."""
        urls = await self.read_urls()
        
        if not urls:
            print("No URLs found in the input file.")
            return
        
        print(f"Checking {len(urls)} sites...")
        
        async with async_playwright() as p:
            # Try to use playwright's chromium, fall back to system chromium if needed
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception:
                # Try system chromium as fallback
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium-browser"
                )
            
            try:
                # Process sites concurrently (but limit concurrency to avoid overwhelming)
                semaphore = asyncio.Semaphore(5)  # Max 5 concurrent checks
                
                async def check_with_semaphore(url: str):
                    async with semaphore:
                        print(f"Checking: {url}")
                        result = await self.check_site(browser, url)
                        self.results.append(result)
                        return result
                
                tasks = [check_with_semaphore(url) for url in urls]
                await asyncio.gather(*tasks)
                
            finally:
                await browser.close()
    
    def generate_report(self) -> str:
        """Generate a human-readable report of the findings.
        
        Returns:
            Formatted report string
        """
        if not self.results:
            return "No results to report."
        
        report_lines = [
            "=" * 80,
            "SITECHECK SECURITY AUDIT REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Sites Checked: {len(self.results)}",
            "=" * 80,
            ""
        ]
        
        # Categorize by risk level
        critical = []
        high = []
        medium = []
        low = []
        inaccessible = []
        
        for result in self.results:
            if not result["accessible"]:
                inaccessible.append(result)
            elif result.get("ai_analysis"):
                risk = result["ai_analysis"].get("risk_level", "UNKNOWN")
                if risk == "CRITICAL":
                    critical.append(result)
                elif risk == "HIGH":
                    high.append(result)
                elif risk == "MEDIUM":
                    medium.append(result)
                else:
                    low.append(result)
        
        # Summary
        report_lines.append("SUMMARY:")
        report_lines.append(f"  Critical Risk: {len(critical)}")
        report_lines.append(f"  High Risk: {len(high)}")
        report_lines.append(f"  Medium Risk: {len(medium)}")
        report_lines.append(f"  Low Risk: {len(low)}")
        report_lines.append(f"  Inaccessible: {len(inaccessible)}")
        report_lines.append("")
        
        # Detailed findings
        for category, sites in [
            ("CRITICAL RISK SITES", critical),
            ("HIGH RISK SITES", high),
            ("MEDIUM RISK SITES", medium),
            ("LOW RISK SITES", low),
            ("INACCESSIBLE SITES", inaccessible)
        ]:
            if sites:
                report_lines.append("-" * 80)
                report_lines.append(category)
                report_lines.append("-" * 80)
                
                for result in sites:
                    report_lines.append(f"\nURL: {result['url']}")
                    
                    if not result["accessible"]:
                        report_lines.append(f"  Status: INACCESSIBLE")
                        report_lines.append(f"  Error: {result.get('error', 'Unknown error')}")
                    else:
                        report_lines.append(f"  Status: HTTP {result.get('status_code', 'N/A')}")
                        report_lines.append(f"  Title: {result.get('page_title', 'N/A')}")
                        
                        if result.get("ai_analysis"):
                            ai = result["ai_analysis"]
                            report_lines.append(f"  Description: {ai.get('description', 'N/A')}")
                            report_lines.append(f"  Secured: {'No' if not ai.get('is_secured') else 'Yes'}")
                            
                            if ai.get("sensitive_info_exposed"):
                                report_lines.append(f"  ⚠ SENSITIVE INFORMATION EXPOSED:")
                                for detail in ai.get("sensitive_details", []):
                                    report_lines.append(f"    - {detail}")
                            
                            if ai.get("recommendations"):
                                report_lines.append(f"  Recommendations:")
                                for rec in ai.get("recommendations", []):
                                    report_lines.append(f"    - {rec}")
                    
                    report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    async def save_results(self, filename: str = None):
        """Save results to a JSON file.
        
        Args:
            filename: Output filename (default: data/results_TIMESTAMP.json)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/results_{timestamp}.json"
        
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(json.dumps(self.results, indent=2))
        
        print(f"\nResults saved to: {output_path}")


async def async_main():
    """Async entry point for the application."""
    print("SiteCheck - Azure Site Security Forensics Tool")
    print("=" * 50)
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nError: ANTHROPIC_API_KEY environment variable not set.")
        print("Please set it with your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    try:
        checker = SiteChecker()
        
        # Check all sites
        await checker.check_all_sites()
        
        # Generate and display report
        print("\n" + checker.generate_report())
        
        # Save detailed results
        await checker.save_results()
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
