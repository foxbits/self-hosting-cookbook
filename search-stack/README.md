This is the docker compose setup for a web search stack, which includes [SearXNG](https://github.com/searxng/searxng) - the Internet metasearch engine, [crawl4ai](https://docs.crawl4ai.com/) - website crawler for LLMs

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
    - [API Endpoints for SearXNG](#api-endpoints-for-searxng)
    - [Categories available for SearXNG](#categories-available-for-searxng)
  - [MCP Server for Crawl4AI](#mcp-server-for-crawl4ai)
    - [API Endpoints for Crawl4AI](#api-endpoints-for-crawl4ai)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [The SearXNG Server](https://fusionauth.io/docs/get-started/download-and-install/docker) at port `9704`
- [crawl4ai](https://docs.crawl4ai.com/) at port `9705`

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


### Back-up

The configuration and data will be stored in these docker volumes: [`searxng-data`] and in these directories: [`./searxng/core-config`] - so this is what you have to back-up.
