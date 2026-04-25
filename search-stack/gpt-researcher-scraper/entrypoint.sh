#!/bin/bash
set -e

SCRAPER_PY=$(python -c "import site; print(site.getsitepackages()[0])")/gpt_researcher/scraper/scraper.py

if [ -f "$SCRAPER_PY" ]; then
    if ! grep -q '"crawl4ai": Crawl4AI' "$SCRAPER_PY"; then
        sed -i 's/\("firecrawl": FireCrawl,?\)/\1\n    "crawl4ai": Crawl4AI,/' "$SCRAPER_PY"
        echo "Patched $SCRAPER_PY to include Crawl4AI scraper"
    fi
    if ! grep -q 'from .crawl4ai import' "$SCRAPER_PY"; then
        sed -i 's/from \.firecrawl import FireCrawl/from .crawl4ai import Crawl4AI\nfrom .firecrawl import FireCrawl/' "$SCRAPER_PY"
    fi
fi

DEFAULT_CFG=$(python -c "import site; print(site.getsitepackages()[0])")/gpt_researcher/config/variables/default.py
if [ -f "$DEFAULT_CFG" ]; then
    sed -i 's/"SCRAPER": "bs"/"SCRAPER": "crawl4ai"/' "$DEFAULT_CFG"
fi

exec "$@"