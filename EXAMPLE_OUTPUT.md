# Example SiteCheck Report

This is an example of what a SiteCheck report looks like.

```
================================================================================
SITECHECK SECURITY AUDIT REPORT
Generated: 2025-10-21 19:00:00
Sites Checked: 3
================================================================================

SUMMARY:
  Critical Risk: 1
  High Risk: 0
  Medium Risk: 1
  Low Risk: 1
  Inaccessible: 0

--------------------------------------------------------------------------------
CRITICAL RISK SITES
--------------------------------------------------------------------------------

URL: https://internal-api.azurewebsites.net
  Status: HTTP 200
  Title: Internal API Dashboard
  Description: This appears to be an internal API management dashboard with database connection details.
  Secured: No
  ⚠ SENSITIVE INFORMATION EXPOSED:
    - Database connection strings visible in configuration page
    - API keys displayed in plain text
    - Internal network topology information
    - Development environment credentials
  Recommendations:
    - Implement authentication immediately (Azure AD integration)
    - Remove all sensitive information from public pages
    - Use Azure Key Vault for secrets management
    - Enable private endpoints for internal services
    - Add IP whitelisting

--------------------------------------------------------------------------------
MEDIUM RISK SITES
--------------------------------------------------------------------------------

URL: https://staging.company.com
  Status: HTTP 200
  Title: Staging Environment - Company Portal
  Description: A staging/development version of the company portal
  Secured: No
  ⚠ SENSITIVE INFORMATION EXPOSED:
    - Version information and framework details exposed
    - Debug mode appears to be enabled
    - Directory listing accessible at /assets
  Recommendations:
    - Disable public access to staging environments
    - Remove debug information from headers
    - Disable directory listings
    - Consider using Azure Private Link

--------------------------------------------------------------------------------
LOW RISK SITES
--------------------------------------------------------------------------------

URL: https://www.company.com
  Status: HTTP 200
  Title: Company - Official Website
  Description: Public corporate website with general information
  Secured: Yes
  Recommendations:
    - Site appears properly configured for public access
    - Consider adding security headers (CSP, HSTS)
    - Regular security audits recommended

================================================================================
END OF REPORT
================================================================================
```

## Detailed JSON Output

The tool also saves detailed JSON results to `data/results_TIMESTAMP.json`:

```json
[
  {
    "url": "https://internal-api.azurewebsites.net",
    "timestamp": "2025-10-21T19:00:15.123456",
    "accessible": true,
    "status_code": 200,
    "error": null,
    "page_title": "Internal API Dashboard",
    "page_content": "<!DOCTYPE html>...",
    "ai_analysis": {
      "description": "This appears to be an internal API management dashboard with database connection details.",
      "is_secured": false,
      "sensitive_info_exposed": true,
      "sensitive_details": [
        "Database connection strings visible in configuration page",
        "API keys displayed in plain text",
        "Internal network topology information",
        "Development environment credentials"
      ],
      "risk_level": "CRITICAL",
      "recommendations": [
        "Implement authentication immediately (Azure AD integration)",
        "Remove all sensitive information from public pages",
        "Use Azure Key Vault for secrets management",
        "Enable private endpoints for internal services",
        "Add IP whitelisting"
      ]
    }
  }
]
```
