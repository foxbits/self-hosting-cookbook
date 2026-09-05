# AGENTS.md — self-hosting-cookbook

This repo is a collection of self-hosted service **stacks**, each in its own top-level
directory, deployed with `docker compose`. This file is the single source of truth for how a
new service stack is added, so you do **not** need to read every existing service to infer the
conventions. Read this, then the upstream docs for the service you are deploying.

When asked to "add a new service/stack", follow the checklist at the bottom of this file.

## Development environment

This repository is a **code-only** workspace. It does **not** have Docker or any container
runtime installed, and no service is ever executed here — stacks are not deployed, started, or
debugged in this environment. The `.env.default` files committed to this repo are examples
(`.env.default`/`.env.example`-style placeholders with `CHANGE_ME` values and inline comments);
they are **never** used to run anything locally.

The actual deployment lives on a separate host that has Docker and `docker compose` installed.
That host copies a service's `.env.default` to `.env`, fills in real secrets/values, and runs
`make run-update` from inside that service's directory. So:

- Do **not** try to run `docker compose config`, `docker compose up`, `make run`, etc. in this
  repo — none of those commands work here. Treat the validation checklist's `docker compose
  config` step as a *recommendation to run on the deployment host*, not something to execute in
  this workspace.
- Do **not** assume `.env` files exist or are usable in this workspace; only `.env.default` is
  guaranteed to be present and safe to read.
- Any verification you can do here is limited to static checks: file layout, YAML syntax,
  referenced paths/ports, alignment with this file's conventions, and consistency between the
  service files and the root-level metadata.

## Repository layout

```
<service-name>/
  docker-compose.yml   # required — the stack definition
  .env.default         # required — example env values (committed); user copies to .env (gitignored)
  Makefile             # required — pull/run/run-update/update-run targets
  .gitignore           # required — at least `.env` + any runtime data dirs
  README.md            # required — setup guide (see structure below)
  Dockerfile           # optional — only for overlay or build-from-source patterns
Makefile               # repo-root: create-network, run-update-all, clean-disk
.env.default           # repo-root: EXECUTION_ORDER (ordered list of service dir names)
README.md              # repo-root: numbered applications list
```

Naming: the directory name, `container_name`, and the `EXECUTION_ORDER` entry are the same
string (e.g. `apprise-notify`). Use kebab-case.

## The docker network

All inter-container communication happens over an **external** docker network named
`home-lab-net`, created once via `make create-network` at the repo root.

- Every service that must be reachable by other containers (or reach other containers) joins it:
  ```yaml
  networks:
    - home-lab-net
  # ...at file bottom:
  networks:
    home-lab-net:
      external: true
  ```
- Reach peers by `container_name` as the hostname, e.g. `redis://datastore-memory:6379/0`,
  `http://apprise-notify:8000`, `jdbc:postgresql://datastore-sql:5432/...`.
- New services SHOULD join `home-lab-net`. (A few older ones only publish host ports and skip
  the network — do not copy that; join the network.)

## Port allocation

Pick a free host port from the list below. **This file is the single source of truth for ports**
— do not scan the compose files; just read this list. When you add a service, add its port to
the list so the next agent sees an up-to-date picture (see the checklist).

Current host ports in use:
```
2283 immich | 5432 postgres (datastore-sql) | 6379 valkey (datastore-memory)
7878 radarr | 8090 beszel | 8191 flaresolverr | 8989 sonarr | 9117 jackett (arr-stack)
9701 fusionauth | 9704 searxng | 9705 crawl4ai | 9706 gpt-researcher | 9707 luna | 9708 open-crawl | 9709 camofox (agents-stack)
9830 jenkins | 9843 portainer | 9860 actual | 9862 apprise-notify | 9863 opencloud | 9864 vaultwarden
```
(plex-server uses `network_mode: host` and the host's own 32400 — a special case; avoid unless
the upstream image requires host networking.)

Convention:
- Infra/data services may reuse the canonical port (5432, 6379, etc.).
- App/web services use the **97xx** and **98xx** ranges. Prefer the next free 98xx port.
- Map as `"HOST:CONTAINER"` (quoted). The container port is whatever the image listens on.

