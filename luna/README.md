This is the docker compose setup for [OpenWebUI](https://docs.openwebui.com/), a self-hosted AI chat interface with web search, RAG, image generation, and tool calling capabilities.

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
    - [For your user](#for-your-user)
    - [For the server](#for-the-server)
    - [Configure Crawl4AI as web fetcher](#configure-crawl4ai-as-web-fetcher)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [OpenWebUI](https://docs.openwebui.com/) at port `9707` - can be accessed in browser at [http://localhost:9707](http://localhost:9707)

This stack depends on a SQL database (PostgreSQL) for pgvector and Redis/Valkey for caching. By default it is configured to use a [`datastore-sql`](../datastore-sql/) and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables that might need changing:

**General settings:**
- `WEBUI_NAME`: display name for your instance (default: `Your-Instance-Name`)
- `WEBUI_URL`: your public URL (e.g., `https://your-instance.your-site.net`) - required for OAuth/SSO
- `DEFAULT_LOCALE`: default language locale (default: `en`)

**LLM Providers:**
- `OPENAI_API_BASE_URL`: OpenAI-compatible API base URL
- `OPENAI_API_KEY`: your API key for the LLM provider (create one and set it depending on what provider you use)

**Model Configuration:**
- `DEFAULT_MODELS`: main chat model (default: `moonshotai/kimi-k2.6`) - make sure to use the exact naming from your provider
- `TASK_MODEL_EXTERNAL`: fast model for non-chat tasks like title/follow-up generation (default: `unsloth/gemma-3-4b-it`)

**RAG / Embeddings:**
- `RAG_EMBEDDING_ENGINE`: embedding engine to use (default: `openai`)
- `RAG_OPENAI_API_BASE_URL`: embedding API base URL (default: `${OPENAI_API_BASE_URL}`)
- `RAG_OPENAI_API_KEY`: embedding API key (default: `${OPENAI_API_KEY}`)
- `RAG_EMBEDDING_MODEL`: embedding model (default: `BAAI/bge-m3`)

**Image Generation:**
- `ENABLE_IMAGE_GENERATION`: enable image generation (default: `True`)
- `IMAGE_GENERATION_ENGINE`: image generation engine (default: `openai`)
- `IMAGE_SIZE`: image generation default size, when not specified in the promot - defaults to 1024x1024 (1:1)
- `IMAGE_GENERATION_MODEL`: image generation model (default: `qwen-image`)
- `ENABLE_IMAGE_EDIT`: enable image editing (default: `true`)
- `IMAGE_EDIT_MODEL`: image edit model (default: `qwen-image`)
- `IMAGES_OPENAI_API_BASE_URL`: your open-ai compatible image generator api
- `IMAGES_OPENAI_API_KEY`: your API key for image generation (create one on your provider's website)
- `IMAGES_EDIT_OPENAI_API_BASE_URL`: your open-ai compatible image editor api
- `IMAGES_EDIT_OPENAI_API_KEY`: your API key for image editing (create one on your provider's website)

**Memory & Vector Database:**
- `ENABLE_MEMORIES`: enable memory system (default: `True`)
- `VECTOR_DB`: vector database backend (default: `pgvector`)
- `POSTGRES_USER`: PostgreSQL user (default: `postgres`)
- `POSTGRES_PASSWORD`: the password for your postgresql user

**Auth Settings:**
- `WEBUI_SECRET_KEY`: generate with `openssl rand -hex 32`
- `ENABLE_API_KEYS`: allow users to create API keys for external access (default: `True`)
- `CORS_ALLOW_ORIGIN`: for security (and also for not getting errors) - set this to the adress where you're going to be accessing your instance, e.g. https://your-instance.your-site.net
- `ENABLE_SIGNUP`: allow public registration (default: `False`)

**Default user/password authentication (not recommended, better to use OAuth SSO in production)**
- `ENABLE_PASSWORD_AUTH`: enable password login (default: `False`). Set to true if you do not plan to use OAUTH (3rd party) login (as well as the form-disabling env vars below)
- `ENABLE_LOGIN_FORM`: enable the login user+password form (default: `False`)
- `ENABLE_PASSWORD_CHANGE_FORM`: enable the password reset form from Account settings (default: `False`)

**OAuth SSO Settings**
- `ENABLE_OAUTH_SIGNUP`: allow OAuth signups, auto-creates account on first login (default: `True`)
- `OAUTH_CLIENT_ID`: OAuth client ID from your provider. For all of the OAUTH-x items, you need to create a new application on your auth website (if using one) and add the connection details here - you can find details under [`fusionauth`](../fusionauth/). For valid redirect url use `OPENID_REDIRECT_URI` and for valid URLs use `WEBUI_URL`. Make sure to not enable registration / self-service registration if you do not want random users to create accounts on your auth server. Create an user and register it to your application (this way you can select username for the app and other details)
- `OAUTH_CLIENT_SECRET`: OAuth client secret from your provider
- `OPENID_PROVIDER_URL`: OIDC discovery URL (e.g., `https://auth.yoursite.net/<tenant-id>/.well-known/openid-configuration`) - Make sure to replace the <tenant-id> with your tenant id
- `OAUTH_PROVIDER_NAME`: display name for the OAuth provider
- `OPENID_REDIRECT_URI`: OAuth callback URL (e.g., `https://your-instance.your-site.net/oauth/oidc/callback`)


## Running

### Pre-requisites

1. The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).
2. This stack depends on a SQL database (PostgreSQL) and Redis/Valkey. By default it is configured to use [`datastore-sql`](../datastore-sql/) - database name `openwebui` - and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).
3. The stack also needs to be exposed through HTTPS to your connecting devices / services and that part is not included here. You can either add a [`caddy`](https://github.com/caddyserver/caddy) reverse proxy (with self-signed certificate) (example [`here`](../firefly/Caddyfile)) and then import the `.crt` certificate to your devices, or use a tunneling service like [cloudflared](https://github.com/cloudflare/cloudflared). If you do not use HTTPS, you won't be able to use the application on mobile phones as PWA.
4. The stack has pre-configured recommended security settings enabled by default (see the compose file)
5. If you do not have an OAUTH Server (e.g. [`fusionauth`](../fusionauth/)), you need to enable the user/password authentication by enabling the environment variables from the section "Default user authentication with username/password" and setting the OAUTH values to empty below. Otherwise, if you have an OAUTH server you want to use, leave them be and set all the values for the OAUTH.
6. The stack allows you (even if OpenWebUI does not theoretically) to customize the logos and visuals of your OpenWebUI instance. You can find all the files that you can replace inside the [`static-example`](./static-example/) directory, including a [`custom.css`](./static/custom.css). You will have to copy this directory into a new `static` directory in the stack's root before the first run, and, if you want, replace the logos with your own. You have the option to also edit the `.manifest` file and put your naming in there. Have fun, explore!

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command); additionaly it will also create the database `openwebui` on first run, if connected to postgres, since the application itself does not create it
- `make run-update` - to first update the stack (pull), and then run it (run)

OpenWebUI will be available at [http://localhost:9707](http://localhost:9707).


### Configure the stack

Go to your `WEBUI_URL`. With OAUTH on by default, you will just have to login with the provider (and user) you have set up. Alternatively, if not using OAUTH, you will have to create an username && password. The first user logging in will be the admin.

#### For your user
1. Go to Settings -> Account and fill in your details.
2. Go to Settings -> Personalization and enable Memory if you want the assistant to remember things about you.
3. Go to Settings -> General and set your Theme, Enable Notifications and eventually add a system prompt for your account if you have one. You can also play with the Advanced Parameters section. This will affect your account only.
4. (Optional) Configure a system prompt for memory management:
  ```
  ## Memory System Rules
  You have access to the long-term memory storage for the user. You need to automatically save memories when the user clearly shares a durable fact about themselves, especially identity, preferences, dislikes, possessions, tools, habits, work, goals, or recurring constraints.

  Pay special attention to first-person patterns such as:
  I am, I'm, I like, I love, I prefer, I enjoy, I dislike, I hate, I have, I own, I use, I work as, I live in, I usually, I often, I always, I never, I want, I plan to, I’m trying to, I need.

  Only save memories that are likely to help in future conversations. Do not save temporary moods, one-off events, generic small talk, sensitive private data, or uncertain / hypothetical / sarcastic statements. Store memories as short, clear, atomic statements in third-person form. Avoid duplicates. Update old memories when newer explicit information replaces them. When unsure, do not save or ask the user.
  Always inform the user that a fact about them has been saved.
  ```
5. Go to Settings -> Interface and set-up things like location access, title generation, chat background image, copy/paste settings and similar pretty things.


#### For the server
1. Go to Admin Panel -> Settings -> Models
   1. Go to the top „Settings” button and make sure that in the Model Params, Function Calling is set to Native.
   2. Disable all the models that you do not plan to use (if your provider offers many). 
   3. It is recommended that you create "clones" of the models you want to use and set them up with the settings you want - e.g. custom instructions for each of them if you want to, also enabling / disabling functionalities, setting up parameters, custom names, images and description. And then pointing them as "base model" to the model from your provider - this way if you switch providers, you can always keep your models and just point them to different providers.
   4. Make sure to also mark the models as 'public' to not be visible only to the Admin user, if you plan to have other users using your instance, and in the Admin interface set the models order and the pinned models.
   5. Validate for all the models that you plan to use that Function Calling is set to Native.
   6. You can set system prompts per model if you want to build specialized models. But for general system prompts on how all models behave, you should use the user-level prompt, which takes priority.
   7. If you are planning to use DeepSeek models, use [this pipe](https://openwebui.com/posts/deepseek_v4_reasoning_content_fix_41c885fb) that enables you to do so (by default they break in OUI because they require the reasoning to be sent back to them), with the following notes:
      1. Set Enable Thinking always to true, as the models do not have non-thinking mode (eventually set reasoning to zero)
      2. Edit the pipe code to put the models id to match the IDs from your provider, otherwise it will not work
      3. It does not require direct deepseek api access, you can use any provider, use the same url and api key you set in OUI config
2. Go to Admin Panel - Settings -> WebSearch
   1. Enable it with engine as "searxng"
   2. For Searxng Query URL set `http://searxng:8080/search?q=<query>`
   3. For language set `all`
   4. For Search Result Count set something between `5`-`10` for everyday use (normal responses using search, non-controversial subjects). This will not work for any research, only for answer engines.
   5. Enable "Bypass Embedding and Retrieval" to speed-up searches by sending the full results to the LLM (this may speed-up responses but increase input token usage).
   6. Enable "Bypass Web Loader" to bypass the default web fetcher

#### Configure Crawl4AI as web fetcher
1. Go to Settings - Admin - Settings - Integrations - Manage Tool Servers and add a new Server with the following parameters:
   1. Name: Web Crawler
   2. Description: Crawl4AI provides tools to scrape web pages content
   3. URL: http://crawl4ai:11235
   4. Function Name Filter List: get_markdown_md_post, generate_screenshot_screenshot_post, generate_pdf_pdf_post (only these are needed)
2. Go to Settings -> Workspace - Skills and add a skill called **Web Crawling** (id: `web-crawling`) that will be used to connect this stack to crawl4ai that is used by default in [`search-stack`](../search-stack/):
    ```
    Mandatory strategy to use whenever fetching a web page:

    1. Never use the `fetch_url` tool
    2. If the user explicitly asks to wait for the page to fully load / render, use the tool `crawl_markdown`
    3. Otherwise, the default approach is to use the tool `get_markdown_md_post` with mode/fit set to 'raw'
    4. If the result of the web page fetch, after trying the tool `get_markdown_md_post`, is suspiciously empty, short, or clearly missing missing contents, then fall back to using `crawl_markdown`

    Other tools and when to use them:
    5. `crawl_crawl_post` - use when you need to: navigate through multiple pages, load and follow related links, or any multi-URL scrape
    6. `generate_screenshot_screenshot_post` - use when the user explicitly asks for a screenshot, or when a visual snapshot of the page would be helpful
    7. `generate_pdf_pdf_post` - use when the user explicitly asks for a PDF, or when a printable/archivable snapshot is needed
    ```
3. Go to Settings and modify the system prompt to be able to correctly use the web crawling tools:
   ```
    ## Web Crawler Rules
    Never use any tool (get_markdown_md_post, fetch_url, etc.) to access a web page without FIRST calling view_skill("web-crawling") in the same turn. Loading the skill is mandatory before every web access.
    ```
4. Go to Settings -> Workspace - Tools and add a new Tool called "Web Crawler (Advanced)" that will be used as backup to fetch full website data when the default (which is faster but does not wait for javascript to be fully executed) does not work:
    ```
    import os
    import json
    import requests
    from datetime import datetime
    from pydantic import BaseModel, Field


    class Tools:
        class Valves(BaseModel):
            CRAWL4AI_URL: str = Field(
                default="http://crawl4ai:11235",
                description="The base URL of the crawl4ai server",
            )

        def __init__(self):
            self.valves = self.Valves()
            pass

        async def crawl_markdown(
            self, urls: str, wait_for: str = "networkidle", page_timeout: int = 60000
        ) -> str:
            """
            Used to fetch a list of web pages for their content, waiting for them to be fully loaded (e.g. all JavaScript to be executed).

            Parameters:
            - urls: Comma-separated list of URLs to crawl
            - wait_for: Page load strategy (default: "networkidle" which waits for page to be fully loaded)
            - page_timeout: Timeout in ms (default: 60000)
            """
            url_list = [u.strip() for u in urls.split(",")]

            response = requests.post(
                f"{self.valves.CRAWL4AI_URL}/crawl",
                json={
                    "urls": url_list,
                    "crawler_config": {
                        "wait_until": wait_for,
                        "page_timeout": page_timeout,
                    },
                },
                timeout=120,
            )

            data = response.json()
            results = data.get("results", [])

            # Extract only raw_markdown from each result
            output = []
            for r in results:
                output.append(
                    {
                        "url": r.get("url"),
                        "success": r.get("success"),
                        "markdown": r.get("markdown", {}).get("raw_markdown", ""),
                    }
                )

            return json.dumps(output, indent=2)
    ```
5. Go to your models and enable: the new toolset (Web Crawler), the optional tool (Web Crawler (Full)) and the new Skill (Web Crawling).

### Back-up

The configuration and data will be stored in the `openwebui-data` Docker volume and in the `openwebui` PostgreSQL database - so back this up.

Also back up the `.env` file (contains API keys and configuration).