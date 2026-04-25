#!/bin/bash
set -e

# Run the Python patch script to inject Crawl4AI scraper and custom image provider
python /tmp/patch_scraper.py

# Execute the original command
exec "$@"
