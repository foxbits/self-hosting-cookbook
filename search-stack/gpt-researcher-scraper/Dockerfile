FROM gptresearcher/gpt-researcher:latest

RUN pip install --no-cache-dir openai

COPY gpt_researcher/scraper/crawl4ai/ /tmp/crawl4ai_scraper/
COPY gpt_researcher/llm_provider/image/openai_image_provider.py /tmp/openai_image_provider.py
COPY gpt_researcher/llm_provider/image/provider_factory.py /tmp/provider_factory.py
COPY gpt_researcher/llm_provider/image/__init__.py /tmp/image_provider_init.py
COPY entrypoint.sh /tmp/entrypoint.sh
COPY setup.py /tmp/setup.py

ENTRYPOINT ["/bin/bash", "/tmp/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]