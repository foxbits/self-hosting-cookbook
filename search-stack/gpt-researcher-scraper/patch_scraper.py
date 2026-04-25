#!/usr/bin/env python3
"""
Patch GPT Researcher's scraper module to register Crawl4AI.

The approach is to directly modify the installed gpt_researcher code at /usr/src/app
which is where the Docker container places the application code.

We:
1. Copy the crawl4ai scraper to the scraper directory
2. Patch scraper.py to:
   a. Add "from .crawl4ai import Crawl4AI" to the imports
   b. Add "crawl4ai": Crawl4AI to the SCRAPER_CLASSES dict inside get_scraper()
"""

import os
import shutil


def patch_scraper():
    base_path = "/usr/src/app/gpt_researcher/scraper"
    scraper_py = os.path.join(base_path, "scraper.py")
    crawl4ai_src = "/tmp/crawl4ai_scraper"

    if not os.path.exists(scraper_py):
        print(f"ERROR: {scraper_py} not found")
        return False

    # Copy crawl4ai scraper
    crawl4ai_dest = os.path.join(base_path, "crawl4ai")
    if os.path.isdir(crawl4ai_src):
        if os.path.exists(crawl4ai_dest):
            shutil.rmtree(crawl4ai_dest)
        shutil.copytree(crawl4ai_src, crawl4ai_dest)
        print(f"Copied Crawl4AI scraper to {crawl4ai_dest}")
    else:
        print(f"WARNING: Crawl4AI source not found at {crawl4ai_src}")

    # Read scraper.py
    with open(scraper_py, "r") as f:
        content = f.read()

    # Add import for Crawl4AI
    if "crawl4ai" not in content:
        import re

        # Match "from . import (" block and add Crawl4AI before the closing parenthesis
        # This regex matches: from . import ( ... ) capturing the content inside
        pattern = r'(from \. import \([^)]*?)(\s*\))'

        def add_crawl4ai_import(match):
            existing = match.group(1)
            closing = match.group(2)
            # Check if there's already a trailing comma
            if existing.rstrip().endswith(','):
                return existing + '\n    Crawl4AI,' + closing
            else:
                # Add comma to last item if needed, then add Crawl4AI
                stripped = existing.rstrip()
                if stripped and not stripped.endswith(','):
                    existing = stripped + ',\n'
                return existing + '    Crawl4AI,' + closing

        new_content = re.sub(pattern, add_crawl4ai_import, content, flags=re.DOTALL)

        if new_content != content:
            content = new_content
            print("Added Crawl4AI to imports using regex")
        else:
            print("WARNING: Could not find import section to patch with regex")
    else:
        print("Crawl4AI already imported")

    # Add to SCRAPER_CLASSES dict
    if '"crawl4ai"' not in content and "'crawl4ai'" not in content:
        # Find SCRAPER_CLASSES dict inside get_scraper and add crawl4ai entry
        old_dict = '''        SCRAPER_CLASSES = {
            "pdf": PyMuPDFScraper,
            "arxiv": ArxivScraper,
            "bs": BeautifulSoupScraper,
            "web_base_loader": WebBaseLoaderScraper,
            "browser": BrowserScraper,
            "nodriver": NoDriverScraper,
            "tavily_extract": TavilyExtract,
            "firecrawl": FireCrawl,
        }'''

        new_dict = '''        SCRAPER_CLASSES = {
            "pdf": PyMuPDFScraper,
            "arxiv": ArxivScraper,
            "bs": BeautifulSoupScraper,
            "web_base_loader": WebBaseLoaderScraper,
            "browser": BrowserScraper,
            "nodriver": NoDriverScraper,
            "tavily_extract": TavilyExtract,
            "firecrawl": FireCrawl,
            "crawl4ai": Crawl4AI,
        }'''

        if old_dict in content:
            content = content.replace(old_dict, new_dict)
            print("Added crawl4ai to SCRAPER_CLASSES")
        else:
            # Try to find and patch the dict more flexibly
            if "\"firecrawl\": FireCrawl," in content:
                content = content.replace(
                    '"firecrawl": FireCrawl,',
                    '"firecrawl": FireCrawl,\n            "crawl4ai": Crawl4AI,'
                )
                print("Added crawl4ai to SCRAPER_CLASSES (inline)")
            else:
                print("WARNING: Could not find SCRAPER_CLASSES dict to patch")
    else:
        print("crawl4ai already in SCRAPER_CLASSES")

    # Write back
    with open(scraper_py, "w") as f:
        f.write(content)
    print(f"Patched {scraper_py}")

    return True


def patch_image_provider():
    image_base = "/usr/src/app/gpt_researcher/llm_provider/image"
    custom_src = "/tmp/custom_providers/image"

    if not os.path.exists(image_base):
        print(f"WARNING: Image provider directory not found at {image_base}")
        return False

    # Copy custom provider files
    if os.path.isdir(custom_src):
        for fname in os.listdir(custom_src):
            src = os.path.join(custom_src, fname)
            dst = os.path.join(image_base, fname)
            shutil.copy2(src, dst)
            print(f"Copied {fname} to {image_base}")

    return True


def verify():
    try:
        from gpt_researcher.scraper.scraper import Scraper
        s = Scraper([], "test-agent", "crawl4ai", None)
        scraper_class = s.get_scraper("http://example.com")
        print(f"SUCCESS: crawl4ai scraper loaded: {scraper_class.__name__}")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False


def main():
    print("=== Patching GPT Researcher ===")

    success = patch_scraper()
    if success:
        patch_image_provider()
        verify()
    else:
        print("Scraper patching failed, skipping image provider")

    print("=== Done ===")


if __name__ == "__main__":
    main()
