#!/usr/bin/env python3
"""
Patch GPT Researcher's scraper module to register Crawl4AI.

Locates the installed gpt_researcher package and patches:
1. scraper/__init__.py - adds Crawl4AI import and __all__ entry
2. scraper/scraper.py - adds Crawl4AI to from . import (...) and SCRAPER_CLASSES
"""

import importlib
import os
import re
import shutil
import site
import sys


def find_gpt_researcher():
    """Find the installed location of gpt_researcher package."""
    try:
        import gpt_researcher
        return os.path.dirname(gpt_researcher.__file__)
    except ImportError:
        pass

    for sp in site.getsitepackages():
        candidate = os.path.join(sp, "gpt_researcher")
        if os.path.isdir(candidate):
            return candidate

    user_site = site.getusersitepackages()
    candidate = os.path.join(user_site, "gpt_researcher")
    if os.path.isdir(candidate):
        return candidate

    candidate = "/usr/src/app/gpt_researcher"
    if os.path.isdir(candidate):
        return candidate

    return None


def patch_init(base_path):
    """Patch __init__.py to import Crawl4AI and add to __all__."""
    init_py = os.path.join(base_path, "__init__.py")
    if not os.path.exists(init_py):
        print(f"WARNING: {init_py} not found")
        return

    with open(init_py, "r") as f:
        content = f.read()

    if "crawl4ai" in content:
        print("Crawl4AI already in __init__.py")
        return

    # Add import after FireCrawl
    if "from .firecrawl.firecrawl import FireCrawl" not in content:
        print("WARNING: Could not find FireCrawl import in __init__.py")
        return

    content = content.replace(
        "from .firecrawl.firecrawl import FireCrawl",
        "from .firecrawl.firecrawl import FireCrawl\nfrom .crawl4ai.crawl4ai import Crawl4AI"
    )
    print("Added Crawl4AI import to __init__.py")

    # Add to __all__ after FireCrawl
    if '"FireCrawl",' not in content:
        print("WARNING: Could not find FireCrawl in __all__")
    else:
        content = content.replace(
            '"FireCrawl",',
            '"FireCrawl",\n    "Crawl4AI",'
        )
        print("Added Crawl4AI to __all__ in __init__.py")

    with open(init_py, "w") as f:
        f.write(content)


def patch_scraper():
    gpt_root = find_gpt_researcher()
    if not gpt_root:
        print("ERROR: Could not find gpt_researcher package")
        return False

    base_path = os.path.join(gpt_root, "scraper")
    scraper_py = os.path.join(base_path, "scraper.py")
    crawl4ai_src = "/tmp/crawl4ai_scraper"

    print(f"GPT Researcher root: {gpt_root}")
    print(f"Scraper path: {base_path}")

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

    # Patch __init__.py
    patch_init(base_path)

    # Read scraper.py
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
            print("Added Crawl4AI to from . import block")
        else:
            print("WARNING: Could not patch import block with regex")
            print(f"First 300 chars:\n{content[:300]}")
            return False
    else:
        print("Crawl4AI already in imports")

    # Add to SCRAPER_CLASSES
    if '"crawl4ai"' not in content:
        content = content.replace(
            '"firecrawl": FireCrawl,',
            '"firecrawl": FireCrawl,\n            "crawl4ai": Crawl4AI,'
        )
        if '"crawl4ai": Crawl4AI' in content:
            print("Added crawl4ai to SCRAPER_CLASSES")
        else:
            print("WARNING: Could not add Crawl4AI to SCRAPER_CLASSES")
            return False
    else:
        print("crawl4ai already in SCRAPER_CLASSES")

    with open(scraper_py, "w") as f:
        f.write(content)
    print(f"Patched {scraper_py}")
    return True


def patch_image_provider():
    gpt_root = find_gpt_researcher()
    if not gpt_root:
        print("WARNING: Cannot find gpt_researcher for image provider patching")
        return False

    image_base = os.path.join(gpt_root, "llm_provider", "image")
    custom_src = "/tmp/custom_providers/image"

    if not os.path.exists(image_base):
        print(f"WARNING: Image provider directory not found at {image_base}")
        return False

    if os.path.isdir(custom_src):
        for fname in os.listdir(custom_src):
            src = os.path.join(custom_src, fname)
            dst = os.path.join(image_base, fname)
            shutil.copy2(src, dst)
            print(f"Copied {fname} to {image_base}")

    return True


def verify():
    gpt_root = find_gpt_researcher()
    if not gpt_root:
        print("WARNING: Cannot verify - gpt_researcher not found")
        return False

    base_path = os.path.join(gpt_root, "scraper")
    scraper_py = os.path.join(base_path, "scraper.py")
    init_py = os.path.join(base_path, "__init__.py")
    crawl4ai_dir = os.path.join(base_path, "crawl4ai")

    errors = []

    if not os.path.exists(crawl4ai_dir):
        errors.append("crawl4ai directory not found")
    else:
        print(f"✓ Crawl4AI directory exists")

    if os.path.exists(scraper_py):
        with open(scraper_py, 'r') as f:
            content = f.read()
            if "from .crawl4ai import Crawl4AI" not in content:
                errors.append("scraper.py missing Crawl4AI import")
            else:
                print("✓ Crawl4AI import in scraper.py")
            if '"crawl4ai": Crawl4AI' not in content:
                errors.append("scraper.py missing Crawl4AI in SCRAPER_CLASSES")
            else:
                print("✓ Crawl4AI in SCRAPER_CLASSES")

    if os.path.exists(init_py):
        with open(init_py, 'r') as f:
            init_content = f.read()
            if "from .crawl4ai.crawl4ai import Crawl4AI" not in init_content:
                errors.append("__init__.py missing Crawl4AI import")
            else:
                print("✓ Crawl4AI import in __init__.py")
            if '"Crawl4AI"' not in init_content:
                errors.append("__init__.py missing Crawl4AI in __all__")
            else:
                print("✓ Crawl4AI in __all__")

    if errors:
        print("\n✗ VERIFICATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("\n✓✓✓ All checks passed! Crawl4AI scraper is properly registered.")
        return True


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