## The five required files

### 1. `docker-compose.yml`

Common (official image) shape — copy this and adapt:
```yaml
services:
  <service-name>:
    image: <image>:latest
    container_name: <service-name>
    restart: unless-stopped
    networks:
      - home-lab-net
    ports:
      - "<HOST_PORT>:<CONTAINER_PORT>"
    env_file:
      - .env
    volumes:
      - ./<data-dir>:/<container-path>      # bind mount (simple, easy to back up)
      # OR a named volume:  <service-name>-data:/<container-path>
    healthcheck:
      test: ["CMD-SHELL", "<curl/wget to the service health endpoint> || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

# only if you use named volumes:
volumes:
  <service-name>-data:

networks:
  home-lab-net:
    external: true
```

Conventions:
- `restart: unless-stopped` on every service.
- `env_file: - .env` is preferred; all env vars come from the user's `.env` (copied from
  `.env.default`). Add an `environment:` block **only** for derived/computed values that
  interpolate env vars (e.g. `DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@datastore-sql:5432/db`).
- `healthcheck`: use the upstream service's health endpoint if it has one
  (`/status`, `/health`, `/healthz`, `pg_isready`, etc.). Omit only if the image has none.
- Volumes: **bind mounts** (`./<dir>:...`) for simple single-host state that is easy to back up;
  **named volumes** (`<name>:`) for managed/stateful data. Both are valid.

### 2. `.env.default`

Committed example values with inline comments. The user copies it to `.env` (gitignored) and
edits. Include every env var the service needs. Use `CHANGE_ME`/placeholder values for secrets
and document how to generate real ones (e.g. `# generate with: openssl rand -hex 32`).
Comment out optional vars.

Keep comments minimal: values plus at most a one-line generation hint or a
"must match X" sync note. Do not explain variables here — every key in
`.env.default` must instead be documented in the service `README.md`
environment-variables section.

### 3. `Makefile`

**Image-only service** (most common — actual, datastore-*, apprise-notify):
```makefile
.PHONY: pull run run-update update-run

pull:
	docker compose pull

run:
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update
```

**Build-from-source / overlay service** (luna, agents-stack): add a `build` target and have
`run-update` build first:
```makefile
build:
	docker compose pull
	docker compose build

run-update:
	$(MAKE) build
	$(MAKE) run
```

**Optional advanced targets** (only if the service needs them — do not add speculatively):
- `create-db` / `delete-db` — when the service needs a database created on `datastore-sql`
  before first run (see `immich/Makefile`, `luna/Makefile`).
- `generate-override` / `clean-override` — when env vars must materialize a
  `docker-compose.override.yml` (e.g. dynamic volume lists; see `arr-stack/Makefile`,
  `beszel/Makefile`).

`update-run` is always an alias of `run-update` (the root `run-update-all` calls `update-run`).

### 4. `.gitignore`

At minimum:
```
.env
<runtime-data-dir>/
```
(e.g. `data/`, `apprise_config/`, `apprise_attach/`). Ignore any bind-mounted runtime dir so it
isn't committed.

### 5. `README.md`

