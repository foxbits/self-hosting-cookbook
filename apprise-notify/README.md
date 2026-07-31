This is the docker compose setup for the official [Apprise API](https://appriseit.com/api/) (`caronc/apprise:latest`), a self-hosted notification gateway that can deliver to **Discord, Telegram, Slack, Email, Pushover, Ntfy, Gotify, Matrix, and 100+ other services** using a single unified URL syntax.

Other services on `home-lab-net` (for example [`actual-notify`](../actual-notify/)) can push notifications to this gateway over HTTP without having to manage their own per-target credentials.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
	- [Environment variables](#environment-variables)
- [Security](#security)
- [Running](#running)
	- [Pre-requisites](#pre-requisites)
	- [Starting the stack](#starting-the-stack)
	- [Sending a test notification](#sending-a-test-notification)
- [Back-up](#back-up)


## Understanding the setup

The setup starts **one service**:
- [The Apprise API server](https://appriseit.com/api/) at port `9862` — can be accessed in browser at [http://localhost:9862/](http://localhost:9862/) (the optional web UI is enabled by `APPRISE_ADMIN=y`).

It is the **stateless** notification gateway consumed by other services in this stack via HTTP. Internal service-to-service URL is `http://apprise-notify:8000`.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings. [`.env.default`](.env.default) can be used as an example. Possible variables:

- `APPRISE_STATEFUL_MODE`: enables both stateless and stateful usage. `simple` is the recommended setting for most deployments. The deployment docs at <https://appriseit.com/api/deployment/> describe all supported values.
- `APPRISE_WORKER_COUNT`: number of gunicorn workers serving the API. `1` is plenty for personal/self-hosted usage.
- `APPRISE_ADMIN`: `y` to enable the optional config web UI at `/`; set to anything else to disable it.
- `APPRISE_BASE_URL`: leave empty when serving on port 8000 directly. Set to e.g. `/apprise` only when serving the API under a subpath behind a reverse proxy.
- `PUID` / `PGID` (optional): user/group IDs for file ownership on bind-mounted directories. Uncomment in `.env.default` and set to your host uid/gid (e.g. `1000`) if you want the container process to write `/config` and `/attach` as your host user.


## Security

> ⚠️ **The Apprise API does not implement authentication.** It is by design.

This means **anyone who can reach the HTTP endpoint can send notifications using whatever Apprise URLs you have configured in it** (or, in stateless mode, specified in their request body). Therefore:

- The host port `9862` is published **for local testing only**. Do **not** reverse-proxy this service to the public internet unless you put a reverse proxy with auth in front of it (the Apprise docs show how to inject Nginx `location-override.conf` + `.htpasswd` for this).
- The realistic way to use this service is on `home-lab-net` only, where it is reached by trusted internal services (such as `actual-notify`). Internal service-to-service traffic uses `http://apprise-notify:8000` and never touches the public network.
- If you enable `APPRISE_ADMIN=y` and the optional web UI, treat the URL as private: anyone with network access to the UI can add or modify stored configuration (URLs, attachments, plugins).
- Storing secret URLs (like Discord webhook tokens) in the stateful config means those secrets are at-rest in `./apprise_config/**` — protect those files accordingly (host permissions, encrypted backups, etc.). Stateless usage avoids storing secrets here at all (recommended when only one service uses this gateway).

Recommended hardening posture: keep the service on `home-lab-net` only, disable or restrict exposure of the host port `9862` at the firewall level, and prefer stateless usage so no long-lived secrets accumulate in `./apprise_config`.


## Running

### Pre-requisites

1. The underlying home lab docker network must exist; create it once with `make create-network` from the repository root.
2. `docker` and `docker compose` are installed on the host.
3. Copy [`.env.default`](.env.default) to [`.env`](.env) and edit it (mainly to confirm `APPRISE_ADMIN=y` if you want the web UI, and to set `APPRISE_BASE_URL=` if you proxy under a subpath).

### Starting the stack

Use:
- `make pull` — refresh the Apprise image to the latest stable tag.
- `make run` — restart the stack from the current local image.
- `make run-update` — first pull, then run (the standard update path).

The Apprise API will be available at [http://localhost:9862/](http://localhost:9862/) (web UI, if enabled) and on the internal docker network as `http://apprise-notify:8000/` for other services.

### Sending a test notification

Quick smoke test (stateless — the URL is supplied in the request body, no setup needed on the Apprise server):

```sh
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "urls": "discord://webhook_id/webhook_token",
    "title": "Apprise API smoke test",
    "body": "Sent from the apprise-notify stack."
  }' \
  http://localhost:9862/notify
```

See <https://appriseit.com/api/usage/> for the full request shape (`format`, `type`, attachments, payload-mapping hooks, etc.).

If you enabled `APPRISE_ADMIN=y`, you can also browse to `/` and save URLs under a `{KEY}`, then send to `POST /notify/{KEY}` to keep secrets off your clients.


## Back-up

Bind-mounted persistent state lives under `./apprise_config/` and `./apprise_attach/` (relative to where the stack is running). These two directories are what you need to back up.

The image itself and environment configuration live in git (the cookbook service files plus your gitignored `.env`).
