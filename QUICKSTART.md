# Quick Start Guide

## 1. Installation (One-Time Setup)

```bash
# Install uv (if not already installed)
pip install uv

# Clone and enter the repository
git clone https://github.com/rtreit/sitecheck.git
cd sitecheck

# Install dependencies
uv sync

# Install Playwright browser
uv run playwright install chromium
```

## 2. Configuration

```bash
# Get your Anthropic API key from:
# https://console.anthropic.com/

# Set the API key
export ANTHROPIC_API_KEY='your-api-key-here'

# Create your URLs file
cp data/urls.txt.example data/urls.txt

# Edit data/urls.txt and add your Azure site URLs
nano data/urls.txt  # or use your preferred editor
```

Example `data/urls.txt`:
```
https://myapp.azurewebsites.net
https://api.company.com
https://internal-portal.company.com
```

## 3. Run the Security Audit

```bash
# Run the tool
uv run sitecheck

# Or use the demo script
./demo.sh
```

## 4. Review Results

The tool will:
1. Display a security report in your terminal
2. Save detailed JSON results to `data/results_TIMESTAMP.json`

### Understanding the Report

**Risk Levels:**
- 🔴 **CRITICAL**: Immediate action required (e.g., exposed credentials)
- 🟠 **HIGH**: Serious security issues (e.g., no authentication)
- 🟡 **MEDIUM**: Moderate concerns (e.g., debug mode enabled)
- 🟢 **LOW**: Minor issues or informational

### Sample Output

```
SUMMARY:
  Critical Risk: 1
  High Risk: 0
  Medium Risk: 1
  Low Risk: 2
  Inaccessible: 0

CRITICAL RISK SITES
-------------------
URL: https://internal-api.azurewebsites.net
  Status: HTTP 200
  ⚠ SENSITIVE INFORMATION EXPOSED:
    - Database connection strings visible
    - API keys in plain text
  Recommendations:
    - Implement authentication immediately
    - Use Azure Key Vault for secrets
```

## 5. Take Action

For each finding:
1. **CRITICAL/HIGH**: Address immediately
2. **MEDIUM**: Schedule for near-term remediation
3. **LOW**: Add to backlog

Common fixes:
- Enable Azure AD authentication
- Use Azure Private Link for internal services
- Move secrets to Azure Key Vault
- Disable public access to staging/dev environments
- Add IP whitelisting

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**"URLs file not found"**
```bash
cp data/urls.txt.example data/urls.txt
# Then edit data/urls.txt
```

**Browser installation fails**
```bash
# The tool will try to use system chromium as fallback
# If that doesn't work, install chromium:
sudo apt-get install chromium-browser
```

## Best Practices

1. **Run Regular Audits**: Schedule weekly or monthly scans
2. **Track Progress**: Compare results over time
3. **Prioritize**: Fix CRITICAL issues first
4. **Document**: Keep records of findings and fixes
5. **Automate**: Consider adding to CI/CD pipeline

## Getting Help

- Read the full [README.md](README.md)
- Check [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md) for sample reports
- See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
