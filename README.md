# sitecheck

A forensics tool for checking whether sites deployed in Azure are properly secured and flagging those which are accessible from outside.

## Overview

SiteCheck is a security audit tool that:
- Takes a list of URLs from a file (`data/urls.txt`)
- Asynchronously uses Playwright to browse to each site
- Uses AI (Claude) to analyze what each site does
- Checks whether sites are accessible from outside
- Identifies whether sites expose potentially sensitive information
- Generates a comprehensive security report

This tool is designed for security teams to audit corporate Azure deployments and identify potential security risks.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. Install uv if you haven't already:
```bash
pip install uv
```

2. Clone the repository:
```bash
git clone https://github.com/rtreit/sitecheck.git
cd sitecheck
```

3. Install dependencies:
```bash
uv sync
```

4. Install Playwright browsers:
```bash
uv run playwright install chromium
```

## Configuration

1. Create your URLs file:
```bash
cp data/urls.txt.example data/urls.txt
```

2. Edit `data/urls.txt` and add your URLs (one per line):
```
https://myapp.azurewebsites.net
https://internal-portal.company.com
https://api.company.com
```

3. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

You can get an API key from [Anthropic](https://console.anthropic.com/).

## Usage

Run the site checker:
```bash
uv run sitecheck
```

The tool will:
1. Read URLs from `data/urls.txt`
2. Visit each site using Playwright
3. Analyze each site with AI for security issues
4. Generate a detailed report on the console
5. Save full results to `data/results_TIMESTAMP.json`

## Output

The tool generates two types of output:

### 1. Console Report
A human-readable summary showing:
- Sites categorized by risk level (Critical, High, Medium, Low)
- Whether sites are properly secured
- Sensitive information that may be exposed
- Specific security recommendations

### 2. JSON Results
Detailed results saved to `data/results_TIMESTAMP.json` containing:
- Full page content
- AI analysis
- HTTP status codes
- Error details
- Timestamps

## Security Analysis

For each accessible site, the AI analyzes:
- **Purpose**: What the site does
- **Authentication**: Whether it requires proper login
- **Sensitive Data Exposure**:
  - Internal system details
  - Database credentials or connection strings
  - API keys or secrets
  - Internal network information
  - Employee or customer data
  - Debug information
  - Directory listings
- **Risk Level**: CRITICAL, HIGH, MEDIUM, or LOW
- **Recommendations**: Specific steps to secure the site

## Development

The project structure:
```
sitecheck/
├── sitecheck/
│   ├── __init__.py
│   └── main.py          # Main application code
├── data/
│   ├── urls.txt.example # Example URLs file
│   └── urls.txt         # Your URLs (gitignored)
├── pyproject.toml       # Project configuration
└── README.md
```

## Requirements

- Python 3.12+
- Anthropic API key
- Internet access for the sites being checked

## License

See LICENSE file for details.

