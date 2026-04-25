FROM gptresearcher/gpt-researcher:latest

RUN pip install --no-cache-dir openai

COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/
COPY gpt_researcher/llm_provider/image/openai_image_provider.py /tmp/openai_image_provider.py
COPY gpt_researcher/llm_provider/image/provider_factory.py /tmp/provider_factory.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN python -c "
import site
import os
import shutil

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
"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]