Follow this structure (mirror `actual/README.md` / `apprise-notify/README.md`):
- One-line intro: what it is + a link to the upstream project.
- Line: "A full setup and integration guide can be found on thefoxdiaries.substack.com."
- TOC (markdown links).
- **Understanding the setup**: bullet list of each service + its port ("at port `XXXX` — can be
  accessed in browser at http://localhost:XXXX"); note the restart-unless-stopped behavior.
- **Environment variables**: a table or bullet list of every `.env` var with a short description.
- **Running** → **Pre-requisites** (docker + docker compose; `make create-network` from root;
  copy `.env.default` to `.env`), **Starting the stack** (`make pull`/`run`/`run-update`), and any
  **Configure the stack** post-start steps (create admin account, point a reverse proxy, etc.).
- **Back-up**: which bind-mounted dir(s) / named volume(s) hold the data to back up.
- **Security** section (when relevant): call out any no-auth, public-exposure, or secret-handling
  concerns explicitly and loudly (see `apprise-notify/README.md` for the pattern).

## Three deployment patterns

1. **Official image** — `image: <image>:latest`. No Dockerfile. (actual, apprise-notify, beszel,
   datastore-*, fusionauth, portainer.)
2. **Overlay** (customize an official image) — a local `Dockerfile` starting `FROM <official>`
   that COPYs/patches assets; `build: context: .`. (luna overlays branding onto open-webui.)
3. **Build from a separate source repo** — the app source + Dockerfile live in another repo
   (e.g. `../../repos/<repo>`). Reference it via an env-var path:
   ```yaml
   build:
     context: ${<NAME>_PATH}
     dockerfile: Dockerfile
   ```
   and in `.env.default`: `<NAME>_PATH=../../repos/<repo>`. Add a `build` Makefile target.
   (agents-stack builds `open-crawl`/`gpt-researcher` this way.) The Dockerfile is NOT in the
   cookbook dir — it lives in the source repo.

(In-repo source build — `build: context: .` with a Dockerfile in the service dir — is also valid;
see the jenkins agent.)

## Root-level changes (required for every new service)

1. **`README.md`** applications list: add a new numbered entry. The list is roughly alphabetical;
   insert in the correct alphabetical slot and **renumber the subsequent entries** so the list
   stays sequential (1..N). Format:
   ```
   N. [`<service-name>`](<service-name>) - docker compose setup for a/an [Upstream](url) ...
   ```
   Only link to other service dirs that already exist (avoid broken links to not-yet-created dirs).
2. **`.env.default`** (repo root): add the service dir name to `EXECUTION_ORDER`. Order:
   infra/datastore/auth/notification dependencies first, then apps. Place a dependency-providing
   service (e.g. a notification gateway, a DB) **before** the services that consume it.
3. **`README.md`** "default order is:" code block: update it to match the new `EXECUTION_ORDER`
   exactly.

The root `Makefile`'s `run-update-all` iterates `EXECUTION_ORDER`, runs each service's
`update-run`, and waits for health between services — so ordering matters for dependencies.

## Validation checklist (run before declaring done)

- [ ] `cd <service-name> && cp .env.default .env && docker compose config` resolves with no
      errors (image, env, ports, volumes, network all present); then `rm .env`.
- [ ] No host port collision — the chosen port is free in the **Port allocation** list in this
      `AGENTS.md` (do not scan compose files).
- [ ] The `AGENTS.md` **Port allocation** list has been updated with the new service's port.
- [ ] `container_name`, directory name, and `EXECUTION_ORDER` entry all match.
- [ ] `.gitignore` covers `.env` and any runtime data dir.
- [ ] Every `.env.default` key is documented in the service `README.md`
      environment-variables section (comments in `.env.default` stay minimal).
- [ ] Root `README.md` list is sequentially numbered 1..N and the "default order is:" block
      matches root `.env.default`'s `EXECUTION_ORDER`.
- [ ] `make run-update` (from the service dir) brings the stack up and it reports healthy.
- [ ] Service is reachable on its host port and (if it has consumers) on `home-lab-net` by
      `container_name`.

## Checklist for adding a new service stack

1. Choose the `<service-name>` (kebab-case) and a free host port from the **Port allocation**
   list in this `AGENTS.md` (do not scan compose files).
2. Decide the deployment pattern (official image / overlay / build-from-source) and whether it
   needs `home-lab-net`, a DB on `datastore-sql`, or `datastore-memory`.
3. Create `<service-name>/` with the five required files using the templates above; add a
   `Dockerfile` only for overlay/build-from-source.
4. Write `.env.default` with every env var the service needs (placeholders for secrets).
5. Write `README.md` in the standard structure, including env vars, run steps, back-up, and any
   security notes.
6. Update the repo root: add to `README.md` applications list (renumber), add to
   `EXECUTION_ORDER` in root `.env.default`, and sync the "default order is:" block. Also add
   the new service's port to the **Port allocation** list in this `AGENTS.md`.
7. Run the validation checklist.
8. Do not commit unless explicitly asked.
