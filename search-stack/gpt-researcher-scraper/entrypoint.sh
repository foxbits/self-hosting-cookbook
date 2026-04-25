#!/bin/bash
set -e

# Patch SCRAPER_CLASSES to include Crawl4AI
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

# Patch default SCRAPER config
DEFAULT_CFG=$(python -c "import site; print(site.getsitepackages()[0])")/gpt_researcher/config/variables/default.py
if [ -f "$DEFAULT_CFG" ]; then
    sed -i 's/"SCRAPER": "bs"/"SCRAPER": "crawl4ai"/' "$DEFAULT_CFG"
fi

# Patch image provider to include OpenAIImageProvider and add IMAGE_GENERATION_PROVIDER support
SITE_PKG=$(python -c "import site; print(site.getsitepackages()[0])")
IMAGE_PROVIDER_DIR=$SITE_PKG/gpt_researcher/llm_provider/image

if [ -d "$IMAGE_PROVIDER_DIR" ]; then
    # Copy our custom OpenAIImageProvider to the site-packages
    if [ -f "/tmp/openai_image_provider.py" ]; then
        cp /tmp/openai_image_provider.py $IMAGE_PROVIDER_DIR/openai_image_provider.py
        echo "Installed OpenAIImageProvider to $IMAGE_PROVIDER_DIR"
    fi

    if [ -f "/tmp/provider_factory.py" ]; then
        cp /tmp/provider_factory.py $IMAGE_PROVIDER_DIR/provider_factory.py
        echo "Installed provider_factory to $IMAGE_PROVIDER_DIR"
    fi

    # Patch __init__.py to export OpenAIImageProvider
    INIT_PY=$IMAGE_PROVIDER_DIR/__init__.py
    if [ -f "$INIT_PY" ]; then
        if ! grep -q 'OpenAIImageProvider' "$INIT_PY"; then
            sed -i 's/from \.image_generator import ImageGeneratorProvider/from .image_generator import ImageGeneratorProvider\nfrom .openai_image_provider import OpenAIImageProvider/' "$INIT_PY"
            sed -i 's/__all__ = \["ImageGeneratorProvider"\]/__all__ = ["ImageGeneratorProvider", "OpenAIImageProvider"]/' "$INIT_PY"
            echo "Patched $INIT_PY to include OpenAIImageProvider"
        fi
    fi
fi

exec "$@"