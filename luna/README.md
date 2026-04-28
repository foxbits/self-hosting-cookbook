This is the docker compose setup for [OpenWebUI](https://docs.openwebui.com/), a self-hosted AI chat interface with web search, RAG, image generation, and tool calling capabilities.

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [OpenWebUI](https://docs.openwebui.com/) at port `9707` - can be accessed in browser at [http://localhost:9707](http://localhost:9707)

This stack depends on a SQL database (PostgreSQL) for pgvector and Redis/Valkey for caching. By default it is configured to use a [`datastore-sql`](../datastore-sql/) and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:

**Data Directory:**
- `DATA_DIR`: data directory mapped on the local machine (default: `./data`)

**Tool Calling:**
- `ENABLE_TOOL_CALLING`: enable tool calling support (default: `True`)
- `DEFAULT_FUNCTION_CALLING_MODE`: function calling mode, native recommended for modern models (default: `native`)

**LLM Providers:**
- `OPENAI_API_BASE_URL`: OpenAI-compatible API base URL (default: `https://nano-gpt.com/api/v1`)
- `OPENAI_API_KEY`: your API key for the LLM provider (create one and set it depending on what provider you use)
- `ENABLE_OLLAMA_API`: enable local Ollama (default: `false`)

**Model Configuration:**
- `DEFAULT_MODELS`: main chat model (default: `openai:deepseek/deepseek-v4-pro`) - make sure to use the exact naming from your provider
- `TASK_MODEL_EXTERNAL`: fast model for non-chat tasks like title/follow-up generation (default: `openai:unsloth/gemma-3-4b-it`)
- `ENABLE_AUTOCOMPLETE_GENERATION`: enable autocomplete suggestions (default: `True`)
- `ENABLE_FOLLOW_UP_GENERATION`: enable follow-up question generation (default: `True`)
- `ENABLE_TITLE_GENERATION`: enable automatic chat title generation (default: `True`)
- `ENABLE_BASE_MODELS_CACHE`: cache model list from provider (default: `True`)
- `MODELS_CACHE_TTL`: cache TTL in seconds (default: `300`)

**RAG / Embeddings:**
- `RAG_EMBEDDING_ENGINE`: embedding engine to use (default: `openai`)
- `RAG_OPENAI_API_BASE_URL`: embedding API base URL (default: `${OPENAI_API_BASE_URL}`)
- `RAG_OPENAI_API_KEY`: embedding API key (default: `${OPENAI_API_KEY}`)
- `RAG_EMBEDDING_MODEL`: embedding model (default: `BAAI/bge-m3`)

**Image Generation:**
- `ENABLE_IMAGE_GENERATION`: enable image generation (default: `True`)
- `IMAGE_GENERATION_ENGINE`: image generation engine (default: `openai`)
- `IMAGE_GENERATION_MODEL`: image generation model (default: `nano-banana-2`)
- `ENABLE_IMAGE_EDIT`: enable image editing (default: `true`)
- `IMAGE_EDIT_MODEL`: image edit model (default: `nano-banana-2-edit`)
- `IMAGES_OPENAI_API_BASE_URL`: your open-ai compatible image generator api, e.g. wavespeed.ai (default: `https://api.wavespeed.ai/v1`)
- `IMAGES_OPENAI_API_KEY`: your API key for image generation (create one on your provider's website)
- `IMAGES_EDIT_OPENAI_API_BASE_URL`: your open-ai compatible image editor api, e.g. wavespeed.ai (default: `https://api.wavespeed.ai/v1`)
- `IMAGES_EDIT_OPENAI_API_KEY`: your API key for image editing (create one on your provider's website)

**Memory & Vector Database:**
- `ENABLE_MEMORIES`: enable memory system (default: `True`)
- `VECTOR_DB`: vector database backend (default: `pgvector`)
- `POSTGRES_USER`: PostgreSQL user (default: `postgres`)
- `POSTGRES_PASSWORD`: the password for your postgresql instance

**Redis / Valkey:**
- `REDIS_URL`: Redis/Valkey connection URL (default: `redis://datastore-memory:6379/0`)

**WebUI Customization:**
- `WEBUI_NAME`: display name for your instance (default: `Your-Instance-Name`)
- `WEBUI_URL`: your public URL (e.g., `https://your-instance.your-site.net`) - required for OAuth/SSO
- `DEFAULT_LOCALE`: default language locale (default: `en`)

**Auth Settings:**
- `WEBUI_SECRET_KEY`: generate with `openssl rand -hex 32`
- `ENABLE_API_KEYS`: allow users to create API keys for external access (default: `True`)
- `ENABLE_SIGNUP`: allow public registration (default: `False`)
- `ENABLE_OAUTH_SIGNUP`: allow OAuth signups, auto-creates account on first login (default: `True`)
- `ENABLE_PASSWORD_AUTH`: enable password login (default: `False`)
- `OAUTH_CLIENT_ID`: OAuth client ID from your provider. For all of the OAUTH-x items, you need to create a new application on your auth website (if using one) and add the connection details here - you can find details under [`fusionauth`](../fusionauth/). For valid redirect url use `OPENID_REDIRECT_URI` and for valid URLs use `WEBUI_URL`. Make sure to not enable registration / self-service registration if you do not want random users to create accounts on your auth server.
- `OAUTH_CLIENT_SECRET`: OAuth client secret from your provider
- `OPENID_PROVIDER_URL`: OIDC discovery URL (e.g., `https://auth.yoursite.net/<tenant-id>/.well-known/openid-configuration`) - Make sure to replace the <tenant-id> with your tenant id
- `OAUTH_PROVIDER_NAME`: display name for the OAuth provider
- `OPENID_REDIRECT_URI`: OAuth callback URL (e.g., `https://your-instance.your-site.net/oauth/oidc/callback`)


## Running

### Pre-requisites

The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).

This stack depends on a SQL database (PostgreSQL) and Redis/Valkey. By default it is configured to use [`datastore-sql`](../datastore-sql/) - database name `openwebui` - and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).

The stack also needs to be exposed through HTTPS to your connecting devices / services and that part is not included here. You can either add a [`caddy`](https://github.com/caddyserver/caddy) reverse proxy (with self-signed certificate) (example [`here`](../firefly/Caddyfile)) and then import the `.crt` certificate to your devices, or use a tunneling service like [cloudflared](https://github.com/cloudflare/cloudflared). If you do not use HTTPS, you won't be able to use the application on mobile phones as PWA.

If you do not have an OAUTH Server (e.g. [`fusionauth`](../fusionauth/)), you need to set `ENABLE_PASSWORD_AUTH` to true and set all the OAUTH-related env vars to empty.

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make pull` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

OpenWebUI will be available at [http://localhost:9707](http://localhost:9707).


### Configure the stack

1. First login: If `ENABLE_PASSWORD_AUTH=False` (default), you'll need OAuth configured first. If `ENABLE_SIGNUP=False` (default), the first user must be created via OAuth or you can temporarily enable signup - the first user logging in will be the admin.
2. Configure your AI provider:
   1. Go to **Admin Panel → Settings → Connections → OpenAI**
   2. Verify the API base URL and key from `.env` are detected
   3. If models don't appear, add them manually in **Model IDs (Filter)** field
3. (Optional) Configure tool integrations via **Admin Panel → Settings → Tools → MCP**:
   1. Add MCP servers: SearXNG (`http://searxng:8080/mcp/sse`), GPT Researcher (`http://gpt-researcher:8000/mcp/sse`), Crawl4AI (`http://crawl4ai:11235/mcp/sse`)
   2. Enable tools for use in chats - they appear in the `+` menu in chat input
4. (Optional) Configure OAuth SSO:
   1. Set `WEBUI_URL` in `.env` (required for redirect URI)
   2. Configure your OAuth provider (e.g., FusionAuth) with redirect URI: `https://luna.foxbites.net/oauth/oidc/callback`
   3. Set OAuth variables in `.env`: `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OPENID_PROVIDER_URL`, `OAUTH_PROVIDER_NAME`, `OPENID_REDIRECT_URI`
   4. Restart the stack

**Important:** Verify that model IDs are available on your provider. Some providers use different naming. If a model doesn't appear, add it manually in **Admin → Connections → OpenAI → Model IDs (Filter)**.


### Back-up

The configuration and data will be stored in the local `./data` directory - so this is what you have to back-up.

Also back up the `.env` file (contains API keys and configuration).