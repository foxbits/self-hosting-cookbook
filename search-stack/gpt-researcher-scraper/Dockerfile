FROM gptresearcher/gpt-researcher:latest

RUN pip install --no-cache-dir openai

COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/
COPY gpt_researcher/llm_provider/image/openai_image_provider.py /tmp/openai_image_provider.py
COPY gpt_researcher/llm_provider/image/provider_factory.py /tmp/provider_factory.py
COPY entrypoint.sh /tmp/entrypoint.sh
COPY setup.py /tmp/setup.py

RUN python /tmp/setup.py

ENTRYPOINT ["/tmp/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]