FROM gptresearcher/gpt-researcher:latest

COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN python -c "
import site
import os
import shutil

site_packages = site.getsitepackages()[0]
dest_dir = os.path.join(site_packages, 'gpt_researcher', 'scraper', 'crawl4ai')
os.makedirs(dest_dir, exist_ok=True)

src = '/tmp/crawl4ai_scraper'
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), dest_dir)

print(f'Installed Crawl4AI scraper to {dest_dir}')
"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]