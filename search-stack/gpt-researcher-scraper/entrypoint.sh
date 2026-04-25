#!/bin/bash
set -e

# Use user-level site-packages which is writable without sudo
USER_SITE=$(python -c "import site; print(site.getusersitepackages())")
SITE_PKG=$(python -c "import site; print(site.getsitepackages()[0])")

echo "User site packages: $USER_SITE"
echo "System site packages: $SITE_PKG"

# Create user site-packages dir if needed
mkdir -p "$USER_SITE"

# Install Crawl4AI scraper to user site-packages
CRAWL4AI_SRC="/tmp/crawl4ai_scraper"
if [ -d "$CRAWL4AI_SRC" ]; then
    # Create module directory in user site-packages
    CRAWL4AI_DEST="$USER_SITE/gpt_researcher/scraper/crawl4ai"
    mkdir -p "$CRAWL4AI_DEST"
    cp -r $CRAWL4AI_SRC/* "$CRAWL4AI_DEST/"
    echo "Installed Crawl4AI scraper to $CRAWL4AI_DEST"
fi

# Install OpenAI image provider to user site-packages
IMAGE_PROVIDER_SRC="/tmp"
if [ -f "$IMAGE_PROVIDER_SRC/openai_image_provider.py" ]; then
    IMAGE_PROVIDER_DEST="$USER_SITE/gpt_researcher/llm_provider/image"
    mkdir -p "$IMAGE_PROVIDER_DEST"
    cp "$IMAGE_PROVIDER_SRC/openai_image_provider.py" "$IMAGE_PROVIDER_DEST/"
    cp "$IMAGE_PROVIDER_SRC/provider_factory.py" "$IMAGE_PROVIDER_DEST/"
    if [ -f "$IMAGE_PROVIDER_SRC/image_provider_init.py" ]; then
        cp "$IMAGE_PROVIDER_SRC/image_provider_init.py" "$IMAGE_PROVIDER_DEST/__init__.py"
    fi
    echo "Installed OpenAI image provider to $IMAGE_PROVIDER_DEST"
fi

# Add user site-packages to PYTHONPATH so it takes precedence
export PYTHONPATH="$USER_SITE:$PYTHONPATH"
echo "PYTHONPATH=$PYTHONPATH"

exec "$@"