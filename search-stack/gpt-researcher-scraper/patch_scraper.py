#!/usr/bin/env python3
"""
Patch GPT Researcher's scraper module to register Crawl4AI.

Directly modifies the installed gpt_researcher code at /usr/src/app
which is where the Docker container places the application code.
"""

import os
import re
import shutil


def patch_scraper():
    base_path = "/usr/src/app/gpt_researcher/scraper"
    scraper_py = os.path.join(base_path, "scraper.py")
    crawl4ai_src = "/tmp/crawl4ai_scraper"

    print(f"Target scraper directory: {base_path}")

    # Verify scraper.py exists
    if not os.path.exists(scraper_py):
        print(f"ERROR: {scraper_py} not found")
        return False

    # Copy crawl4ai scraper to target
    crawl4ai_dest = os.path.join(base_path, "crawl4ai")
    if os.path.isdir(crawl4ai_src):
        if os.path.exists(crawl4ai_dest):
            shutil.rmtree(crawl4ai_dest)
        shutil.copytree(crawl4ai_src, crawl4ai_dest)
        print(f"✓ Copied Crawl4AI scraper to {crawl4ai_dest}")
    else:
        print(f"WARNING: Crawl4AI source not found at {crawl4ai_src}")
        return False

    # Patch __init__.py
    init_py = os.path.join(base_path, "__init__.py")
    if os.path.exists(init_py):
        with open(init_py, "r") as f:
            init_content = f.read()

        if "crawl4ai" not in init_content:
            # Add import after FireCrawl
            if "from .firecrawl.firecrawl import FireCrawl" in init_content:
                init_content = init_content.replace(
                    "from .firecrawl.firecrawl import FireCrawl",
                    "from .firecrawl.firecrawl import FireCrawl\nfrom .crawl4ai.crawl4ai import Crawl4AI"
                )
                print("✓ Added Crawl4AI import to __init__.py")

            # Add to __all__ after FireCrawl
            if '"FireCrawl",' in init_content:
                init_content = init_content.replace(
                    '"FireCrawl",',
                    '"FireCrawl",\n    "Crawl4AI",'
                )
                print("✓ Added Crawl4AI to __all__ in __init__.py")

            with open(init_py, "w") as f:
                f.write(init_content)
        else:
            print("✓ Crawl4AI already in __init__.py")
    else:
        print(f"WARNING: {init_py} not found")

    # Patch scraper.py
    with open(scraper_py, "r") as f:
        content = f.read()

    # Add Crawl4AI to 'from . import (...)' using regex
    if "Crawl4AI" not in content:
        pattern = r'(from \. import\s*\([^)]*?)\)(\s*\n)'

        def add_crawl4ai(match):
            inner_with_paren = match.group(1)
            newline = match.group(2)
            inner_items = inner_with_paren[inner_with_paren.index('(')+1:]
            inner_stripped = inner_items.rstrip()
            if inner_stripped.endswith(','):
                new_inner = inner_items + '    Crawl4AI,'
            else:
                lines = inner_stripped.split('\n')
                lines[-1] = lines[-1] + ','
                new_inner = '\n'.join(lines) + '\n    Crawl4AI'
            return 'from . import (' + new_inner + ')' + newline

        new_content = re.sub(pattern, add_crawl4ai, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            print("✓ Added Crawl4AI to 'from . import' block")
        else:
            print("WARNING: Could not patch import block")
            return False
    else:
        print("✓ Crawl4AI already in imports")

    # Add to SCRAPER_CLASSES
    if '"crawl4ai"' not in content:
        content = content.replace(
            '"firecrawl": FireCrawl,',
            '"firecrawl": FireCrawl,\n            "crawl4ai": Crawl4AI,'
        )
        if '"crawl4ai": Crawl4AI' not in content:
            print("WARNING: Could not add Crawl4AI to SCRAPER_CLASSES")
            return False
        print("✓ Added Crawl4AI to SCRAPER_CLASSES")
    else:
        print("✓ Crawl4AI already in SCRAPER_CLASSES")

    with open(scraper_py, "w") as f:
        f.write(content)

    print(f"✓ Patched {scraper_py}")
    return True


def patch_image_provider():
    """Patch image provider module."""
    image_base = "/usr/src/app/gpt_researcher/llm_provider/image"
    custom_src = "/tmp/custom_providers/image"

    if not os.path.exists(image_base):
        print(f"WARNING: Image provider directory not found at {image_base}")
        return False

    if os.path.isdir(custom_src):
        for fname in os.listdir(custom_src):
            src = os.path.join(custom_src, fname)
            dst = os.path.join(image_base, fname)
            shutil.copy2(src, dst)
            print(f"✓ Copied {fname} to image provider")
    return True


def verify():
    """Verify patches are in place."""
    base_path = "/usr/src/app/gpt_researcher/scraper"
    scraper_py = os.path.join(base_path, "scraper.py")
    init_py = os.path.join(base_path, "__init__.py")
    crawl4ai_dir = os.path.join(base_path, "crawl4ai")

    errors = []

    if not os.path.exists(crawl4ai_dir):
        errors.append("crawl4ai directory not found")
    else:
        print("✓ crawl4ai directory in place")

    if os.path.exists(scraper_py):
        with open(scraper_py, 'r') as f:
            c = f.read()
            if "from .crawl4ai import Crawl4AI" not in c:
                errors.append("scraper.py missing Crawl4AI import")
            else:
                print("✓ Crawl4AI import in scraper.py")
            if '"crawl4ai": Crawl4AI' not in c:
                errors.append("scraper.py missing Crawl4AI in SCRAPER_CLASSES")
            else:
                print("✓ Crawl4AI in SCRAPER_CLASSES")

    if os.path.exists(init_py):
        with open(init_py, 'r') as f:
            c = f.read()
            if "from .crawl4ai.crawl4ai import Crawl4AI" not in c:
                errors.append("__init__.py missing Crawl4AI import")
            else:
                print("✓ Crawl4AI import in __init__.py")
            if '"Crawl4AI"' not in c:
                errors.append("__init__.py missing Crawl4AI in __all__")
            else:
                print("✓ Crawl4AI in __all__")

    if errors:
        print("\n✗ VERIFICATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("\n✓✓✓ All patches verified!")
        return True


def main():
    print("=== Patching GPT Researcher ===")
    if patch_scraper():
        patch_image_provider()
        verify()
    else:
        print("✗ Patching failed")
    print("=== Done ===")


if __name__ == "__main__":
    main()
