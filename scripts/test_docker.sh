#!/bin/bash
set -e
echo "Building Docker image..."
docker-compose build
echo "Testing browser launch in container..."
docker-compose run --rm cast-service python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')
    print('✓ Browser launched successfully')
    print(f'✓ Page title: {page.title()}')
    browser.close()
"
echo "Docker build verified"
