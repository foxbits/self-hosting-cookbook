This is the docker compose setup for a web search stack, which includes [SearXNG](https://github.com/searxng/searxng) - the Internet metasearch engine, [crawl4ai](https://docs.crawl4ai.com/) - website crawler for LLMs, [GPT Researcher](https://github.com/assafelovic/gpt-researcher) - autonomous research agent backend

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
  - [GPT-Researcher Settings](#gpt-researcher-settings)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
    - [API Endpoints for SearXNG](#api-endpoints-for-searxng)
    - [Categories available for SearXNG](#categories-available-for-searxng)
  - [MCP Server for Crawl4AI](#mcp-server-for-crawl4ai)
    - [API Endpoints for Crawl4AI](#api-endpoints-for-crawl4ai)
  - [GPT Researcher Backend](#gpt-researcher-backend)
    - [API Endpoints for GPT Researcher](#api-endpoints-for-gpt-researcher)
    - [MCP Server for GPT Researcher](#mcp-server-for-gpt-researcher)
    - [Image Generation](#image-generation)
    - [Scraper Configuration](#scraper-configuration)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [The SearXNG Server](https://fusionauth.io/docs/get-started/download-and-install/docker) at port `9704`
- [crawl4ai](https://docs.crawl4ai.com/) at port `9705`
- [GPT Researcher](https://github.com/assafelovic/gpt-researcher) backend at port `9706`

This stack depends on an In-Memory Database (Valkey) and by default is configured to use a [`datastore-memory`](../datastore-memory/) instance already running on the same docker network (`home-lab-net`).

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `DEBUG`: searxng will log all the logs debug level if this is enabled, useful for troubleshooting
- `LIMITER_ENABLED`: The stack assumes that you will use it for personal use, therefore it disables the rate limiter. But you can enable it with this env var.
- `SEARXNG_INSTANCE_NAME`: The instance name that will be displayed in the SearXNG UI, if used
- `SEARXNG_BASE_URL`: the URL you will be accessing the SearXNG instance from a browser, it is usually either `http://localhost:9704` or `http://my-local-server-address:9704`. Service-to-service communication is not affected by this URL. It is not advisable to expose your instance publicly (or at least protect it with a reverse proxy with authentication)
- `LOCALE`: the language ISO code used by default in the SearXNG UI and results (e.g. `en`)
- `COUNTRY_CODE`: the country ISO code used by default by SearXNG results (e.g. `US`)
- `SEARXNG_SECRET_KEY`: A secret key for the cryptography of this instance - change it with a random value, e.g. generate it with  openssl rand -hex 32
- `WOLFRAM_API_KEY`: Go to https://developer.wolframalpha.com/access and create an account and an API key (Full Results API) if you want to use Wolfram Alpha as source as well (the API is limited on the free tier). Otherwise, leave `WOLFRAM_DISABLED` as `true`.
- `MAX_CONCURRENT_TASKS`: Depends on the allowed number of concurrent tasks for a crawl, number must be considered with the formula agent count x parallel tasks x 150MB depending on the RAM you allocate and the number of agents you plan to use. Default is 10.

### GPT-Researcher Settings

- `OPENAI_API_KEY`: API key for the LLM provider (required)
- `OPENAI_BASE_URL`: Base URL for the LLM API (default: `https://nano-gpt.com/api/v1`)
- `SCRAPER`: Web scraper method - `bs` (BeautifulSoup), `browser` (Selenium), `nodriver` (ZenDriver), `firecrawl`, `tavily_extract`, **`crawl4ai`** (local Crawl4AI, **default in this stack**)
- `CRAWL4AI_API_URL`: URL of the Crawl4AI service (default: `http://crawl4ai:11235`, for host access use `http://localhost:9705`)
- `IMAGE_GENERATION_ENABLED`: Enable AI-generated inline images (`true`/`false`, default: `false`)
- `IMAGE_GENERATION_PROVIDER`: Image generation provider - `google` (official Google API) or `openai` (OpenAI-compatible custom URL)
- `GOOGLE_API_KEY`: Google API key for image generation (required if `IMAGE_GENERATION_PROVIDER=google`)
- `IMAGE_API_KEY`: API key for OpenAI-compatible image generation (uses `OPENAI_API_KEY` as fallback)
- `IMAGE_GENERATION_BASE_URL`: Base URL for OpenAI-compatible image generation (e.g., `https://nano-gpt.com/api/v1/images/generations`)
- `IMAGE_GENERATION_MODEL`: Model for image generation (Gemini model when `google`, DALL-E model when `openai`)
- `IMAGE_GENERATION_MAX_IMAGES`: Maximum images per report (default: 3)


## Running

### Pre-requisites

The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).

This stack depends on an In-Memory Database (Valkey) and by default is configured to use a [`datastore-memory`](../datastore-memory/) instance already running on the same docker network (`home-lab-net`), so that needs to be configured first.

On the first run, the stack will generate a `settings.yml` file in `searxng/core-config` directory, based on the default configuration and environment variables. On subsequent runs, if you want to change the config file (you should not need to), you need to delete the existing `settings.yml` file and allow the `run` command to run as `sudo` since it needs to take ownership of the directory containing it.

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

SearXNG will be available at [http://localhost:9704](http://localhost:9704) (or your specific `SEARXNG_BASE_URL`), or with [http://searxng:8080](http://searxng:8080) in `home-lab-net`

Crawl4AI will be available at [http://localhost:9705](http://localhost:9705), or with [http://crawl4ai:11235](http://crawl4ai:11235) in `home-lab-net`

GPT Researcher will be available at [http://localhost:9706](http://localhost:9706), or with [http://gpt-researcher:8000](http://gpt-researcher:8000) in `home-lab-net`

#### API Endpoints for SearXNG

| Endpoint | Description | Format |
|----------|-----------|--------|
| `GET /search?q=QUERY&format=json` | Search | JSON |
| `GET /search?q=QUERY&format=json&categories=news` | News | JSON |
| `GET /search?q=QUERY&format=rss&categories=news` | News RSS feed | RSS/XML |
| `GET /search?q=QUERY&format=json&categories=social` | Social | JSON |
| `GET /search?q=QUERY&format=json&categories=science` | Academic | JSON |
| `GET /search?q=QUERY&format=json&categories=finance` | Finance | JSON |
| `GET /search?q=QUERY&format=json&categories=code` | Code | JSON |
| `GET /search?q=QUERY&format=json&categories=it` | IT | JSON |

#### Categories available for SearXNG

- `general` — web search (Google, Brave, Duck Duck Go, optionally Bing)
- `news` — News (Google News, Brave News, Bing News)
- `science` — academic (Google Scholar, Semantic Scholar, arXiv, PubMed)
- `social` — social media (Reddit, Mastodon, Lemmy, Tootfinder)
- `financial` - Reuters, Brave News (Finance), Duck Duck Go Finance News, Currency Converter, Wolfram Alpha (Optional)
- `code` & `it` — source code (GitHub, StackOverflow), forums (StackExchange, SuperUser)

### MCP Server for Crawl4AI

The Crawl4AI server exposes two MCP endpoints:
- Server-Sent Events (SSE): http://localhost:11235/mcp/sse
- WebSocket: ws://localhost:11235/mcp/ws

Example to add the SSE endpoint as MCP server:
`mcp add --transport sse c4ai-sse http://localhost:9705/mcp/sse`

#### API Endpoints for Crawl4AI

For full details see [their official documentation](https://docs.crawl4ai.com/core/self-hosting/#mcp-model-context-protocol-support).

| Endpoint | Description | Format |
|----------|-----------|--------|
| `GET /playground` | Playground website to test, use in browser | Application |
| `POST /crawl { urls: [] }` | The default crawl endpoint, crawls media, html and markdown | Markdown |
| `POST /md { url: [] }` | The default crawl endpoint, crawls media, html and markdown | Markdown |
| `POST /html` { url: "" } | Crawls the content as HTML | HTML |
| `POST /screenshot` { url: "" } | Crawls the content as HTML | HTML |
| `POST /pdf` { url: "" } | Crawls the content as PDF | PDF |
| `POST /execute_js` { url: "", scripts: [""] } | Execute JS on the page | Markdown |

For dynamic websites, add in the request body:
```
"crawler_config": {
    "wait_until": "networkidle"
  }
```

For the `/md` request, use `"f": "raw"` in the body to get the unfit markdown (sometimes the fitting process strips wrong parts of websites, even important ones).
For the `/crawl` request, you can let the agent use the `raw_markdown` content, which is the unfit one and contains also links to media (separately, media is also in the `media` object).


### GPT Researcher Backend

GPT Researcher is an autonomous agent that conducts deep research on any topic using LLM providers. The backend exposes REST API endpoints and an MCP server for integration with other AI assistants.

#### API Endpoints for GPT Researcher

For full details see [the official documentation](https://docs.gptr.dev/docs/gpt-researcher/gptr/querying-the-backend).

| Endpoint | Description | Format |
|----------|-------------|--------|
| `GET /health` | Health check | JSON |
| `POST /research` `{ query: "", report_type: "research_report" }` | Conduct autonomous research | JSON |
| `POST /report` `{ query: "", report_type: "research_report" }` | Generate research report | JSON/Markdown |
| `GET /outputs/` | Access generated reports | File |

#### MCP Server for GPT Researcher

The GPT Researcher backend exposes an MCP server for AI assistants to perform deep research:

- Server-Sent Events (SSE): `http://localhost:9706/mcp/sse`
- WebSocket: `ws://localhost:9706/mcp/ws`

Example to add as MCP server:
```
mcp add --transport sse gpt-researcher http://localhost:9706/mcp/sse
```

The MCP server provides:
- `deep_research` - Perform autonomous web research
- `quick_search` - Fast web search
- `write_report` - Generate a report from research
- `get_research_sources` - Get sources used in research
- `get_research_context` - Get full research context

#### Image Generation

Image generation is optional and can use either Google Gemini API or an OpenAI-compatible API.

**Google Gemini API:**
1. Set `IMAGE_GENERATION_PROVIDER=google`
2. Set `IMAGE_GENERATION_ENABLED=true`
3. Provide `GOOGLE_API_KEY`

**OpenAI-compatible API (e.g., nano-gpt.com) (default):**
1. Set `IMAGE_GENERATION_PROVIDER=openai`
2. Set `IMAGE_GENERATION_ENABLED=true`
3. Provide `IMAGE_API_KEY` (or `OPENAI_API_KEY` as fallback)
4. Provide `IMAGE_GENERATION_BASE_URL` (e.g., `https://nano-gpt.com/api/v1/images/generations`)
5. Set `IMAGE_GENERATION_MODEL` to a model supported by your provider (e.g., `dall-e-3`)

#### Scraper Configuration

The scraper is configurable via the `SCRAPER` environment variable:

- `bs` - BeautifulSoup (static) - no additional setup
- `browser` - Selenium (dynamic) - requires WebDriver setup
- `nodriver` - NoDriver/ZenDriver (dynamic) - requires `pip install zendriver`
- `firecrawl` - FireCrawl - requires API key and `pip install firecrawl-py`
- `tavily_extract` - Tavily Extract - requires API key and `pip install tavily-python`
- `crawl4ai` - **Local Crawl4AI** (default in this stack, no API key needed) - uses the Crawl4AI service running on port `9705`


### Back-up

The configuration and data will be stored in these docker volumes: [`searxng-data`], [`gpt-researcher-data`] and in these directories: [`./searxng/core-config`] - so this is what you have to back-up.
