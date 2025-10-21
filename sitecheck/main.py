"""Main module for SiteCheck - analyze URLs for security and accessibility."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    AzureOpenAI,
    RateLimitError,
)
from playwright.async_api import (
    Browser,
    Page,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)


logger = logging.getLogger(__name__)


class SiteChecker:
    """Asynchronously checks sites for accessibility and security issues."""

    def __init__(
        self,
        urls_file: str = "data/urls.txt",
        azure_endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the site checker and Azure OpenAI client configuration."""

        load_dotenv()

        self.urls_file = Path(urls_file)
        self.endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = (
            deployment_name
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_MODEL")
        )
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")

        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint required. Set AZURE_OPENAI_ENDPOINT or pass azure_endpoint explicitly."
            )

        if not self.deployment_name:
            raise ValueError(
                "Azure OpenAI deployment name required. Set AZURE_OPENAI_DEPLOYMENT or provide deployment_name."
            )

        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key required. Store it in .env as AZURE_OPENAI_KEY or set via environment."
            )

        self.temperature = self._load_temperature()
        self._temperature_supported = self.temperature is not None

        self.client = self._create_openai_client()
        self.results: List[Dict[str, Any]] = []

    def _create_openai_client(self) -> AzureOpenAI:
        """Instantiate the Azure OpenAI client using API key authentication."""

        logger.info("Initializing AzureOpenAI client for endpoint %s", self.endpoint)
        return AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )

    def _load_temperature(self) -> Optional[float]:
        """Read an optional temperature override from the environment.

        Returns
        -------
        Optional[float]
            The temperature value to use or ``None`` if temperature should be omitted.
        """

        raw_value = os.getenv("AZURE_OPENAI_TEMPERATURE")
        disable_flag = os.getenv("AZURE_OPENAI_DISABLE_TEMPERATURE", "false").lower() in {"1", "true", "yes"}

        if disable_flag:
            return None

        if raw_value is None:
            # Default temperature was previously 0.1, retain it unless the deployment rejects the parameter.
            return 1

        try:
            value = float(raw_value)
        except ValueError:
            logger.warning("Invalid AZURE_OPENAI_TEMPERATURE value '%s'; temperature parameter will be omitted.", raw_value)
            return None

        return value
    
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
        """Use Azure OpenAI to analyze the site for security and information exposure."""

        prompt = f"""You are a security analyst reviewing a corporate website hosted on Azure.

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

Respond strictly in JSON using the following schema:
{{
    "description": "Brief description of the site",
    "is_secured": true/false,
    "sensitive_info_exposed": true/false,
    "sensitive_details": ["list of specific issues found"],
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "recommendations": ["list of specific recommendations"]
}}
"""

        messages = [
            {"role": "system", "content": "You are a meticulous Azure security auditor. Always respond with valid JSON."},
            {"role": "user", "content": prompt},
        ]

        last_error: Optional[str] = None
        for attempt in range(3):
            try:
                request_kwargs: Dict[str, Any] = {
                    "messages": messages,
                    "model": self.deployment_name,
                    "max_completion_tokens": 2048,
                    "response_format": {"type": "json_object"},
                }

                if self._temperature_supported and self.temperature is not None:
                    request_kwargs["temperature"] = self.temperature

                logger.info(
                    "[DEBUG] Calling Azure OpenAI (attempt %s/3) with endpoint=%s, deployment=%s, kwargs=%s",
                    attempt + 1,
                    self.endpoint,
                    self.deployment_name,
                    {k: v for k, v in request_kwargs.items() if k != "messages"}
                )

                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    **request_kwargs,
                )

                logger.info("[DEBUG] Azure OpenAI response received: %s choices, usage=%s", len(response.choices), getattr(response, "usage", None))

                if not response.choices:
                    logger.error("[DEBUG] Response object dump: %s", response)
                    raise ValueError("Azure OpenAI returned no choices")

                response_text = response.choices[0].message.content
                logger.info("[DEBUG] Raw response_text type=%s, value=%s", type(response_text).__name__, repr(response_text))
                logger.info(
                    "[DEBUG] Response content length=%s, finish_reason=%s, content_preview=%s",
                    len(response_text) if response_text else 0,
                    getattr(response.choices[0], "finish_reason", None),
                    (response_text[:200] if response_text else "<empty>")
                )

                if not response_text:
                    logger.error("[DEBUG] Empty response_text. Full response.choices[0]: %s", response.choices[0])
                    finish_reason = getattr(response.choices[0], "finish_reason", None)
                    if finish_reason == "length":
                        raise ValueError("Azure OpenAI response was truncated due to token limit. Consider increasing max_completion_tokens or reducing prompt size.")
                    raise ValueError("Azure OpenAI returned an empty response")

                parsed = self._parse_json_response(response_text)
                parsed.setdefault("model", self.deployment_name)
                if getattr(response, "usage", None):
                    parsed.setdefault(
                        "usage",
                        {
                            "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                            "completion_tokens": getattr(response.usage, "completion_tokens", None),
                            "total_tokens": getattr(response.usage, "total_tokens", None),
                        },
                    )
                return parsed

            except (APIConnectionError, RateLimitError, ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                wait_seconds = min(2 ** attempt, 8)
                logger.warning(
                    "[DEBUG] Azure OpenAI request failed (attempt %s/3) with %s: %s | Full exception: %s",
                    attempt + 1,
                    type(exc).__name__,
                    last_error,
                    repr(exc)
                )
                logger.exception("[DEBUG] Full traceback for attempt %s:", attempt + 1)
                await asyncio.sleep(wait_seconds)
            except APIError as exc:
                last_error = str(exc)
                error_message = last_error.lower()

                logger.warning(
                    "[DEBUG] Azure OpenAI APIError (attempt %s/3): %s",
                    attempt + 1,
                    last_error
                )

                if self._temperature_supported and (
                    "temperature" in error_message and (
                        "not supported" in error_message
                        or "parameter" in error_message
                        or "invalid" in error_message
                    )
                ):
                    logger.info(
                        "Azure OpenAI deployment rejected temperature parameter; retrying without temperature."
                    )
                    self._temperature_supported = False
                    # Retry immediately without waiting to respect rate limits.
                    continue

                wait_seconds = min(2 ** attempt, 8)
                logger.warning(
                    "[DEBUG] Azure OpenAI APIError (attempt %s/3): %s (retrying in %ss)",
                    attempt + 1,
                    last_error,
                    wait_seconds
                )
                await asyncio.sleep(wait_seconds)

        logger.error("[DEBUG] All Azure OpenAI attempts exhausted. Last error: %s", last_error)
        return {
            "error": f"AI analysis failed: {last_error or 'Unknown error'}",
            "description": "Analysis unavailable",
            "is_secured": None,
            "sensitive_info_exposed": None,
            "risk_level": "UNKNOWN",
        }

    @staticmethod
    def _parse_json_response(response_text: str) -> Dict[str, Any]:
        """Parse a JSON response, handling fenced code blocks."""

        if not response_text:
            raise ValueError("Azure OpenAI returned an empty response")

        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    
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

    async def aclose(self) -> None:
        """Release Azure OpenAI client resources."""

        close = getattr(self.client, "close", None)
        if callable(close):
            await asyncio.to_thread(close)


async def async_main():
    """Async entry point for the application."""
    print("SiteCheck - Azure Site Security Forensics Tool")
    print("=" * 50)

    try:
        checker = SiteChecker()
    except ValueError as config_error:
        print(f"\nConfiguration error: {config_error}")
        print("\nRequired environment variables:")
        print("  AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com")
        print("  AZURE_OPENAI_DEPLOYMENT=<gpt-5-deployment-name>")
        print("  AZURE_OPENAI_KEY=<your-azure-openai-key>  # place in .env")
        print("Optional:")
        print("  AZURE_OPENAI_API_VERSION=2024-12-01-preview")
        sys.exit(1)

    try:
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
    finally:
        await checker.aclose()


def main():
    """Main entry point for the CLI."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
