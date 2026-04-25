#!/usr/bin/env python3
"""
Patch GPT Researcher's scraper module to register Crawl4AI.

Directly modifies /usr/src/app/gpt_researcher/scraper/:
1. Copies the crawl4ai scraper module
2. Patches __init__.py to import Crawl4AI and add to __all__
3. Patches scraper.py to add 'from .crawl4ai import Crawl4AI' after the existing import block
4. Adds "crawl4ai": Crawl4AI to SCRAPER_CLASSES dict
"""

import os
import shutil


def patch_scraper():
    base_path = "/usr/src/app/gpt_researcher/scraper"
    scraper_py = os.path.join(base_path, "scraper.py")
    crawl4ai_src = "/tmp/crawl4ai_scraper"

    print(f"Target: {base_path}")

    if not os.path.exists(scraper_py):
        print(f"ERROR: {scraper_py} not found")
        return False

    # Copy crawl4ai scraper
    crawl4ai_dest = os.path.join(base_path, "crawl4ai")
    if os.path.isdir(crawl4ai_src):
        if os.path.exists(crawl4ai_dest):
            shutil.rmtree(crawl4ai_dest)
        shutil.copytree(crawl4ai_src, crawl4ai_dest)
        print(f"✓ Copied crawl4ai scraper")
    else:
        print(f"ERROR: Source not found: {crawl4ai_src}")
        return False

    # Patch __init__.py
    init_py = os.path.join(base_path, "__init__.py")
    if os.path.exists(init_py):
        with open(init_py, "r") as f:
            init_content = f.read()

        if "crawl4ai" not in init_content:
            added = False
            if "from .firecrawl.firecrawl import FireCrawl" in init_content:
                init_content = init_content.replace(
                    "from .firecrawl.firecrawl import FireCrawl",
                    "from .firecrawl.firecrawl import FireCrawl\nfrom .crawl4ai.crawl4ai import Crawl4AI"
                )
                print("✓ Added Crawl4AI import to __init__.py")
                added = True

            if '"FireCrawl",' in init_content:
                init_content = init_content.replace(
                    '"FireCrawl",',
                    '"FireCrawl",\n    "Crawl4AI",'
                )
                print("✓ Added Crawl4AI to __all__ in __init__.py")

            if added:
                with open(init_py, "w") as f:
                    f.write(init_content)
            else:
                print("WARNING: Could not patch __init__.py (FireCrawl pattern not found)")
        else:
            print("✓ Crawl4AI already in __init__.py")

    # Patch scraper.py
    with open(scraper_py, "r") as f:
        content = f.read()

    # Add separate import line: "from .crawl4ai import Crawl4AI"
    if "from .crawl4ai import Crawl4AI" not in content:
        # Insert after the closing paren of the 'from . import (...)' block
        # Find the line with the closing paren followed by newline
        pattern = r'(from \. import\s*\([^)]*\))\n'
        replacement = r'\1\nfrom .crawl4ai import Crawl4AI\n'
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            print("✓ Added 'from .crawl4ai import Crawl4AI' to scraper.py")
        else:
            print("WARNING: Could not add Crawl4AI import line")
            print(f"First 300 chars:\n{content[:300]}")
            return False
    else:
        print("✓ Crawl4AI import already in scraper.py")

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
    print(f"✓ Patched scraper.py")
    return True


def patch_image_provider():
    image_base = "/usr/src/app/gpt_researcher/llm_provider/image"
    custom_src = "/tmp/custom_providers/image"

    if not os.path.exists(image_base):
        print(f"⚠ Image provider not found at {image_base}")
        return False

    if os.path.isdir(custom_src):
        for fname in os.listdir(custom_src):
            src = os.path.join(custom_src, fname)
            dst = os.path.join(image_base, fname)
            shutil.copy2(src, dst)
            print(f"✓ Copied {fname}")
    else:
        print(f"⚠ Custom image provider source not found at {custom_src}")
    return True


def verify():
    base_path = "/usr/src/app/gpt_researcher/scraper"
    scraper_py = os.path.join(base_path, "scraper.py")
    init_py = os.path.join(base_path, "__init__.py")
    crawl4ai_dir = os.path.join(base_path, "crawl4ai")

    errors = []

    if not os.path.exists(crawl4ai_dir):
        errors.append("crawl4ai/ directory missing")
    else:
        print("✓ crawl4ai/ directory exists")

    if os.path.exists(scraper_py):
        with open(scraper_py, 'r') as f:
            c = f.read()
            if "from .crawl4ai import Crawl4AI" not in c:
                errors.append("scraper.py missing 'from .crawl4ai import Crawl4AI'")
            else:
                print("✓ Import line for Crawl4AI in scraper.py")
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
        print("\n✗ VERIFICATION FAILED")
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
        exit(1)
    print("=== Done ===")


if __name__ == "__main__":
    main()
