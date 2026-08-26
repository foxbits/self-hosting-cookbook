This is the docker compose setup for [OpenCloud](https://opencloud.eu) — a self-hosted, GDPR-friendly file sync and share platform that serves as a Nextcloud replacement (file storage only; no bundled document editor).

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Setting up FusionAuth as the external IdP](#setting-up-fusionauth-as-the-external-idp)
  - [1. Tenant and issuer URL](#1-tenant-and-issuer-url)
  - [2. Disable OpenCloud's built-in IdP](#2-disable-openclouds-built-in-idp)
  - [3. Create the FusionAuth application (public client + PKCE)](#3-create-the-fusionauth-application-public-client--pkce)
  - [4. Redirect URIs](#4-redirect-uris)
  - [5. Claims used by OpenCloud](#5-claims-used-by-opencloud)
  - [6. Role assignment (making a user admin)](#6-role-assignment-making-a-user-admin)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
  - [Back-up](#back-up)
  - [Security](#security)
  - [Migrating from Nextcloud AIO](#migrating-from-nextcloud-aio)


## Understanding the setup

The setup starts the following services:
- [OpenCloud](https://opencloud.eu) (files/sharing) at port `9863` — can be accessed in browser at [http://localhost:9863](http://localhost:9863). The upstream image bundles the file server, sharing, and a built-in in-process LDAP IdP. **This stack disables the built-in IdP by default** (`OC_EXCLUDE_RUN_SERVICES=idp`) and expects you to delegate authentication to an **external OIDC provider** — the default/recommended one being the [`fusionauth`](../fusionauth/) stack in this repo. Users are auto-provisioned from the IdP on first login; see [Setting up FusionAuth as the external IdP](#setting-up-fusionauth-as-the-external-idp).

The service is bound to **`127.0.0.1` only** — a reverse proxy is required to expose it under `https://OC_DOMAIN`.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in docker compose. [`.env.default`](.env.default) can be used as an example. All variables use their **container-native names** (what the opencloud image actually reads) and are loaded via `env_file`. Notable variables:

**Domains:**
- `OC_DOMAIN` — publicly-served hostname for OpenCloud (e.g. `cloud.example.com`); TLS terminated at the reverse proxy.

**Identity (built-in LDAP — disabled by default):**

The built-in in-process LDAP IdP is excluded by default via `OC_EXCLUDE_RUN_SERVICES=idp` so that authentication is delegated to an external OIDC provider (see below). These `IDM_*` vars **only apply if you remove `idp` from `OC_EXCLUDE_RUN_SERVICES`** and run the built-in IdP instead:
- `IDM_ADMIN_PASSWORD` — initial admin password. **Must be set BEFORE first start**. After the first start the env value is ignored — use the OpenCloud Web UI to change it.
- `IDM_CREATE_DEMO_USERS` — set `true` to also create demo users (only on first start).

**Authentication (external OIDC — default, with FusionAuth):**

This stack is wired to delegate auth to an external OIDC provider. The [`fusionauth`](../fusionauth/) stack in this repo is the default/reference setup; any spec-compliant OIDC provider works. See [Setting up FusionAuth as the external IdP](#setting-up-fusionauth-as-the-external-idp) for the full end-to-end configuration.

- `OC_OIDC_ISSUER` — the **full tenant-scoped issuer URL** of your IdP. OIDC discovery appends `/.well-known/openid-configuration` to this. For FusionAuth this MUST include the tenant ID (e.g. `https://auth.example.com/<tenant-id>`). The `iss` claim in issued tokens must match this exactly.
- `IDP_DOMAIN` — the IdP base **host** (e.g. `auth.example.com`). Must match the host of `OC_OIDC_ISSUER`.
- `OC_OIDC_CLIENT_ID` — the OIDC client ID OpenCloud presents (the FusionAuth application's client ID).
- `OC_EXCLUDE_RUN_SERVICES` — services to exclude from startup; defaults to `idp` (disables the built-in IdP in favor of the external OIDC provider). Remove `idp` here only if you want the built-in LDAP instead.

Token validation (required):
- `PROXY_OIDC_ACCESS_TOKEN_VERIFY_METHOD=jwt` — validate access tokens as JWTs locally (against the IdP's JWKS).
- `PROXY_OIDC_REWRITE_WELLKNOWN=true` — rewrite the discovered well-known config so endpoints/issuer resolve correctly behind a reverse proxy.

User mapping (recommended):
- `PROXY_USER_OIDC_CLAIM` — OIDC claim to map to the OpenCloud user id (default `preferred_username`).
- `PROXY_USER_CS3_CLAIM` — CS3 (OpenCloud) claim to match it against (default `username`).

Auto-provision (create OpenCloud accounts on first login):
- `PROXY_AUTOPROVISION_ACCOUNTS=true` — enable auto-provisioning.
- `PROXY_AUTOPROVISION_CLAIM_USERNAME`, `PROXY_AUTOPROVISION_CLAIM_EMAIL`, `PROXY_AUTOPROVISION_CLAIM_DISPLAYNAME`, `PROXY_AUTOPROVISION_CLAIM_GROUPS` — which OIDC claims feed the username, email, display name and group memberships respectively.

Role assignment (drive OpenCloud roles from IdP claims; see [Role assignment](#6-role-assignment-making-a-user-admin)):
- `PROXY_ROLE_ASSIGNMENT_DRIVER=oidc` — read roles from an OIDC claim instead of giving everyone the default `user` role.
- `PROXY_ROLE_ASSIGNMENT_OIDC_CLAIM` — claim to read roles from (default `roles`).
- `GRAPH_ASSIGN_DEFAULT_USER_ROLE=false` — do **not** pre-assign the `user` role before the OIDC mapping runs (set this when using the role driver).

Logout:
- `WEB_OPTION_LOGOUT_URL` — the IdP logout URL the profile page redirects to (e.g. `https://auth.example.com/oauth2/logout`).

WebFinger (optional — needed for desktop/mobile clients, so most likely needed):
- `WEBFINGER_DESKTOP_OIDC_CLIENT_ID`, `WEBFINGER_ANDROID_OIDC_CLIENT_ID`, `WEBFINGER_IOS_OIDC_CLIENT_ID`.
- `WEBFINGER_WEB_OIDC_CLIENT_SCOPES` — scopes advertised for the web client at `/.well-known/webfinger`. Desktop/mobile defaults already include `offline_access`; the web entry does not. Set to match `WEB_OIDC_SCOPE` so WebFinger discovery stays consistent (harmless if they differ).

OIDC scopes (refresh tokens for the browser):
- `WEB_OIDC_SCOPE` — the **authoritative** OIDC scope string used by the embedded web client (the JS app in your browser) and sent in the actual `/authorize` request to the IdP. Defaults to `openid profile email`. To make the browser receive a refresh token (so reloads / background tabs don't kick you back to the IdP), add `offline_access`: `WEB_OIDC_SCOPE="openid profile email offline_access"`. The IdP application for the web client must also have refresh-token issuance enabled (`Refresh Token grant` + `Generate refresh tokens`) or it will silently drop `offline_access`.

**TLS / networking:**
- `OC_INSECURE` — `true` skips certificate validation toward the public URL (use when behind a self-signed / local reverse proxy); `false` validates certificates (use behind a trusted proxy).

**Localization:**
- `OC_DEFAULT_LANGUAGE` — default Web UI language (`ro` for Romanian, community-translated; `en` for English, fully maintained). Users can switch individually.

**Image:**
- `OC_DOCKER_IMAGE` / `OC_DOCKER_TAG` — defaults to `opencloudeu/opencloud-rolling:latest`. For production, pin to `opencloudeu/opencloud:<stable-tag>`.

**Storage (bind mounts — must exist and be owned `1000:1000`):**
- `SH_OC_CONFIG_DIR` — host path for the config dir (`/etc/opencloud` in the container; default `/mnt/sda4/opencloud/config`). Prefixed `SH_OC_*` so the opencloud container (which reads `OC_CONFIG_DIR` natively) does not pick the host path up and try to `mkdir` it inside the container.
- `SH_OC_DATA_DIR` — host path for the data dir (`/var/lib/opencloud` in the container; default `/mnt/sda4/opencloud/data`).
- `SH_OC_APPS_DIR` — host path for web app assets (committed `./config/opencloud/apps`).

**Optional services / logging:**
- `START_ADDITIONAL_SERVICES` — comma-separated additional services (e.g. `notifications,antivirus`).
- `OC_LOG_LEVEL`, `OC_LOG_PRETTY`, `OC_LOG_COLOR`, `LOG_DRIVER` — logging.

**Sharing:**
- `OC_SHARING_PUBLIC_SHARE_MUST_HAVE_PASSWORD`, `OC_SHARING_PUBLIC_WRITEABLE_SHARE_MUST_HAVE_PASSWORD` — public link sharing controls.

**Password policy:** `OC_PASSWORD_POLICY_DISABLED`, `OC_PASSWORD_POLICY_MIN_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_LOWERCASE_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_UPPERCASE_CHARACTERS`, `OC_PASSWORD_POLICY_MIN_DIGITS`, `OC_PASSWORD_POLICY_MIN_SPECIAL_CHARACTERS`.

**Optional SMTP (notifications service):**
- `NOTIFICATIONS_SMTP_HOST`, `NOTIFICATIONS_SMTP_PORT`, `NOTIFICATIONS_SMTP_SENDER`, `NOTIFICATIONS_SMTP_USERNAME`, `NOTIFICATIONS_SMTP_PASSWORD`, `NOTIFICATIONS_SMTP_AUTHENTICATION`, `NOTIFICATIONS_SMTP_ENCRYPTION`, `NOTIFICATIONS_SMTP_INSECURE` — leave blank to disable; add `notifications` to `START_ADDITIONAL_SERVICES` to enable.


## Setting up FusionAuth as the external IdP

This stack delegates authentication to an external OIDC provider. The reference setup is the [`fusionauth`](../fusionauth/) stack in this repo — the steps below describe wiring it to OpenCloud. The same flow applies to any spec-compliant OIDC provider (Keycloak, Authentik, etc.) with the equivalent settings.

### 1. Tenant and issuer URL

FusionAuth is multi-tenant and the OIDC discovery endpoint is **tenant-scoped**: the tenant ID must appear in the issuer. Format:

```
# v1.46.0+ — spec-compliant (tenant ID as prefix):
https://auth.example.com/<tenant-id>/.well-known/openid-configuration
```

OIDC discovery takes the **issuer URL** and appends `/.well-known/openid-configuration`, so set `OC_OIDC_ISSUER` to the full tenant-scoped issuer:

```bash
OC_OIDC_ISSUER=https://auth.example.com/<tenant-id>
```

Then in **FusionAuth → Tenants → your tenant → JWT Settings**, make sure the **Issuer** field equals `OC_OIDC_ISSUER` **exactly** — including the `https://` scheme and the tenant-id path (e.g. `https://auth.example.com/<tenant-id>`). The `iss` claim in issued tokens and the `issuer` field in the well-known config must both match `OC_OIDC_ISSUER`, or token validation fails. **This is NOT correct by default** — FusionAuth's default issuer is the bare hostname (e.g. `auth.example.com` without scheme or tenant path), which OpenCloud will reject with `issuer did not match the issuer returned by provider`. Verify by opening `https://auth.example.com/<tenant-id>/.well-known/openid-configuration` and checking the `issuer` field.

The OAuth endpoints (`/oauth2/authorize`, `/oauth2/token`, `/oauth2/logout`, `/oauth2/userinfo`) are **root-level** (no tenant ID in the path) — the tenant is resolved from the `client_id`, which belongs to an application, which belongs to a tenant. OpenCloud discovers these automatically from the well-known config, so you do not set them individually.

`WEB_OPTION_LOGOUT_URL` points to the root-level logout endpoint:

```bash
WEB_OPTION_LOGOUT_URL=https://auth.example.com/oauth2/logout
```

**Enable CORS in FusionAuth (required).** OpenCloud's web client is a browser SPA on a different origin (`https://OC_DOMAIN`) than the IdP, so it fetches the well-known config and token/userinfo endpoints cross-origin. FusionAuth's CORS filter is **disabled by default**, which blocks these requests (`Access-Control-Allow-Origin` missing). Enable it in **Settings → System → CORS**:

| Setting | Value |
|---|---|
| **Enable CORS** | ✅ on |
| **Allowed origins** | `https://cloud.example.com` (your `OC_DOMAIN`; add `http://localhost:9863` for local testing) |
| **Allowed methods** | `GET`, `POST`, `OPTIONS` |
| **Allowed headers** | `Content-Type`, `Accept`, `Authorization` |
| **Include credentials in CORS requests** | ✅ on |

CORS in FusionAuth is a **system-wide** setting (not per-application or per-tenant). Additionally, on the FusionAuth **Application → OAuth tab**, set **Authorized request origin URLs** to the same `https://cloud.example.com` — this is a separate control that gates the hosted login page origin check (distinct from the ACAO filter, but both are needed for a browser PKCE client).

### 2. Disable OpenCloud's built-in IdP

Excluding the internal `idp` service prevents the built-in LDAP (and its seeded `admin` user) from starting, so users come from the external IdP:

```bash
OC_EXCLUDE_RUN_SERVICES=idp
```

This is already the default in `.env.default`. When the built-in IdP is excluded, **no `admin` user is bootstrapped** — users are auto-provisioned from FusionAuth on first login (`PROXY_AUTOPROVISION_ACCOUNTS=true`), and admin rights are granted via [role assignment](#6-role-assignment-making-a-user-admin). The admin user is still created in the internal LDAP, but it is useless.

### 3. Create the FusionAuth application (public client + PKCE)

OpenCloud's clients (Web, Desktop, Android, iOS) are implemented as **public clients** using the **authorization-code flow with PKCE**, so the IdP must support that flow. FusionAuth does not have a single "Public/Confidential" toggle — the client type is set via the **Client Authentication** and **PKCE** options on the Application's **OAuth** tab.

**Client Authentication** (available since v1.28.0):

| Value | Behavior | Client type |
|---|---|---|
| `Required` (default) | `client_secret` always required at the token endpoint | Confidential |
| `Not required` | `client_secret` optional | Public |
| `Not required when using PKCE` | `client_secret` required **unless** a valid PKCE `code_verifier` is sent | Public (with PKCE) |

**PKCE** (since v1.28.0):

| Value | Behavior |
|---|---|
| `Not required` (default) | `code_verifier` optional |
| `Required` | `code_verifier` always required |
| `Not required when using client authentication` | PKCE required unless `client_secret` is sent |

Recommended combination for OpenCloud:

| Setting | Value | Why |
|---|---|---|
| **Client Authentication** | `Not required when using PKCE` | No client secret needed, but still enforces PKCE at the token endpoint |
| **PKCE** | `Required` | OpenCloud always sends `code_verifier` — enforce it |
| **Authorization Code grant** | ✅ Enabled | OpenCloud uses the auth-code flow |
| **Refresh Token grant** | ✅ Enabled | Needed for `offline_access` (desktop/mobile clients) |
| **Generate refresh tokens** | ✅ Enabled | Required so refresh tokens are issued when `offline_access` is requested |

When **Client Authentication** is anything other than `Required`, the client secret is effectively unused (regenerating it has no effect).

You need **one application per OpenCloud client** (each has its own client ID). If you only use the web client, a single application with client ID `web` and scopes `openid profile email` is enough.

| OpenCloud client | Client ID | Required scopes |
|---|---|---|
| Web | `web` | `openid profile email` |
| Desktop | `OpenCloudDesktop` | `openid profile email offline_access` |
| Android | `OpenCloudAndroid` | `openid profile email offline_access` |
| iOS | `OpenCloudIOS` | `openid profile email offline_access` |

Set `OC_OIDC_CLIENT_ID` to the web client's client ID. Be careful that in FusionAuth the client id is the GUID not the visual name (e.g. not the 'web').

### 4. Redirect URIs

Each application needs its authorized redirect URI(s). The mobile/desktop clients use these exact values:

| Client | Client ID | Authorized redirect URL(s) | URL validation |
|---|---|---|---|
| **Web** | *(your web client ID)* | `https://cloud.example.com/*` | **Allow wildcards** |
| **Desktop** | `OpenCloudDesktop` | `http://127.0.0.1:*` and `http://localhost:*` | **Allow wildcards** |
| **Android** | `OpenCloudAndroid` | `oc://android.opencloud.eu` | Exact match |
| **iOS** | `OpenCloudIOS` | `oc://ios.opencloud.eu` | Exact match |


The desktop app spins up a temporary local HTTP server on a **random port** to receive the callback, so the runtime URI is e.g. `http://localhost:54321/`. To accept this, set **URL validation** to **Allow wildcards** (FusionAuth v1.43.0+) on the `OpenCloudDesktop` application and add `http://127.0.0.1:*` + `http://localhost:*` (the `*` matches the port).

### 5. Claims used by OpenCloud

OpenCloud reads the following OIDC claims (defaults in `.env.default`):

| OpenCloud mapping | OIDC claim | FusionAuth behavior |
|---|---|---|
| Username (`PROXY_USER_OIDC_CLAIM` / `PROXY_AUTOPROVISION_CLAIM_USERNAME`) | `preferred_username` | Present in access + ID tokens since v1.5.0 |
| Email (`PROXY_AUTOPROVISION_CLAIM_EMAIL`) | `email` | Present with the `email` scope |
| Display name (`PROXY_AUTOPROVISION_CLAIM_DISPLAYNAME`) | `name` | **ID token only** by default — not in the access token |
| Roles (`PROXY_ROLE_ASSIGNMENT_OIDC_CLAIM`) | `roles` | Present in the **access token** as an array; **removed from the ID token in v1.24.0** |

**Caveats under FusionAuth v1.50.0+ with Scope handling policy = `Strict`:**
- `preferred_username` is dropped from the access token, and only appears in the ID token when the `profile` scope is requested.
- `email` requires the `email` scope.
- `name` requires the `profile` scope and still only lands in the ID token.

Because OpenCloud validates the **access token** as a JWT (`PROXY_OIDC_ACCESS_TOKEN_VERIFY_METHOD=jwt`), the `name` claim is not in the access token by default. Either:
- keep `PROXY_OIDC_SKIP_USER_INFO=false` (the default) so OpenCloud also fetches claims from the userinfo endpoint (where `name` is available), or
- add a **JWT Populate Lambda** in FusionAuth to copy `name` into the access token.

The `roles` claim (used for role assignment below) is in the **access token**, so role-based assignment works with JWT validation. The default web scopes `openid profile email` cover `preferred_username` and `email` in the ID token.

### 6. Role assignment (making a user admin)

By default OpenCloud assigns the `user` role to everyone. To drive roles from FusionAuth claims (e.g. to make your user an admin automatically on login), enable the OIDC role driver:

```bash
PROXY_ROLE_ASSIGNMENT_DRIVER=oidc
PROXY_ROLE_ASSIGNMENT_OIDC_CLAIM=roles
GRAPH_ASSIGN_DEFAULT_USER_ROLE=false
```

OpenCloud's **default role mapping** expects a `roles` claim with these values:

| Claim value in `roles` | OpenCloud role |
|---|---|
| `opencloudAdmin` | `admin` |
| `opencloudSpaceAdmin` | `spaceadmin` |
| `opencloudUser` | `user` |
| `opencloudGuest` | `user-light` |

FusionAuth **automatically emits assigned application roles as a `roles` array** in the JWT access token, so no lambda is needed. Setup in FusionAuth, for each OpenCloud application:

1. Application → **Roles** tab → create roles named exactly `opencloudAdmin` (set as superseeding), `opencloudSpaceAdmin`, `opencloudUser` (set as default role), `opencloudGuest`.
2. **Users** → your user → **Registrations** tab → register them to the OpenCloud application(s) with the **`opencloudAdmin`** role assigned.

FusionAuth will include `"roles": ["opencloudAdmin"]` in the access token, and OpenCloud's default `oidc` role mapper maps it to the `admin` role.

Note: do this only for your users, let the other users go to the default roles. And do this for all the applications created to allow access on all platforms.

**Important details:**
- A user can only have **one** OpenCloud role — the first matching mapping in the list wins. If a user has both `opencloudAdmin` and `opencloudUser`, they get `admin`.
- If a user's claim values don't match **any** mapping, they **cannot log in** (an error is logged and access is denied). Make sure every user who should be able to log in has at least `opencloudUser` assigned in FusionAuth.
- `GRAPH_ASSIGN_DEFAULT_USER_ROLE=false` prevents OpenCloud from pre-assigning the `user` role before the OIDC mapping runs.

Full flow:

```
User logs in via FusionAuth
  → FusionAuth issues JWT with "roles": ["opencloudAdmin"]
  → OpenCloud proxy reads the "roles" claim
  → Maps "opencloudAdmin" → OpenCloud "admin" role
  → User gets admin privileges in OpenCloud
```


## Running

### Pre-requisites

1. The stack runs on the docker network `home-lab-net`. To create it, run `make create-network` from the root of this repository [`self-hosting-cookbook`](../).
2. You need `docker` and `docker compose` installed on the host machine.
3. **A reverse proxy is mandatory** — the stack binds only to `127.0.0.1`. Point `https://OC_DOMAIN` → `127.0.0.1:9863`, with TLS terminated at the proxy.
4. **An external OIDC provider is required** (the built-in IdP is disabled by default). The reference setup is the [`fusionauth`](../fusionauth/) stack — stand it up first, then configure it as described in [Setting up FusionAuth as the external IdP](#setting-up-fusionauth-as-the-external-idp).
5. Copy `.env.default` to `.env` and set at minimum `OC_DOMAIN`, `OC_OIDC_ISSUER`, `OC_OIDC_CLIENT_ID`, `IDP_DOMAIN` (and the FusionAuth application/client setup matching those values).
6. Run `make init-storage` once — it creates `/mnt/sda4/opencloud/{config,data}` (change `SH_OC_CONFIG_DIR`/`SH_OC_DATA_DIR` to match your layout) and chowns them to `1000:1000` so the opencloud container can write to them.

### Starting the stack

- `make pull` — pulls the OpenCloud image.
- `make init-storage` — creates the bind-mount dirs and chowns them to `1000:1000` (one-time, idempotent).
- `make run` — runs `init-storage`, then `docker compose down && docker compose up -d`.
- `make run-update` — `make pull` followed by `make run`.

After `make run`, reach OpenCloud at `https://OC_DOMAIN` through your reverse proxy. Log in is via your external IdP — the first OIDC login auto-provisions your OpenCloud account, and your role is taken from the `roles` claim if [role assignment](#6-role-assignment-making-a-user-admin) is enabled. (If you re-enabled the built-in IdP instead, log in as `admin` with `IDM_ADMIN_PASSWORD`.)

### Configure the stack

1. **Authentication** is delegated to your external IdP — complete [Setting up FusionAuth as the external IdP](#setting-up-fusionauth-as-the-external-idp) (tenant issuer, public+PKCE application, redirect URIs, roles). First login auto-provisions your user; assign `opencloudAdmin` in FusionAuth to become admin. If you instead run the built-in IdP, log in as `admin` and **change the admin password via the OpenCloud UI** (Settings → profile) — the env value is ignored after the first start.
2. **(Optional) Outgoing email (notifications).** Fill `NOTIFICATIONS_SMTP_*` vars and add `notifications` to `START_ADDITIONAL_SERVICES`, then `make run-update`.

### Back-up

OpenCloud does **not** use a database — all state is persisted in the filesystem. The bind mounts `/mnt/sda4/opencloud/config` (`SH_OC_CONFIG_DIR`, `/etc/opencloud` in the container — secrets, `jwt_secret`, signing keys) and `/mnt/sda4/opencloud/data` (`SH_OC_DATA_DIR`, `/var/lib/opencloud` — file content + xattr metadata via the default PosixFS driver, plus embedded NATS JetStream under `nats/`, the bleve search index under `search/`, and thumbnails under `thumbnails/`) hold all persistent state. Back these up. Also keep a copy of `.env` so the OIDC issuer/client config and SMTP credentials can be restored — and back up your FusionAuth instance (see [`fusionauth`](../fusionauth/) → Back-up), since it holds all user accounts and roles.

### Security

- **127.0.0.1-only port**: `9863` is NOT reachable from other hosts. Use a reverse proxy for HTTPS and consider fail2ban / IP allowlists at the proxy.
- **Authentication is external**: with the default `OC_EXCLUDE_RUN_SERVICES=idp`, no built-in `admin` user exists — every account comes from your OIDC provider. The security of OpenCloud logins is therefore the security of your FusionAuth (or other IdP) tenant: enforce MFA, strong password policy, and email verification there. Keep `PROXY_OIDC_ACCESS_TOKEN_VERIFY_METHOD=jwt` so tokens are validated locally against the IdP's JWKS rather than trusted blindly.
- **Role gating**: when `PROXY_ROLE_ASSIGNMENT_DRIVER=oidc` + `GRAPH_ASSIGN_DEFAULT_USER_ROLE=false` are set, users whose `roles` claim matches **no** mapping are denied login. Make sure every intended user has at least `opencloudUser` assigned in FusionAuth.
- **`IDM_ADMIN_PASSWORD`** (only if you run the built-in IdP): must be a strong, unique value set BEFORE first start; change it via the UI immediately after first log-in (the env value is no longer applied after first boot).
- **`OC_INSECURE=true`**: disables certificate validation within OpenCloud. Use `false` in production (trusted proxy with valid certs); use `true` only for dev / self-signed local setups.
- **GDPR**: OpenCloud is on-prem, EU-based; data does not leave your host.

### Migrating from Nextcloud AIO

If you are replacing an existing Nextcloud AIO deployment (`nextcloud-aio-mastercontainer` and `nextcloud-*-aio-*` containers at e.g. `/mnt/esesdee/nextcloud/`):

1. **Back up your Nextcloud files first** (e.g. via the Nextcloud UI or by copying the data dir).
2. Confirm OpenCloud is running and you can reach it.
3. Dry-run the teardown: `./remove-nextcloud-aio.sh --dry-run` — it lists every container / volume / network it would touch.
4. Live teardown: `./remove-nextcloud-aio.sh` — stops the mastercontainer first (so it can't respawn inner containers), then removes every `nextcloud*` container, volume and the `nextcloud-aio` network. Host data directories are NOT removed; move/delete them manually once the backup is safe.

User accounts and Nextcloud app settings are **not** migrated — recreate accounts in your external IdP (FusionAuth) and re-share any links.
