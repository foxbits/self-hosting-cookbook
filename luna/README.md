# Luna (OpenWebUI)

OpenWebUI stack running on port 9707, connected to nano-gpt.com as the AI provider.

## Prerequisites

1. **Docker & Docker Compose** installed
2. **home-lab-net** network created:
   ```bash
   make create-network
   ```
   (from the repository root)

3. **nano-gpt.com API key** and chosen model(s) configured

## Configuration

1. Copy `.env.default` to `.env`:
   ```bash
   cp .env.default .env
   ```

2. Edit `.env` and set:
   - `WEBUI_SECRET_KEY` - generate: `openssl rand -hex 32`
   - `OPENAI_API_KEY` - your nano-gpt.com API key
   - `WAVESPEED_API_KEY` - your wavespeed.ai API key (for image generation)
   - `WEBUI_ADMIN_EMAIL` - admin email
   - `WEBUI_ADMIN_PASSWORD` - strong admin password
   - `WEBUI_URL` - your public URL (`https://luna.foxbites.net`) - **CRITICAL: must be set before enabling OAuth/SSO**
   - Optional: `TASK_MODEL_EXTERNAL` - fast model for background tasks (default: `openai:unsloth/gemma-3-4b-it`)
   - Optional: `RAG_EMBEDDING_MODEL` - embedding model (default: `text-embedding-3-small`)
   - Optional: `DATA_DIR` - data directory inside container (default: `/app/backend/data`); local `./data` is already mounted

3. (Optional) Adjust other settings:
   - `DEFAULT_MODELS` - main chat model (default: `openai:moonshotai/kimi-k2.6:thinking`)
   - `IMAGE_GENERATION_MODEL` - image model (default: `nano-banana-2`)
   - `IMAGES_OPENAI_API_BASE_URL` - wavespeed.ai base URL (default: `https://api.wavespeed.ai/v1`)
   - `ENABLE_OLLAMA_API` - set to `false` (no local Ollama)
   - `REDIS_URL` - datastore-memory Valkey URL (default: `redis://datastore-memory:6379/0`)
   - `ENABLE_BASE_MODELS_CACHE` - cache model list (default: `True`)
   - `MODELS_CACHE_TTL` - cache TTL in seconds (default: `300`)
   - `ENABLE_SIGNUP` - set to `True` to allow user registration

**Important:** Verify that the model IDs (`moonshotai/kimi-k2.6:thinking`, `unsloth/gemma-3-4b-it`, `text-embedding-3-small`) are actually available on your chosen providers. Some providers may use different naming. If a model doesn't appear in the UI, add it manually in **Admin → Connections → OpenAI → Model IDs (Filter)**.

## Running

```bash
make build    # Pull images
make run      # Start the stack
```

Or manually:
```bash
docker compose up -d
```

## Access

- **Web UI**: http://localhost:9707
- **First login**: Admin account created from `.env` settings

## Post-Installation: Tool Integrations

OpenWebUI can use your existing search-stack services as **Tools**:

### 1. MCP Server Connections (via Admin UI)

Navigate to **Admin Panel → Settings → Tools → MCP** and add:

#### SearXNG (Web Search)
- Name: `SearXNG`
- Transport: `SSE`
- URL: `http://searxng:8080/mcp/sse` (if SearXNG has MCP enabled)
- Note: SearXNG may need MCP plugin enabled

#### GPT Researcher (Research Agent)
- Name: `GPT Researcher`
- Transport: `SSE`
- URL: `http://gpt-researcher:8000/mcp/sse`

#### Crawl4AI (Web Crawler)
- Name: `Crawl4AI`
- Transport: `SSE`
- URL: `http://crawl4ai:11235/mcp/sse`

### 2. OpenAPI Tool Connections (Alternative)

If MCP is not available, connect via **Admin Panel → Connections → OpenAPI**:

- **SearXNG API**: `http://searxng:8080` (Swagger/OpenAPI spec)
- **GPT Researcher API**: `http://gpt-researcher:8000` (OpenAPI spec)
- **Crawl4AI API**: `http://crawl4ai:11235` (OpenAPI spec)

### 3. Enable Tools

After adding connections:
- Go to **Admin Panel → Settings → Tools**
- Enable each tool for use in chats
- Tools appear in the `+` menu in chat input

## Optional: FusionAuth OAuth SSO (via Admin UI)

If you have FusionAuth running in your homelab, OpenWebUI supports OIDC SSO natively.

### Prerequisites
1. Cloudflare tunnel active with `WEBUI_URL=https://luna.foxbites.net` set (required for redirect URI)
2. FusionAuth application configured with:
   - **Client ID** & **Client Secret** (create in FusionAuth Application settings)
   - **Redirect URI**: `https://luna.foxbites.net/oauth/oidc/callback`
   - **Logout URL**: `https://luna.foxbites.net`

### Configuration (Admin Panel)
1. Go to **Admin Panel → Settings → OAuth**
2. Enable OAuth: tick **Enable OAuth Sign-up**
3. Fill in:
   - **Client ID**: from FusionAuth
   - **Client Secret**: from FusionAuth
   - **OIDC Discovery URL**: `https://<your-fusionauth>/.well-known/openid-configuration`
   - **Provider Name**: `FusionAuth` (or your preferred label)
4. Save

### Post-OAuth
- Re-authenticate; you should see "Login with FusionAuth" button
- New users can sign up via OAuth; password auth remains available unless `ENABLE_PASSWORD_AUTH=False`
- Admin: optionally configure group/role mapping via `OAUTH_GROUP_CLAIM`, `OAUTH_ADMIN_ROLES`
- See OpenWebUI docs: [SSO & OAuth](https://docs.openwebui.com/troubleshooting/sso/)

## Cloudflare Tunnel (luna.foxbites.net)

When you configure Cloudflare tunnel separately:
1. Point the tunnel to `http://localhost:9707`
2. Set `WEBUI_URL=https://luna.foxbites.net` in `.env` (required for OAuth/SSO if used later)
3. Restart the stack

## Updates

```bash
make run-update    # Pull latest image and restart
```

Or manually:
```bash
docker compose pull
docker compose up -d
```

## Troubleshooting

### Model not showing up
- Verify `OPENAI_API_BASE_URL` and `OPENAI_API_KEY` are correct
- Check connectivity: `curl $OPENAI_API_BASE_URL/models`
- Some providers don't implement `/models` endpoint — add model ID manually in **Admin → Connections → OpenAI**

### MCP connection failures
- Ensure search-stack services are running and on same `home-lab-net` network
- Check MCP endpoints are exposed: `http://gpt-researcher:8000/mcp/sse`
- Some tools require additional configuration in their own `.env` files

### Port conflict
Port 9707 already in use? Change `ports:` mapping in `docker-compose.yml`.

## Data Backup

Back up the local data directory:
```bash
# The ./data directory contains all persistent data
tar -czf luna-backup-$(date +%Y%m%d).tar.gz ./data
```

Also back up the `.env` file (contains API keys and admin credentials).
