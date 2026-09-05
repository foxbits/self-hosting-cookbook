This is the docker compose setup for a web search stack, which includes [SearXNG](https://github.com/searxng/searxng) - the Internet metasearch engine, [crawl4ai](https://docs.crawl4ai.com/) - website crawler for LLMs, [GPT Researcher](https://github.com/assafelovic/gpt-researcher) - autonomous research agent backend, [camofox-browser](https://github.com/jo-inc/camofox-browser) - anti-detection browser for agents (Camoufox engine) with native locale/timezone/geolocation identifiers matching the home residential IP

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
  - [Camofox Browser](#camofox-browser)
    - [Browser identity (locale/timezone/geolocation)](#browser-identity-localetimezonegeolocation)
    - [API Endpoints for Camofox](#api-endpoints-for-camofox)
    - [Verifying the setup (Postman walkthrough)](#verifying-the-setup-postman-walkthrough)
    - [Importing browser cookies](#importing-browser-cookies)
  - [crw (Firecrawl-compatible scrape/search)](#crw-firecrawl-compatible-scrapesearch)
    - [API Endpoints for crw](#api-endpoints-for-crw)
    - [Camofox integration and limits](#camofox-integration-and-limits)
    - [LLM-backed outputs stay off](#llm-backed-outputs-stay-off)
    - [Verifying crw](#verifying-crw)
  - [GPT Researcher Backend](#gpt-researcher-backend)
    - [API Endpoints for GPT Researcher](#api-endpoints-for-gpt-researcher)
    - [MCP Server for GPT Researcher](#mcp-server-for-gpt-researcher)
    - [Image Generation](#image-generation)
    - [Scraper Configuration](#scraper-configuration)
  - [Back-up](#back-up)
  - [Security](#security)


## Understanding the setup

The setup starts the following services:
- [The SearXNG Server](https://fusionauth.io/docs/get-started/download-and-install/docker) at port `9704`
- [crawl4ai](https://docs.crawl4ai.com/) at port `9705`
- [open-crawl](https://github.com/foxbits/open-crawl) at port `9708`
- [GPT Researcher](https://github.com/assafelovic/gpt-researcher) backend at port `9706`
- [camofox-browser](https://github.com/jo-inc/camofox-browser) at port `9709` (stealth browser; see [Camofox Browser](#camofox-browser))
- crw (Firecrawl-compatible scrape/search over plain HTTP with camofox stealth fallback) at port `9710` — can be accessed in browser at http://localhost:9710, or with `http://crw:3000` in `home-lab-net` (see [crw](#crw-firecrawl-compatible-scrapesearch))

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
- `SEARXNG_REDIS_URL`: Valkey/Redis URL for rate limiting and caching (points at `datastore-memory` on `home-lab-net`)
- `FORCE_OWNERSHIP`: take ownership of the mounted config dir on start (needed for the generated `settings.yml`)
- `LOG_LEVEL`: SearXNG log verbosity
- `SEARXNG_SECRET`: A secret key for the cryptography of this instance - change it with a random value, e.g. generate it with  openssl rand -hex 32
- `WOLFRAM_DISABLED`: set to `false` only if you provide a `WOLFRAM_API_KEY` below
- `WOLFRAM_API_KEY`: Go to https://developer.wolframalpha.com/access and create an account and an API key (Full Results API) if you want to use Wolfram Alpha as source as well (the API is limited on the free tier). Otherwise, leave `WOLFRAM_DISABLED` as `true`.
- `MAX_CONCURRENT_TASKS`: Depends on the allowed number of concurrent tasks for a crawl, number must be considered with the formula agent count x parallel tasks x 150MB depending on the RAM you allocate and the number of agents you plan to use. Default is 10.
- `CRAWL4AI_API_TOKEN`: Random token to protect the crawl4ai instance; can use `openssl rand -hex 32` to generate
- `CAMOFOX_BROWSER_PATH`: checkout of the camofox-browser fork (with the native locale/geo identifier patch); built with the official `Dockerfile.ci`, same as `GPT_RESEARCHER_PATH`/`OPENCRAWL_PATH`. Keep the fork rebased on upstream releases.
- `CAMOUFOX_VERSION` / `CAMOUFOX_RELEASE`: Camoufox engine pinned to the latest `daijro/camoufox` release (tag `v<VERSION>-<RELEASE>`); refresh from the releases page. Note upstream pins older engines per app release, so smoke-test after bumping (browserscan check below).
- `CAMOFOX_ACCESS_KEY` / `CAMOFOX_API_KEY` / `CAMOFOX_ADMIN_KEY`: bearer keys for the camofox API (global access / cookie import / `POST /stop`); generate with `openssl rand -hex 32`.
- `CAMOFOX_LOCALES`: browser language override at native Camoufox fingerprint level (first entry used for Intl/Accept-Language). Default `ro-RO,ro,en-US,en`.
- `TZ`: container-local timezone, must match `CAMOFOX_TIMEZONE`. Lives in `.env`, so every stack service sharing it adopts Bucharest local time.
- `CAMOFOX_TIMEZONE` / `CAMOFOX_LATITUDE` / `CAMOFOX_LONGITUDE`: browser timezone and coordinates at native Camoufox fingerprint level. Must match the public geolocation of the home IP (verify against an IP-geolocation lookup; re-check if the IP ever changes region). Must stay unset if `PROXY_HOST` is ever used — the server refuses to start otherwise.
- `PROXY_HOST` / `PROXY_PORT`: unset. Setting them re-enables GeoIP-derived timezone/coordinates and requires a proxy sidecar plus unsetting the three manual vars above.
- `CAMOFOX_PROFILE_DIR` / `CAMOFOX_TRACES_DIR` / `CAMOFOX_COOKIES_DIR` / `CAMOFOX_UPLOADS_DIR`: state dirs inside the container (named volumes / bind mounts).
- `CAMOFOX_CRASH_REPORT_ENABLED`: anonymized crash telemetry to upstream (`false` for personal use).
- `MAX_SESSIONS` / `MAX_TABS_PER_SESSION` / `MAX_TABS_GLOBAL` / `SESSION_TIMEOUT_MS` / `TAB_INACTIVITY_MS` / `BROWSER_IDLE_TIMEOUT_MS` / `HANDLER_TIMEOUT_MS` / `NAVIGATE_TIMEOUT_MS` / `MAX_CONCURRENT_PER_USER` / `MAX_OLD_SPACE_SIZE`: camofox sizing caps (18 tabs worst case fits the 4G limit / 3G shm at ~150MB per tab; a 24h idle window keeps the fingerprint stable (`0` does not mean never upstream — it fires immediately))
- `CAMOFOX_SNAPSHOT_MAX_CHARS` / `CAMOFOX_SNAPSHOT_TAIL_CHARS` / `CAMOFOX_SNAPSHOT_MAX_NODES`: snapshot windowing (160K chars ≈ 40K tokens per observation; the tail preserves pagination/nav refs in every chunk; the nodes cap limits `[eN]` ref annotation — raise together)..
- `CRW_PATH`: checkout of the crw source repo (build-from-source pattern, same as `GPT_RESEARCHER_PATH`/`OPENCRAWL_PATH`/`CAMOFOX_BROWSER_PATH`); the compose `build.context` points here and builds with `CARGO_PKGS="-p crw-server --features camoufox -p crw-mcp -p crw-cli"`. If the build fails with "none of the selected packages contains this feature", use the qualified form `-p crw-server --features crw-server/camoufox`.
- `CRW_API_KEY`: bearer key guarding crw itself (`/v1/*` + `/mcp`); generate with `openssl rand -hex 32`. Public endpoints (`/health`, `/ready`, `/openapi.json`) stay unauthenticated.
- `CRW_RENDERER__CAMOUFOX__API_KEY` is not set in `.env` — it is derived in `docker-compose.yml` as `${CAMOFOX_ACCESS_KEY}` (no new secret). If `POST /tabs` returns 401 with the access key, retry with `CAMOFOX_API_KEY` and rewire the mapping to whichever succeeds (see [Verifying crw](#verifying-crw)).

### GPT-Researcher Settings

GPT Researcher requires an OpenAI-compatible LLM API Provider. Configure the following variables:

- `GPT_RESEARCHER_PATH`: path to where you have cloned the repository [better-gpt-researcher](https://github.com/foxbits/better-gpt-researcher) (which adds crawl4ai and open-ai compatible image generators) or the original [gpt-researcher](https://github.com/assafelovic/gpt-researcher)
- `LANGUAGE`: The language to generate the response in
- `RETRIEVER`: search backend for GPT Researcher (`searx` = local SearXNG)
- `SEARX_URL`: in-network URL of SearXNG used by the retriever
- `OPENCRAWL_PATH`: checkout of the open-crawl Tavily-compatible proxy over crawl4ai (see pre-requisites below)
- `CURATE_SOURCES`: Whether to curate sources for research. This step adds an LLM run which may increase costs and total run time but improves quality of source selection
- `OPENAI_API_KEY`: API key for the LLM provider (required)
- `OPENAI_BASE_URL`: Base URL for the Open-AI compatible LLM API
- `FAST_LLM`: Model used for very fast operations with OK intelligence (default: `xiaomi/mimo-v2-flash`), must be prefixed by the provider, e.g. `openai:`
- `SMART_LLM`: Model used for comprehensive research and the report generation (needs to be high in intelligence), must be prefixed by the provider, e.g. `openai:`
- `SMART_TOKEN_LIMIT`: token budget for the smart LLM
- `STRATEGIC_LLM`: Model used to generate plan and delegate tasks, needs to support structured outputs and tool calling, must be prefixed by the provider, e.g. `openai:`
- `EMBEDDING`: Embedding model for text vectorization, must be prefixed by the provider, e.g. `openai:`
- `MAX_SEARCH_RESULTS_PER_QUERY`: Maximum number of search results to retrieve per query
- `MAX_ITERATIONS`: Maximum number of iterations for processes like query expansion or search refinement
- `MAX_SUBTOPICS`: Maximum number of subtopics to generate or consider.
- `DEEP_RESEARCH_BREADTH`: How many parallel research areas are explored during deep research
- `DEEP_RESEARCH_DEPTH`: For each of the research area, how many sequential iterations are done
- `DEEP_RESEARCH_CONCURRENCY`: How many concurrent deep research operations are allowed
- `MIN_RAW_CONTENT_LENGTH`: Minimum length of content returned by search engine considered enough (if below this, will scrape the website using the configured scraping engine). Defaults to 300.
- `SCRAPER`: Web scraper method - `bs` (BeautifulSoup), `browser` (Selenium), `nodriver` (ZenDriver), `firecrawl`, `tavily_extract`, **`crawl4ai`** (local Crawl4AI, **default in this stack**)
- `CRAWL4AI_API_URL`: URL of the Crawl4AI service (default: `http://crawl4ai:11235`, for host access use `http://localhost:9705`)
- `IMAGE_GENERATION_ENABLED`: Enable AI-generated inline images (`true`/`false`, default: `false`).
- `IMAGE_GENERATION_PROVIDER`: Image generation provider - `google` (official Google API) or `openai` (OpenAI-compatible custom URL)
- `IMAGE_GENERATION_API_KEY`: API key for OpenAI-compatible image generation (uses `OPENAI_API_KEY` as fallback)
- `IMAGE_GENERATION_BASE_URL`: Base URL for OpenAI-compatible image generation
- `IMAGE_GENERATION_MODEL`: Model for image generation (Gemini model when `google`, DALL-E model when `openai`)
- `IMAGE_GENERATION_MAX_IMAGES`: Maximum images per report (default: 3)


## Running

### Pre-requisites

1. The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).
2. This stack depends on an In-Memory Database (Valkey) and by default is configured to use a [`datastore-memory`](../datastore-memory/) instance already running on the same docker network (`home-lab-net`), so that needs to be configured first.
3. On the first run, the stack will generate a `settings.yml` file in `searxng/core-config` directory, based on the default configuration and environment variables. On subsequent runs, if you want to change the config file (you should not need to), you need to delete the existing `settings.yml` file and allow the `run` command to run as `sudo` since it needs to take ownership of the directory containing it.
4. For GPT Researcher, this stack (temporarily) uses a fork of it, to be able to use crawl4ai as engine (and some embeddings fixes), therefore you will have to first clone locally the repository [better-gpt-researcher](https://github.com/foxbits/better-gpt-researcher) (which adds crawl4ai and open-ai compatible image generators) or the original [gpt-researcher](https://github.com/assafelovic/gpt-researcher) and set the path to it through `GPT_RESEARCHER_PATH`.
5. For Crawl4AI, this stach also adds [open-crawl](https://github.com/foxbits/open-crawl), a proxy on top of crawl4ai that exposes Tavily compatible APIs (that can be used with [OpenWebUI](./../luna/) or other tools). So first you have to clone the repository and set the path to it through `OPENCRAWL_PATH`


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

Camofox will be available at [http://localhost:9709](http://localhost:9709), or with [http://camofox:9377](http://camofox:9377) in `home-lab-net`

crw will be available at [http://localhost:9710](http://localhost:9710), or with [http://crw:3000](http://crw:3000) in `home-lab-net`

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


### Camofox Browser

Camofox is an anti-detection headless browser (Camoufox engine: C++-level fingerprint spoofing) driven over a REST API built for agents: accessibility snapshots with stable element refs (`e1`, `e2`, …) instead of bloated HTML, plus search macros. It is built from a fork (`CAMOFOX_BROWSER_PATH`, official `Dockerfile.ci`) that adds native locale/geo identifier support; keep the fork rebased on upstream app releases and re-verify the identifiers below after each rebase or engine bump.

Camofox traffic goes straight out the home residential connection, and the browser identifiers are set explicitly at native Camoufox fingerprint level (patched `launchOptions`: `locale` + `config` with timezone/geolocation, mirrored into the Playwright session context). No proxy is involved.

#### Browser identity (locale/timezone/geolocation)

Manual identifiers by default, proxy-derived geography as the opt-in alternative:

| Mode | Timezone | Coordinates / WebRTC IP | Locale |
|------|----------|-------------------------|--------|
| Manual (normal) | `CAMOFOX_TIMEZONE` | `CAMOFOX_LATITUDE` / `CAMOFOX_LONGITUDE` (WebRTC follows the real residential IP) | `CAMOFOX_LOCALES` |
| Proxy configured (alternative) | Camoufox GeoIP (from residential exit IP) | Camoufox GeoIP | `CAMOFOX_LOCALES` if set, else GeoIP |

Manually overriding timezone/coordinates while the proxy is active is rejected at startup (that combination is exactly the inconsistency Camoufox exists to avoid). Production config is `CAMOFOX_LOCALES=ro-RO,ro,en-US,en` with `CAMOFOX_TIMEZONE=Europe/Bucharest`, Iasi coordinates, and `TZ=Europe/Bucharest` on the container: Romanian geography with Romanian-first, English-capable browser language — fully plausible on a Romanian residential IP.

Verify after first start: warm the engine so no agent request pays cold start (`curl -X POST -H "Authorization: Bearer $CAMOFOX_ACCESS_KEY" http://localhost:9709/start`), then create a tab on `https://browserscan.net` and confirm timezone `Europe/Bucharest`, language starting with `ro-RO`, and coordinates near Iasi.

#### API Endpoints for Camofox

All tab endpoints are scoped by `userId` in the body (or query for `GET`s). Full machine-readable spec at `http://localhost:9709/openapi.json`, interactive docs at `http://localhost:9709/docs`.

| Endpoint | Description | Format |
|----------|-------------|--------|
| `POST /tabs {userId, sessionKey, url?}` | Create tab (optional initial URL) | JSON |
| `GET /tabs?userId=X` | List open tabs | JSON |
| `GET /tabs/:id/snapshot?userId=X&offset=N&includeScreenshot=true` | Accessibility snapshot with element refs (paginated) | Text/JSON |
| `POST /tabs/:id/navigate {userId, url}` or `{macro, query}` | Navigate to URL or search macro (`@google_search`, `@youtube_search`, …) | Snapshot |
| `POST /tabs/:id/click {userId, ref}` | Click element by ref (`e1`) or selector | Snapshot |
| `POST /tabs/:id/type {userId, ref, text}` | Type into element | Snapshot |
| `POST /tabs/:id/press {userId, key}` | Press keyboard key | JSON |
| `POST /tabs/:id/scroll {userId, direction}` | Scroll page | JSON |
| `POST /tabs/:id/wait {userId, selector?, timeout?}` | Wait for selector/timeout | JSON |
| `POST /tabs/:id/back|forward|refresh {userId}` | History navigation | JSON |
| `GET /tabs/:id/links|images|downloads|screenshot?userId=X` | Extract links/images/downloads, capture PNG | JSON |
| `POST /tabs/:id/extract {userId, schema}` | Structured extract via JSON Schema with `x-ref` hints | JSON |
| `POST /youtube/transcript {url, languages}` | YouTube captions via yt-dlp (no API key) | JSON |
| `GET /health` | Health check (no auth) | JSON |
| `POST /sessions/:userId/cookies` | Import cookies (requires `CAMOFOX_API_KEY`) | JSON |
| `DELETE /sessions/:userId` | Close all tabs for a user | JSON |

Authenticated calls need `Authorization: Bearer <CAMOFOX_ACCESS_KEY>` (everything except `/health`).

#### Verifying the setup (Postman walkthrough)

Base URL `http://<host>:9709`. Set auth once (Authorization tab → Bearer Token → your `CAMOFOX_ACCESS_KEY`); all requests below inherit it.

> This sequence is the real agent loop in miniature: every automated task runs create → navigate → wait → snapshot (→ act via click/type → re-snapshot) → cleanup. Walking it once in Postman verifies exactly what your agents will rely on.

1. **Create a tab** — `POST /tabs`, body `{"userId": "smoke"}`. Note the tab id from the response.
2. **Navigate** — `POST /tabs/:id/navigate`, body `{"userId": "smoke", "url": "https://browserscan.net"}`. This only waits for `domcontentloaded`, so the page (especially SPAs) is usually still rendering when it returns.
3. **Wait for readiness** — `POST /tabs/:id/wait`, body `{"userId": "smoke", "timeout": 15000}`. Blocks through network-idle, hydration polling, and a settle delay; returns `{"ok": true, "ready": true/false}`. Proceed on `true`; after a `false` you still get whatever rendered so far.
4. **Read the snapshot** — `GET /tabs/:id/snapshot?userId=smoke`. Expect: the IP, language, timezone and location coordinates that you set, `Proxy: No`, `Bot Detection: No`. If the response has `"truncated": true`, page through it with `?userId=smoke&offset=<nextOffset>` until `"hasMore": false`; if it's nearly empty, `wait` again and re-request (no re-navigate needed).
5. **Clean up** — `DELETE /sessions/smoke`.

#### Importing browser cookies

Use this to reuse logins from your daily browser in an agent session. Import first, then open tabs with the same `userId` — the tabs pick the cookies up.

1. **Export from Brave.** Brave encrypts cookies at rest, so copy-pasting its SQLite file does not work. Install the open-source "Get cookies.txt LOCALLY" extension (exports locally, nothing is uploaded), open the site, and export to `cookies.txt` (Netscape format).
2. **Convert to JSON.** The import endpoint takes `{"cookies": [{"name", "value", "domain", ...}]}` (max 500 per request). Convert with the bundled script (Python 3, stdlib only):
   ```bash
   python camofox/cookies-to-json.py cookies.txt -o cookies.json
   ```
3. **Import.** `POST /sessions/:userId/cookies` with the JSON file as body — authenticated with `Authorization: Bearer <CAMOFOX_API_KEY>` (note: the API key, not the access key).
4. **Use.** `POST /tabs` with the same `userId`, navigate to the site — you should arrive logged in. `chmod 0600` any cookie files you keep on disk.

### crw (Firecrawl-compatible scrape/search)

crw serves Firecrawl-compatible `/v1/scrape|search|crawl|map|extract` (plus `/v1/capabilities` and `/mcp`) on host port `9710` (container `3000`). Fetch ladder is `mode="auto"` with `include_in_auto=true`: plain HTTP first, failover to the existing `camofox:9377` stealth tier; search goes through the existing `searxng:8080`. It is built from source (`CRW_PATH`, `camoufox` feature only — no lightpanda/chrome/playwright/CDP). Config is the bind-mounted `crw/config.crw.toml`, selected via `CRW_CONFIG=config.crw` (bare stem — `config::File::with_name` appends `.toml`). The first build is slow (Rust + cargo-chef) and reuses the dependency layer unless manifests/`CARGO_PKGS` change.

#### API Endpoints for crw

Authenticated calls need `Authorization: Bearer <CRW_API_KEY>` (everything under `/v1/*` plus `/mcp`). `/health`, `/ready`, and `/openapi.json` stay public.

| Endpoint | Description | Auth |
|----------|-------------|------|
| `GET /health` | Liveness probe (cheap, never touches renderers) | none |
| `GET /ready` | Readiness probe (checks renderers; 503s when camofox is down — do NOT use as the compose healthcheck) | none |
| `GET /openapi.json` | Machine-readable API spec | none |
| `POST /v1/scrape {"url": "...", "formats": ["markdown"]}` | Scrape one URL to markdown | bearer `CRW_API_KEY` |
| `POST /v1/scrape {"url": "...", "renderer": "camoufox", "formats": ["markdown"]}` | Scrape pinned to the camofox tier | bearer `CRW_API_KEY` |
| `POST /v1/search {"query": "...", "limit": 5}` | Web search via searxng | bearer `CRW_API_KEY` |
| `POST /v1/crawl {"url": "..."}` | Crawl a site (fan-out over the same HTTP→camofox ladder) | bearer `CRW_API_KEY` |
| `POST /v1/map {"url": "..."}` | Map/discover URLs for a site (search-enriched) | bearer `CRW_API_KEY` |
| `POST /v1/extract {"urls": ["..."]}` | Extract page content (plain markdown; no LLM schema mode — see below) | bearer `CRW_API_KEY` |
| `GET /v1/capabilities` | Lists enabled tiers — must include `camoufox` (proves the `camoufox` cargo feature was compiled in) | bearer `CRW_API_KEY` |
| `/mcp` | MCP endpoint for agents | bearer `CRW_API_KEY` |

Compose healthcheck is a bash `/dev/tcp` liveness probe on `3000` (the runtime image has no curl/wget; `bash` exists in `bookworm-slim`), never `/ready` (which flaps with the sidecar).

#### Camofox integration and limits

- Ladder: `mode="auto"` + `include_in_auto=true` + non-empty `base_url` is the only way into the auto chain. A configured-but-default (`false`) tier stays reachable solely via explicit `renderer="camoufox"` pins. `mode="camoufox"` (pin everything) is intentionally not used — HTTP stays first.
- Contract: crw calls `POST /tabs {userId, sessionKey, url}` → `POST /tabs/{id}/evaluate {userId, expression="document.documentElement.outerHTML"}` → `DELETE /sessions/{userId}`, plus a `GET /health` probe. The evaluate response shape is `{ok, result}` where `result` is the HTML string. Upstream `jo-inc/camofox-browser` exposes `POST /tabs/{tabId}/evaluate` (see its `docs/openapi.json`); if the fork predates it or the native locale/geo patch broke it, the tier cannot work — rebase/patch the fork (the [Verifying crw](#verifying-crw) guide surfaces this first).
- Response-size cap: `CAMOFOX_EVALUATE_MAX_BODY_SIZE` (default `1mb`) bounds the evaluate payload on the camofox side.
- Known gaps (accepted — HTTP+camofox only, CDP removed):
  - No screenshots: `formats:["screenshot"]` hard-errors with only camoufox configured.
  - No cookie carryover: crw mints a fresh random session per request and deletes it on a fixed 5s budget even on error, so imported cookies (`POST /sessions/:userId/cookies`) never apply.
  - No proxy rotation on the JS path and no CDP `Fetch` resource blocking (camofox loads the page itself — slower/heavier); HTTP-tier stealth headers/UA rotation still apply. No new proxy needed (direct residential egress, same as camofox today).
  - No readiness wait: crw does create→immediate evaluate. It never calls camofox `POST /tabs/:id/wait`, so thin SPAs may return empty/challenge HTML and fail. `wait_for_ms` and custom headers are ignored on this tier — tune `camoufox_timeout_ms` (60s default) + request `deadlineMs` instead of expecting networkidle.
  - Sidecar saturation: each crw request costs 1 camofox session + 1 tab against `MAX_SESSIONS=15 / MAX_TABS_GLOBAL=18`. Concurrent crawls (crw `max_concurrency=10` + fan-out) can exhaust the sidecar → 429/503. Cap crw concurrency first, raise camofox caps second.
- Auth mapping: crw sends one bearer (`CRW_RENDERER__CAMOUFOX__API_KEY`, derived from `CAMOFOX_ACCESS_KEY`) on every camofox call including `GET /health`. crw never calls cookie import or `/stop`, so `CAMOFOX_API_KEY` / `CAMOFOX_ADMIN_KEY` are otherwise irrelevant to it.

#### LLM-backed outputs stay off

This deployment wires no `[extraction.llm]` section (intentional — crw LLM wiring is out of scope):

- `formats:["summary"]`, `formats:["json"]` with a `jsonSchema`, and `answer:true` / summarize paths return HTTP 400 pointing at `CRW_EXTRACTION__LLM__API_KEY`.
- `query_expand` stays `false` and `answer_calibrated` stays `false` in `crw/config.crw.toml` (both need an LLM behind them; re-enable together with `[extraction.llm]` later).
- Scope is plain markdown + search-only until LLM wiring becomes a separate change.

#### Verifying crw

Run these on the deploy host (Docker available). Modelled on the camofox Postman walkthrough above: part (a) proves the camofox contract crw depends on, part (b) smokes crw itself. Stop at the first failure — do not trust the tier until (a) passes.

(a) Camofox contract check (base URL `http://<host>:9709`):

1. **Spec check** — `GET http://<host>:9709/openapi.json` and confirm it contains `/tabs/{tabId}/evaluate`. If absent: STOP — rebase/patch the fork (or change crw to snapshot, out of scope).
2. **Create a tab** — `POST /tabs` with `Authorization: Bearer $CAMOFOX_ACCESS_KEY`, body `{"userId": "crw-smoke", "sessionKey": "crw-smoke", "url": "https://example.com"}`. Note the tab id. If 401, retry with `Authorization: Bearer $CAMOFOX_API_KEY`; whichever succeeds is the key crw must use — rewire `CRW_RENDERER__CAMOUFOX__API_KEY` in compose to the winner and document it in `.env`.
3. **Evaluate** — `POST /tabs/:id/evaluate` (same bearer as step 2), body `{"userId": "crw-smoke", "expression": "document.documentElement.outerHTML"}`. Expect `{ok: true, result: "<html>..."}`.
4. **Cleanup** — `DELETE /sessions/crw-smoke` (same bearer). Expect 200.
5. **Bearer health** — `GET /health` with the same bearer. Expect 200 (if a bearer-gated `/health` ever 401s here, crw's `is_available()` stays false and the tier is skipped).

(b) crw smokes (base URL `http://<host>:9710`, bearer `CRW_API_KEY` unless noted):

1. **Liveness (open)** — `GET /health` with no auth. Expect 200.
2. **Capabilities** — `GET /v1/capabilities` with `Authorization: Bearer $CRW_API_KEY`. Expect 200 listing `camoufox` (plus the startup log line `camoufox tier enabled`). If `camoufox` is missing, the image was built without the feature — rebuild with `CARGO_PKGS="-p crw-server --features camoufox -p crw-mcp -p crw-cli"` (fallback: `-p crw-server --features crw-server/camoufox`).
3. **Search** — `POST /v1/search` with bearer, body `{"query": "self-hosted metasearch engine", "limit": 5}`. Expect 200 with results (proves `http://searxng:8080` wiring).
4. **Auto scrape** — `POST /v1/scrape` with bearer, body `{"url": "https://example.com", "formats": ["markdown"]}`. Expect 200 with markdown.
5. **Pinned scrape** — `POST /v1/scrape` with bearer, body `{"url": "https://example.com", "renderer": "camoufox", "formats": ["markdown"]}`. Expect 200 with markdown (proves the camofox tier end to end).
6. **Negative LLM check** — `POST /v1/scrape` with bearer, body `{"url": "https://example.com", "formats": ["markdown"], "answer": true}` (or a schema-`json` extract). Expect HTTP 400 (LLM off by design — see above).
7. **Session-leak check** — `GET http://<host>:9709/tabs?userId=crw-smoke` with `Authorization: Bearer $CAMOFOX_ACCESS_KEY` (the camofox bearer, not `CRW_API_KEY`). Expect an empty list — crw deletes its random session per request, so no tabs may linger.

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

**OpenAI-compatible API (default):**
1. Set `IMAGE_GENERATION_PROVIDER=openai`
2. Set `IMAGE_GENERATION_ENABLED=true`
3. Provide `IMAGE_GENERATION_API_KEY` (or `OPENAI_API_KEY` as fallback)
4. Provide `IMAGE_GENERATION_BASE_URL`
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

The configuration and data will be stored in these docker volumes: [`searxng-data`], [`gpt-researcher-data`], [`camofox-profiles`], [`camofox-traces`] and in these directories: [`./searxng/core-config`], [`./camofox/cookies`], [`./camofox/uploads`] - so this is what you have to back-up. Note `camofox-traces` holds screenshots/DOM/network captures and `camofox-profiles` holds live session cookies — both are sensitive, treat backups accordingly.

crw is stateless — only `crw/config.crw.toml` needs backing up (versioned in git; no named volume, no runtime data dir).

### Security

- Camofox publishes host port `9709`: keep `CAMOFOX_ACCESS_KEY` set (all routes except `/health` require it) and do not expose the port beyond your LAN without a reverse proxy with authentication.
- There is no egress sidecar: traffic leaves directly via the home connection, so nothing extra needs shielding.
- Cookie files in `./camofox/cookies` are live session secrets: `chmod 0600` every file you place there (the mount itself is read-only and the import endpoint additionally requires `CAMOFOX_API_KEY`).
- `POST /stop` (stops the whole browser engine) requires `CAMOFOX_ADMIN_KEY`.
- Crash telemetry is disabled (`CAMOFOX_CRASH_REPORT_ENABLED=false`); upstream it reports anonymized failure data to the vendor.
- crw publishes host port `9710`: keep it LAN-only, keep `CRW_API_KEY` set (all `/v1/*` + `/mcp` routes require it; only `/health`, `/ready`, `/openapi.json` are public), and do not expose the port beyond your LAN without a reverse proxy with authentication. The container runs `read_only: true` with `tmpfs: [/tmp]`, `cap_drop: [ALL]`, and `no-new-privileges` hardening.
