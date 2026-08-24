This is the docker compose setup for [OpenCloud](https://opencloud.eu) (with [Euro Office](https://github.com/EURO-office/DocumentServer) document editing) — a self-hosted, GDPR-friendly file sync, share and collaboration platform that serves as a Nextcloud replacement.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
  - [Back-up](#back-up)
  - [Security](#security)
  - [Migrating from Nextcloud AIO](#migrating-from-nextcloud-aio)


## Understanding the setup

The setup starts the following services:
- [OpenCloud](https://opencloud.eu) (files/sharing + built-in LDAP identity provider) at port `9863` — can be accessed in browser at [http://localhost:9863](http://localhost:9863). The upstream image bundles the file server, sharing, collaboration (WOPI endpoint under `/wopi` and `/collaboration`) and an in-process LDAP for users (`admin` is seeded from `IDM_ADMIN_PASSWORD` on first start).
- [Euro Office](https://github.com/EURO-office/DocumentServer) (document editor for `.docx`/`.xlsx`/`.pptx`/`.odt`/`.ods`/`.odp`) at port `9864` — reachable at [http://localhost:9864](http://localhost:9864). Romanian (`ro_RO`) + English (`en_US`/`en_GB`/`en_AU`/`en_CA`/`en_ZA`) dictionaries are baked into the image; the editor UI follows the browser locale.

Both services are bound to **`127.0.0.1` only** — a reverse proxy is required to expose them under `https://OC_DOMAIN` and `https://EURO_OFFICE_DOMAIN`.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in docker compose. [`.env.default`](.env.default) can be used as an example. All variables use their **container-native names** (what the opencloud/euro-office images actually read) and are loaded via `env_file`. Notable variables:

**Domains:**
- `OC_DOMAIN` — publicly-served hostname for OpenCloud (e.g. `cloud.example.com`); TLS terminated at the reverse proxy.
- `EURO_OFFICE_DOMAIN` — publicly-served hostname for the Euro Office editor (e.g. `euro-office.example.com`).

**Identity (built-in LDAP):**
- `IDM_ADMIN_PASSWORD` — initial admin password. **Must be set BEFORE first start**. After the first start the env value is ignored — use the OpenCloud Web UI to change the admin password.
- `IDM_CREATE_DEMO_USERS` — set `true` to also create demo users (only on first start).

**TLS / networking:**
- `OC_INSECURE` — `true` skips certificate validation toward Euro Office and the public URL (use when behind a self-signed / local reverse proxy); `false` validates certificates (use behind a trusted proxy).

**Localization:**
- `OC_DEFAULT_LANGUAGE` — default Web UI language (`ro` for Romanian, community-translated; `en` for English, fully maintained). Users can switch individually.

**Image:**
- `OC_DOCKER_IMAGE` / `OC_DOCKER_TAG` — defaults to `opencloudeu/opencloud-rolling:latest`. For production, pin to `opencloudeu/opencloud:<stable-tag>`.
- `EURO_OFFICE_DOCKER_IMAGE` / `EURO_OFFICE_DOCKER_TAG` — defaults to `ghcr.io/euro-office/documentserver:latest`.

**Storage (bind mounts — must exist and be owned `1000:1000`):**
- `OC_CONFIG_DIR` — config dir (`/etc/opencloud` in the container; default `/mnt/sda4/opencloud/config`).
- `OC_DATA_DIR` — data dir (`/var/lib/opencloud` in the container; default `/mnt/sda4/opencloud/data`).
- `OC_APPS_DIR` — web app assets (committed `./config/opencloud/apps`).

**Optional services / logging:**
- `START_ADDITIONAL_SERVICES` — comma-separated additional services (e.g. `notifications,antivirus`); `collaboration` is always started.
- `OC_LOG_LEVEL`, `OC_LOG_PRETTY`, `OC_LOG_COLOR`, `LOG_DRIVER` — logging.

**Sharing:**
- `OC_SHARING_PUBLIC_SHARE_MUST_HAVE_PASSWORD`, `OC_SHARING_PUBLIC_WRITEABLE_SHARE_MUST_HAVE_PASSWORD` — public link sharing controls.

**Password policy:** `OC_PASSWORD_POLICY_DISABLED`, `OC_PASSWORD_POLICY_MIN_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_LOWERCASE_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_UPPERCASE_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_DIGITS`, `OC_PASSWORD_POLICY_MIN_SPECIAL_CHARACTERS`.

**Optional SMTP (notifications service):**
- `NOTIFICATIONS_SMTP_HOST`, `NOTIFICATIONS_SMTP_PORT`, `NOTIFICATIONS_SMTP_SENDER`, `NOTIFICATIONS_SMTP_USERNAME`, `NOTIFICATIONS_SMTP_PASSWORD`, `NOTIFICATIONS_SMTP_AUTHENTICATION`, `NOTIFICATIONS_SMTP_ENCRYPTION`, `NOTIFICATIONS_SMTP_INSECURE` — leave blank to disable; add `notifications` to `START_ADDITIONAL_SERVICES` to enable.


## Running

### Pre-requisites

1. The stack runs on the docker network `home-lab-net`. To create it, run `make create-network` from the root of this repository [`self-hosting-cookbook`](../).
2. You need `docker` and `docker compose` installed on the host machine.
3. **A reverse proxy is mandatory** — the stack binds only to `127.0.0.1`. Point `https://OC_DOMAIN` → `127.0.0.1:9863` and `https://EURO_OFFICE_DOMAIN` → `127.0.0.1:9864`, with TLS terminated at the proxy. For the OpenCloud domain, also forward the WOPI paths `/wopi` and `/collaboration` (euro-office uses these URLs when opening documents).
4. Copy `.env.default` to `.env` and set at minimum `OC_DOMAIN`, `EURO_OFFICE_DOMAIN` and `IDM_ADMIN_PASSWORD`.
5. Run `make init-storage` once — it creates `/mnt/sda4/opencloud/{config,data}` (change `OC_CONFIG_DIR`/`OC_DATA_DIR` to match your layout) and chowns them to `1000:1000` so the opencloud container can write to them.

### Starting the stack

- `make pull` — pulls the OpenCloud + Euro Office images.
- `make init-storage` — creates the bind-mount dirs and chowns them to `1000:1000` (one-time, idempotent).
- `make run` — runs `init-storage`, then `docker compose down && docker compose up -d`.
- `make run-update` — `make pull` followed by `make run`.

After `make run`, reach OpenCloud at `http://localhost:9863` (or `https://OC_DOMAIN` through your reverse proxy) and log in as `admin` with the password you set in `IDM_ADMIN_PASSWORD`.

### Configure the stack

1. Log in as `admin` — **change the admin password via the OpenCloud UI** (Settings → profile). The env value is ignored after the first start.
2. Open a `.docx` / `.xlsx` / `.pptx` from OpenCloud — it should open in the Euro Office editor. Romanian or English spellcheck is available out of the box (dictionaries baked into the image); the editor UI follows the browser locale.
3. **(Optional) Pin the Euro Office JWT secret** for hardening. By default the image auto-generates and manages its own `JWT_SECRET` (matching upstream's `weboffice/euro-office.yml`). To pin a known secret:
   1. `openssl rand -hex 32` → put the value in `.env.default`/`env` as `EURO_OFFICE_JWT_SECRET=…` and uncomment the line.
   2. In `docker-compose.yml`, add `JWT_SECRET: ${EURO_OFFICE_JWT_SECRET}` under the `euro-office` service's `environment:` block.
   3. Re-run `make run-update` and **re-verify document editing**, because the WOPI proof key changes. If editing breaks, revert the env change.
4. **(Optional) Outgoing email (notifications).** Fill `NOTIFICATIONS_SMTP_*` vars and add `notifications` to `START_ADDITIONAL_SERVICES`, then `make run-update`.

### Back-up

The bind mounts `/mnt/sda4/opencloud/config` and `/mnt/sda4/opencloud/data` hold all persistent state (database, blob storage, config files written at first start). Back these up. Also keep a copy of `.env` so the admin password and SMTP credentials can be restored.

### Security

- **127.0.0.1-only ports**: `9863` and `9864` are NOT reachable from other hosts. Use a reverse proxy for HTTPS and consider fail2ban / IP allowlists at the proxy.
- **`IDM_ADMIN_PASSWORD`**: must be a strong, unique value set BEFORE first start. Change it via the UI immediately after first log-in (the env value is no longer applied after first boot).
- **`OC_INSECURE=true`**: disables certificate validation toward Euro Office and within OpenCloud. Use `false` in production (trusted proxy with valid certs); use `true` only for dev / self-signed local setups.
- **Euro Office is community / early-stage** — the upstream docs flag it as such. Track [opencloud-eu/opencloud-compose](https://github.com/opencloud-eu/opencloud-compose) for updates.
- **GDPR**: OpenCloud is on-prem, EU-based; data does not leave your host.

### Migrating from Nextcloud AIO

If you are replacing an existing Nextcloud AIO deployment (`nextcloud-aio-mastercontainer` and `nextcloud-*-aio-*` containers at e.g. `/mnt/esesdee/nextcloud/`):

1. **Back up your Nextcloud files first** (e.g. via the Nextcloud UI or by copying the data dir).
2. Confirm OpenCloud is running and you can reach it.
3. Dry-run the teardown: `./remove-nextcloud-aio.sh --dry-run` — it lists every container / volume / network it would touch.
4. Live teardown: `./remove-nextcloud-aio.sh` — stops the mastercontainer first (so it can't respawn inner containers), then removes every `nextcloud*` container, volume and the `nextcloud-aio` network. Host data directories are NOT removed; move/delete them manually once the backup is safe.

User accounts and Nextcloud app settings are **not** migrated — recreate accounts in OpenCloud (built-in LDAP) and re-share any links.
