FROM gptresearcher/gpt-researcher:latest

# Install openai for image generation
RUN pip install --no-cache-dir openai

# Copy custom Crawl4AI scraper
COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/

# Copy custom image provider files
COPY gpt_researcher/llm_provider/image/ /tmp/custom_providers/image/

# Copy the patch script
COPY patch_scraper.py /tmp/patch_scraper.py

# Copy entrypoint script (will be executed via bash)
COPY entrypoint.sh /app/entrypoint.sh

# Use bash to run the entrypoint script (no chmod needed)
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
