# sitecheck

A forensics tool for checking whether sites deployed in Azure are properly secured and flagging those which are accessible from outside.

## Overview

SiteCheck is a security audit tool that:
- Takes a list of URLs from a file (`data/urls.txt`)
- Asynchronously uses Playwright to browse to each site
- Uses Azure OpenAI (GPT-5 deployment) to analyze what each site does
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

3. Provide Azure OpenAI credentials by creating a `.env` file in the project root:

```
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=<gpt-5-deployment-name>
AZURE_OPENAI_KEY=<your-azure-openai-key>
# Optional override if your deployment uses a different API version
# AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

The project loads environment variables with [`python-dotenv`](https://pypi.org/project/python-dotenv/), so placing the values in `.env` is usually the easiest approach. You can also set them directly in the shell if you prefer.

## Usage

Run the site checker:
```bash
uv run sitecheck
```

The tool will:
1. Read URLs from `data/urls.txt`
2. Visit each site using Playwright
3. Analyze each site with Azure OpenAI for security issues
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
├── demo.sh              # Demo script
├── EXAMPLE_OUTPUT.md    # Example report output
└── README.md
```

## Example Output

See [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md) for an example of what the security report looks like.

## Testing

The project includes basic tests:

```bash
# Install test tooling once if you plan to run pytest
uv pip install pytest pytest-asyncio

# Run the full test suite
uv run python -m pytest

# Alternatively, execute the standalone functional script
uv run python test_functional.py
```

> **Note:** `test_functional.py` is an integration-style coroutine script that assumes network access and a Chromium browser. The pytest suite focuses on import and structural checks unless you adapt the functional tests to use proper pytest async markers.

## Security Notes

- All dependencies are checked for known vulnerabilities
- The tool uses secure HTTPS connections
- No sensitive data (URLs, results, API keys) is sent to third parties except:
  - Azure OpenAI for AI analysis of page content
  - The target URLs being checked (via Playwright browser)
- Results are stored locally in the `data/` directory
- The `data/urls.txt` file is gitignored to prevent accidental commits

## Limitations

- Requires internet access to check external sites
- AI analysis requires an Anthropic API key (paid service)
- Browser automation may not work with sites requiring complex authentication
- Rate limiting may apply for large numbers of URLs

## Requirements

- Python 3.12+
- Azure OpenAI resource (with GPT-4o/GPT-5 style chat deployment)
- Internet access for the sites being checked

## License

See LICENSE file for details.

