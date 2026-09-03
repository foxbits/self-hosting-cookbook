This is the docker compose setup for a [VaultWarden](https://github.com/dani-garcia/vaultwarden) server, a community Bitwarden-compatible password manager backend written in Rust (works with all stock Bitwarden clients).

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
	- [Environment variables](#environment-variables)
- [Running](#running)
	- [Pre-requisites](#pre-requisites)
	- [Starting the stack](#starting-the-stack)
	- [Configure the stack](#configure-the-stack)
	- [Public HTTPS address](#public-https-address)
	- [First-run setup](#first-run-setup)
	- [Admin page protection model](#admin-page-protection-model)
	- [Back-up](#back-up)
	- [Physical copy of the master password](#physical-copy-of-the-master-password)
- [Security](#security)

## Understanding the setup

The setup starts the following services:
- [VaultWarden](https://github.com/dani-garcia/vaultwarden) at port `9864` - can be accessed in browser at [http://localhost:9864](http://localhost:9864) (see [Public HTTPS address](#public-https-address) — always use the https address in practice)

The stack is Postgres-backed: relational data lives in the `vaultwarden` database on the shared [`datastore-sql`](../datastore-sql/) PostgreSQL instance. The `./vw-data/` bind mount still holds attachments, the icon cache, the `rsa_key`, and `config.json` if the admin page ever writes one. No Redis/Valkey is involved — VaultWarden has built-in WebSocket notifications and a built-in job scheduler.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:

- `POSTGRES_USER` - PostgreSQL superuser name; must match the `datastore-sql` instance credentials (used for `create-db` and interpolated into the derived `DATABASE_URL`).
- `POSTGRES_PASSWORD` - PostgreSQL superuser password; must match the `datastore-sql` instance credentials. If it contains special characters (`@`, `:`, `/`, `?`, `#`, etc.), percent-encode them in the derived `DATABASE_URL` or libpq URI parsing breaks (e.g. `@` -> `%40`, `:` -> `%3A`, `/` -> `%2F`, `?` -> `%3F`, `#` -> `%23`).
- `DATABASE_URL` - not set in `.env`; derived in `docker-compose.yml` as `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@datastore-sql:5432/vaultwarden`.
- `DOMAIN` - (REQUIRED) public https URL of this instance, scheme + host, e.g. `https://vault.example.com`. Must exactly match the address clients use. See [Public HTTPS address](#public-https-address).
- `SIGNUPS_ALLOWED` - keep `false`. Users are created by temporarily enabling signups via the `/admin` panel toggle (never by flipping env vars), then disabling again. See [First-run setup](#first-run-setup).
- `INVITATIONS_ALLOWED` - keep `true` so admins can invite users while signups stay off. Invites REQUIRE working SMTP — without it they fail silently.
- `SHOW_PASSWORD_HINT` - keep `true` if you want users to put hints.
- `ADMIN_TOKEN` - must be an Argon2 PHC hash, NOT plaintext (plaintext in `.env` is readable via `docker inspect`). Primary path: set `ENABLE_ADMIN=true` and run `make generate-admin-token` from this directory — it prompts for a passphrase twice and writes the hash into `.env` automatically (skipped if a token is already set). Fallback: run `docker run --rm -it vaultwarden/server:latest /vaultwarden hash` yourself, or use the host `argon2` CLI, and paste the printed `$argon2id$...` string single-quoted into `.env`. No `$$` escaping needed (`env_file` values are passed literally). Leave empty to keep `/admin` fully disabled. See [Admin page protection model](#admin-page-protection-model).
- `ENABLE_ADMIN` - gates `make generate-admin-token` only (VaultWarden ignores it). Set `true` to allow automatic token generation; the target only writes when `ADMIN_TOKEN` is empty/missing/`CHANGE_ME` and never overwrites an existing token.
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_SECURITY` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_FROM_NAME` (+ optional `SMTP_TIMEOUT`) - (optional, but REQUIRED for organization invites, email verification, and email 2FA — invites fail silently without working SMTP).

## Running

### Pre-requisites

You will have to have `docker` and `docker compose` installed on the host machine.

The [`datastore-sql`](../datastore-sql/) PostgreSQL instance must be up and healthy first (this stack's `EXECUTION_ORDER` entry is placed after `datastore-sql`). Create the underlying home lab docker network once from the repo root with `make create-network` if you have not already.

Make sure that you setup the environment variables correctly: copy [`.env.default`](.env.default) to `.env`, then follow [First-run setup](#first-run-setup) step 1 (`ENABLE_ADMIN=true` + `make generate-admin-token` for `ADMIN_TOKEN`), and fill in `POSTGRES_USER` / `POSTGRES_PASSWORD` (matching `datastore-sql`) and `DOMAIN`.

### Starting the stack

Then use:
- `make pull` - to update the stack images to latest version
- `make run` - to just run the system (auto-generates `ADMIN_TOKEN` on first run via `generate-admin-token`, creates the `vaultwarden` database if missing via `create-db`, then basic docker compose up command; the very first run needs a terminal for the passphrase prompts)
- `make run-update` - to first update the stack (pull), and then run it (run)

VaultWarden will be available at [http://localhost:9864](http://localhost:9864) locally, but always use the https address from [Public HTTPS address](#public-https-address) in practice. At startup VaultWarden runs its Diesel migrations against the `vaultwarden` database automatically.

Extra targets:
- `make create-db` - creates the `vaultwarden` database on `datastore-sql` (idempotent, safe to re-run)
- `make delete-db` - drops the `vaultwarden` database on `datastore-sql` (destructive)
- `make generate-admin-token` - interactive helper that prompts for an admin passphrase twice and writes the Argon2 PHC hash into `.env` as `ADMIN_TOKEN` automatically (only when `ENABLE_ADMIN=true` and no token is set yet; never overwrites). Runs automatically on every `make run` / `make run-update` — a no-op unless it is a first run; invoke it standalone only to (re)generate outside the normal flow

### Configure the stack

See [First-run setup](#first-run-setup) for the ordered steps (first account, lock down signups, enable 2FA, optional SMTP).

### Public HTTPS address

HTTPS is REQUIRED, not optional. The Bitwarden web vault uses WebCrypto APIs that browsers only expose in secure contexts, so the vault will not work correctly over plain `http://` or a bare IP. U2F/FIDO2 security keys additionally require HTTPS, mobile clients require a properly chained certificate with working OCSP stapling, and Let's Encrypt issuance requires a DNS name (no bare IPs).

So: expose this service at a public DNS name with TLS termination in front of it (e.g. `https://vault.example.com` via your reverse proxy — Caddy / cloudflared / etc., same convention as `fusionauth`, `luna`, `opencloud`), set `DOMAIN` to EXACTLY that URL (scheme + host, no trailing path tricks), and never expose or test solely over `http://` or a bare IP except for throwaway local bring-up. Do NOT enable Rocket's built-in `ROCKET_TLS` — upstream considers it immature (RSA-only, no strict SNI); terminate TLS at the reverse proxy instead.

### First-run setup

1. Copy `.env.default` to `.env`. Fill in `POSTGRES_USER` / `POSTGRES_PASSWORD` (matching `datastore-sql`) and `DOMAIN` (public https URL).
2. Run `make run-update` from a terminal (the first run needs interaction): it prompts for an admin passphrase twice and writes the Argon2 hash into `.env` as `ADMIN_TOKEN` automatically (skipped on later runs; refused unless `ENABLE_ADMIN=true`), auto-creates the `vaultwarden` database on `datastore-sql`, and runs the Diesel migrations on startup. Fallback if you prefer it manual: run `docker run --rm -it vaultwarden/server:latest /vaultwarden hash` yourself or use the host `argon2` CLI, then paste the printed PHC string single-quoted into `.env`.
3. Log into `/admin` and toggle signups ON (General Settings — this writes `config.json`, so afterwards keep managing `SIGNUPS_ALLOWED` in `/admin`, or delete `config.json` to return to env-driven config; never flip env vars for this).
4. Register the first account through the public HTTPS URL via the normal signup form (`/admin` has NO create-user function — its only user path is Users → Invite, which needs SMTP).
5. Toggle signups OFF in `/admin`.
6. Log in as the user, enable 2FA / FIDO2 on the account, and verify WebSocket live-sync and attachments work.
7. Optionally configure SMTP in `.env` / the panel — a hard requirement for invites, email verification, and email 2FA.
8. Add a permanent Cloudflare WAF custom rule blocking `/admin*` from the public internet, and thereafter reach `/admin` only via a non-public path.
9. Note: the first user is NOT special — VaultWarden has no super-admin account flag; `/admin` is server-level and stands apart from user accounts.

### Admin page protection model

The `/admin` page has a layered protection model, and its default state is off:

- **Disabled unless explicitly enabled.** If `ADMIN_TOKEN` is not set, the panel is disabled — requests to `/admin` just return "The admin panel is disabled, please configure the 'ADMIN_TOKEN' variable to enable it". Out of the box the endpoint is inert, not a login page waiting to be brute-forced.
- **Token authentication.** The token must be an Argon2 PHC hash, not plaintext — generate it with the image's built-in `vaultwarden hash` command (`make generate-admin-token`) or the host `argon2` CLI. A plaintext token in compose / `.env` is readable by anyone who can `docker inspect`; a PHC hash is not reversible.
- **Short-lived sessions.** Entering the token grants a signed session cookie (~20 minutes), so the credential is not re-transmitted on every click. Nuance: changing the token from inside the panel itself does NOT deauthorize existing admin sessions — restart the container after rotating the token.
- **Rate limiting** on the login route (configurable via the `ADMIN_RATELIMIT_*` env vars), so brute-forcing the token form is throttled.
- **Network layer.** A Cloudflare WAF rule blocking `/admin*` (see [First-run setup](#first-run-setup)) means the form is not even reachable from the public internet. Tunnel + WAF block + Argon2 token is defense in depth; any one layer failing still leaves the others.

### Back-up

You must back up BOTH places — restoring only one yields a broken instance (database rows reference files in `vw-data/`):

1. The `vaultwarden` Postgres database (via the [`datastore-sql`](../datastore-sql/) backup procedure).
2. The `./vw-data/` bind mount (attachments, icon cache, `rsa_key`, and `config.json` if the admin page ever writes one). WARNING: if `config.json` exists, it takes precedence over environment variables — editing `.env` will then appear to have no effect.

Store encrypted copies off-host. Also back up `.env` (holds `ADMIN_TOKEN`, SMTP creds, `POSTGRES_PASSWORD`) to encrypted offline storage.

### Physical copy of the master password

> ⚠️ WRITE DOWN YOUR MASTER PASSWORD (AND 2FA RECOVERY CODE) ON PAPER AND STORE IT OFFLINE IN A SAFE PLACE. ⚠️
>
> VaultWarden is zero-knowledge: your master password decrypts your vault, and NEITHER the server admin NOR the `/admin` page can reset or recover it. Losing it means PERMANENT, IRREVERSIBLE LOSS of your entire vault contents. This cannot be softened: there is no "forgot password" that works without the master password. Every user of this instance must keep a physical emergency sheet.

## Security

- Keep `SIGNUPS_ALLOWED=false`, toggling it in `/admin` only to register new users, and keep `INVITATIONS_ALLOWED=true` only with working SMTP configured — otherwise anyone who can reach the instance can register, and invites fail silently.
- Guard `ADMIN_TOKEN` like a password: Argon2 PHC hash only (generate with `make generate-admin-token`), never commit a real value, restart the container after any rotation, and keep the Cloudflare WAF block on `/admin*` permanently (see [Admin page protection model](#admin-page-protection-model)).
- If `POSTGRES_PASSWORD` contains special characters, percent-encode them in the derived `DATABASE_URL` (see [Environment variables](#environment-variables)) or the database connection fails to parse.
- Consider fail2ban (or equivalent rate-limiting at the reverse proxy) in front of the login endpoints.
- Keep the `vaultwarden/server` image updated (`make run-update`) — it tracks upstream security fixes.
