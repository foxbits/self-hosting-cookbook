FROM gptresearcher/gpt-researcher:latest

# Install openai for image generation
RUN pip install --no-cache-dir openai

# Copy custom Crawl4AI scraper
COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/

# Copy custom image provider files
COPY gpt_researcher/llm_provider/image/ /tmp/custom_providers/image/

# Copy the patch script
COPY patch_scraper.py /tmp/patch_scraper.py

# Copy entrypoint to a persistent location
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
