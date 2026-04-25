#!/usr/bin/env python3
"""Setup script to install custom providers into GPT Researcher."""

import os
import shutil
import site


def main():
    site_packages = site.getsitepackages()[0]

    # Install Crawl4AI scraper
    scraper_dir = os.path.join(site_packages, 'gpt_researcher', 'scraper', 'crawl4ai')
    os.makedirs(scraper_dir, exist_ok=True)
    src = '/tmp/crawl4ai_scraper'
    for f in os.listdir(src):
        shutil.copy(os.path.join(src, f), scraper_dir)
    print(f'Installed Crawl4AI scraper to {scraper_dir}')

    # Install OpenAI image provider
    image_provider_dir = os.path.join(site_packages, 'gpt_researcher', 'llm_provider', 'image')
    os.makedirs(image_provider_dir, exist_ok=True)
    shutil.copy('/tmp/openai_image_provider.py', image_provider_dir)
    shutil.copy('/tmp/provider_factory.py', image_provider_dir)
    print(f'Installed OpenAI image provider to {image_provider_dir}')


if __name__ == '__main__':
    main()