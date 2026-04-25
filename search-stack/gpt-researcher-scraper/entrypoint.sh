#!/bin/bash
set -e

SITE_PKG=$(python -c "import site; print(site.getsitepackages()[0])")

# Install Crawl4AI scraper at runtime (entrypoint runs as user with permissions)
SCRAPER_DIR="$SITE_PKG/gpt_researcher/scraper/crawl4ai"
if [ -d "/tmp/crawl4ai_scraper" ]; then
    mkdir -p "$SCRAPER_DIR"
    cp -r /tmp/crawl4ai_scraper/* "$SCRAPER_DIR/"
    echo "Installed Crawl4AI scraper to $SCRAPER_DIR"
fi

# Install OpenAI image provider at runtime
IMAGE_PROVIDER_DIR="$SITE_PKG/gpt_researcher/llm_provider/image"
if [ -f "/tmp/openai_image_provider.py" ]; then
    mkdir -p "$IMAGE_PROVIDER_DIR"
    cp /tmp/openai_image_provider.py "$IMAGE_PROVIDER_DIR/"
    cp /tmp/provider_factory.py "$IMAGE_PROVIDER_DIR/"
    if [ -f "/tmp/image_provider_init.py" ]; then
        cp /tmp/image_provider_init.py "$IMAGE_PROVIDER_DIR/__init__.py"
    fi
    echo "Installed OpenAI image provider to $IMAGE_PROVIDER_DIR"
fi

# Patch SCRAPER_CLASSES to include Crawl4AI
SCRAPER_PY="$SITE_PKG/gpt_researcher/scraper/scraper.py"
if [ -f "$SCRAPER_PY" ]; then
    if ! grep -q '"crawl4ai": Crawl4AI' "$SCRAPER_PY"; then
        sed -i 's/\("firecrawl": FireCrawl,?\)/\1\n    "crawl4ai": Crawl4AI,/' "$SCRAPER_PY"
        echo "Patched $SCRAPER_PY to include Crawl4AI scraper"
    fi
    if ! grep -q 'from .crawl4ai import' "$SCRAPER_PY"; then
        sed -i 's/from \.firecrawl import FireCrawl/from .crawl4ai import Crawl4AI\nfrom .firecrawl import FireCrawl/' "$SCRAPER_PY"
    fi
fi

# Patch default SCRAPER config
DEFAULT_CFG="$SITE_PKG/gpt_researcher/config/variables/default.py"
if [ -f "$DEFAULT_CFG" ]; then
    sed -i 's/"SCRAPER": "bs"/"SCRAPER": "crawl4ai"/' "$DEFAULT_CFG"
fi

exec "$@"