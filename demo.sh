#!/bin/bash
# Demo script showing how to use sitecheck

echo "SiteCheck Demo"
echo "=============="
echo ""

# Check if virtual environment is activated
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    uv sync
    uv run playwright install chromium
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "To use sitecheck, you need an Anthropic API key."
    echo "Get one at: https://console.anthropic.com/"
    echo ""
    echo "Then set it with:"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo ""
    exit 1
fi

# Check for URLs file
if [ ! -f "data/urls.txt" ]; then
    echo "Creating example data/urls.txt file..."
    cat > data/urls.txt <<EOF
# Add your URLs here (one per line)
# Example Azure sites:
# https://myapp.azurewebsites.net
# https://api.company.com
# https://internal-portal.company.com

https://example.com
EOF
    echo ""
    echo "Please edit data/urls.txt and add the URLs you want to check."
    echo "Then run this script again."
    exit 0
fi

# Count URLs
url_count=$(grep -v '^#' data/urls.txt | grep -v '^$' | wc -l)
echo "Found $url_count URLs to check in data/urls.txt"
echo ""

# Run the checker
echo "Running sitecheck..."
uv run sitecheck

echo ""
echo "Check the data/ directory for detailed JSON results."
