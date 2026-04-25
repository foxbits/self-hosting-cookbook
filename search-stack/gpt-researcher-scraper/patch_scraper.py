#!/usr/bin/env python3
"""
Patch GPT Researcher's scraper module to register Crawl4AI.

The approach is to directly modify the installed gpt_researcher code at /usr/src/app
which is where the Docker container places the application code.

We:
1. Copy the crawl4ai scraper to the scraper directory
2. Patch scraper/__init__.py to add Crawl4AI import and to __all__
3. Patch scraper/scraper.py to add Crawl4AI to the 'from . import (...)' block
4. Patch scraper/scraper.py to add "crawl4ai": Crawl4AI to SCRAPER_CLASSES dict
"""

import os
import shutil


def patch_init(base_path):
    """Patch __init__.py to import Crawl4AI (same pattern as FireCrawl)."""
    init_py = os.path.join(base_path, "__init__.py")
    if not os.path.exists(init_py):
        print(f"WARNING: {init_py} not found")
        return

    with open(init_py, "r") as f:
        content = f.read()

    if "crawl4ai" in content:
        print("Crawl4AI already in __init__.py")
        return

    # Add import for Crawl4AI after FireCrawl import (same pattern as other scrapers)
    if "from .firecrawl.firecrawl import FireCrawl" in content:
        content = content.replace(
            "from .firecrawl.firecrawl import FireCrawl",
            "from .firecrawl.firecrawl import FireCrawl\nfrom .crawl4ai.crawl4ai import Crawl4AI"
        )
        print("Added Crawl4AI import to __init__.py")
    else:
        print("WARNING: Could not find FireCrawl import in __init__.py")
        return

    # Add to __all__ list after FireCrawl
    if '"FireCrawl",' in content:
        content = content.replace(
            '"FireCrawl",',
            '"FireCrawl",\n    "Crawl4AI",'
        )
        print("Added Crawl4AI to __all__ in __init__.py")
    else:
        print("WARNING: Could not find FireCrawl in __all__")

    with open(init_py, "w") as f:
        f.write(content)


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

    # Patch __init__.py first
    patch_init(base_path)

    # Read scraper.py
    with open(scraper_py, "r") as f:
        content = f.read()

    # Add Crawl4AI to the 'from . import (...)' block using regex
    if "Crawl4AI" not in content:
        import re

        # Find: from . import ( ... ) including any content inside (non-greedy match)
        pattern = r'(from \. import\s*\([^)]*?)\)(\s*\n)'
        
        def add_crawl4ai(match):
            full_match = match.group(0)
            inner_with_paren = match.group(1)  # "from . import ( ...items..."
            newline = match.group(2)
            
            # Extract just the items inside the parens
            inner_items = inner_with_paren[inner_with_paren.index('(')+1:]
            
            # Capitalize: add "    Crawl4AI," before the closing paren
            # Check if inner_items ends with comma or not
            inner_items_stripped = inner_items.rstrip()
            if inner_items_stripped.endswith(','):
                new_inner = inner_items + '    Crawl4AI,'
            else:
                # Add comma to last line
                lines = inner_items_stripped.split('\n')
                lines[-1] = lines[-1] + ','
                new_inner = '\n'.join(lines) + '\n    Crawl4AI'
            
            # Reconstruct: from . import ( items... ) + newline
            return 'from . import (' + new_inner + ')' + newline

        new_content = re.sub(pattern, add_crawl4ai, content, flags=re.DOTALL)
        
        if new_content != content:
            content = new_content
            print("Added Crawl4AI to from . import block using regex")
        else:
            print("WARNING: Could not patch import block with regex")
            print(f"Pattern did not match - showing first 500 chars of file:\n{content[:500]}")
            return False
    else:
        print("Crawl4AI already in scraper.py imports")

    # Add to SCRAPER_CLASSES dict
    if '"crawl4ai"' not in content:
        # Add entry after firecrawl
        content = content.replace(
            '"firecrawl": FireCrawl,',
            '"firecrawl": FireCrawl,\n            "crawl4ai": Crawl4AI,'
        )
        if '"crawl4ai": Crawl4AI' in content:
            print("Added crawl4ai to SCRAPER_CLASSES")
        else:
            print("WARNING: Could not add crawl4ai to SCRAPER_CLASSES")
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
        import traceback
        traceback.print_exc()
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
