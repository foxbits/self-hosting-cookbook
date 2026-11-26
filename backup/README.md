This is the docker compose setup for a per-service backup stack built on [restic](https://restic.net/) and [rclone](https://rclone.org/), storing an encrypted, deduplicated repository on iCloud Drive and sending Discord notifications through the [Apprise CLI](https://appriseit.com/cli/).

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [What is backed up](#what-is-backed-up)
  - [Service catalog](#service-catalog)
- [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [iCloud and rclone](#icloud-and-rclone)
  - [First run and trial](#first-run-and-trial)
  - [Automatic schedule](#automatic-schedule)
  - [Manual backups](#manual-backups)
- [Restore](#restore)
- [Back-up](#back-up)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Validation notes](#validation-notes)

## Understanding the setup

The stack starts **one container**, `backup`, with **no published host port**. It joins `home-lab-net` so it can reach `datastore-sql`, and it uses the host Docker socket to stop and restart the small services that cannot be safely copied while running.

The container contains:

- a Python package (`src/backup_runner/`) for orchestration, validation, locking, stop/start and notifications;
- the JSON service catalog (`services.json`), mounted read-only at `/etc/backup/services.json`;
- `restic` for encrypted, deduplicated snapshots and retention;
- `rclone` for the iCloud Drive remote;
- the PostgreSQL client tools for logical dumps;
- the Docker CLI for stop/start operations;
- the Apprise CLI for Discord notifications;
- `supercronic` for the container-friendly cron schedule.

Every service is a separate restic snapshot tagged `service:<name>`. A single repository is used, so identical data is deduplicated across services. If a run is interrupted, the next container start restarts any containers the backup had stopped.

The first backup of `immich` or `opencloud` can take a long time and saturate the home upload link. Run those manually first and let them finish before enabling the daily schedule; the lock prevents a second run from overlapping if the first one lasts more than a day.

### What is backed up

| Service | State | Method | Runtime handling |
| --- | --- | --- | --- |
| `actual` | `actual/data`, `actual/.env` | restic | stop `actual_server` |
| `arr-stack` | `arr-stack/config` (excluding `jackett-downloads`), `.env` | restic | stop `radarr`, `sonarr`, `jackett` |
| `configs` | every service `.env` and the repo-root `.env` | restic | none |
| `datastore-sql` | PostgreSQL globals and all databases | `pg_dumpall` | none; the raw `postgres_data` volume is not copied |
| `fusionauth` | database `fusionauth`, `fusionauth_config` volume, `kickstart/`, `plugins/`, `.env` | `pg_dump -Fc` + restic | none |
| `immich` | database `immich`, uploads at `UPLOAD_LOCATION`, `.env` | `pg_dump -Fc` + restic | online; `model-cache` excluded |
| `luna` | database `openwebui`, `luna_openwebui-data` volume, `.env` | `pg_dump -Fc` + restic | online |
| `opencloud` | `SH_OC_CONFIG_DIR`, `SH_OC_DATA_DIR`, `opencloud/config/`, `.env` | restic (xattrs preserved) | online |
| `portainer` | `portainer_data` volume | restic | stop `portainer` |
| `vaultwarden` | database `vaultwarden`, `vw-data/`, `.env` | `pg_dump -Fc` + restic | online |
| `agents-stack` | `searxng/core-config`, `camofox` profiles/cookies/uploads, `gpt-researcher-data`, `.env` | restic | stop `camofox` briefly |

Not backed up by default:

- `beszel` metrics/agent data (rebuildable; `.env` is captured by `configs`);
- `datastore-memory` (Valkey is a cache with `allkeys-lru`);
- `jenkins` controller/agent volumes and `.env` data (`.env` is captured by `configs`; enable later if needed);
- `plex-server` metadata, transcodes and media libraries (`.env` is captured by `configs`);
- `crw` and `open-crawl` (stateless; `.env` is captured by `configs`);
- media libraries, caches, ML model caches, SearXNG cache, camofox traces and Docker images.

PostgreSQL is never copied at the file level while running. The backup uses `pg_dump -Fc` per service and `pg_dumpall` for the full cluster. A database dump and the related file snapshot are taken sequentially, not as one atomic cross-subsystem transaction; stop the service first if you need strict consistency for a particular restore.

### Service catalog

The per-service definitions live in [`services.json`](services.json), which is tracked in git and mounted read-only at `/etc/backup/services.json`. No shell script is needed for a new service.

Each entry has:

| Field | Meaning |
| --- | --- |
| `name` | Service name used by `BACKUP_SERVICES` and `make backup-service SERVICE=<name>`. |
| `type` | `files` (source paths, optional database dumps), `env_configs` (discover `.env` files) or `postgres_cluster` (full `pg_dumpall`). |
| `sources` | Required paths or files for a `files` service. |
| `optional_sources` | Paths included when present; missing optional paths are logged and skipped. |
| `excludes` | Restic exclude patterns for a `files` service. |
| `databases` | PostgreSQL databases to dump with `pg_dump -Fc` for a `files` service. |
| `stop` | `{ "project": "<compose project>", "services": ["..."] }` to stop containers briefly during a `files` backup. |
| `root` | Directory searched for `.env` files by an `env_configs` service. |
| `env_excludes` | Absolute paths excluded from an `env_configs` service. |

String values support container environment expansion: `${VAR}` and `${VAR:-default}`. The catalog is validated by `make preflight`; `BACKUP_SERVICES` selects and orders the services for a run, while the JSON order is not the run order. The catalog is read on every run, so an edit takes effect on the next `make backup` without rebuilding the image.

Example `files` entry:

```json
{
  "name": "actual",
  "description": "Actual Budget server data",
  "type": "files",
  "sources": ["/cookbook/actual/data"],
  "optional_sources": ["/cookbook/actual/.env"],
  "stop": { "project": "actual", "services": ["actual_server"] }
}
```

`configs` is an `env_configs` entry that discovers `/cookbook/.env` and `/cookbook/*/.env`, excluding `/cookbook/backup/.env`. `datastore-sql` is a `postgres_cluster` entry.

## Environment variables

The setup uses [`.env`](.env), copied from [`.env.default`](.env.default). All keys:

| Variable | Description |
| --- | --- |
| `BACKUP_SCHEDULE_ENABLED` | `true` starts `supercronic`; `false` keeps the container idle so manual runs still work. |
| `BACKUP_CRON` | Cron expression for the automatic `run-all`, default `30 3 * * *`. |
| `BACKUP_TIMEZONE` | Container timezone, default `Europe/Bucharest`; used by cron. |
| `BACKUP_SERVICES` | Space-separated service names to back up. Start with `actual`, then use the full list shown in `.env.default`. |
| `BACKUP_NOTIFY_ENABLED` | `true` enables Apprise notifications. |
| `BACKUP_NOTIFY_ON_SUCCESS` | `true` sends one success message per service; failures are always sent. |
| `APPRISE_DISCORD_URL` | Discord webhook in Apprise form: `discord://<webhook_id>/<webhook_token>`. |
| `RESTIC_REPOSITORY` | Restic repository, default `rclone:icloud:Backups/self-hosting-cookbook/restic`. |
| `RESTIC_PASSWORD` | Encryption password for the restic repository. Generate with `openssl rand -base64 32` and store it offline. |
| `RESTIC_PACK_SIZE` | Optional restic pack size in MiB (commented by default; restic uses 16 MiB). Raise only after testing iCloud upload performance. |
| `BACKUP_PG_HOST` | PostgreSQL host, default `datastore-sql`. |
| `BACKUP_PG_PORT` | PostgreSQL port, default `5432`. |
| `BACKUP_PG_USER` | PostgreSQL user, default `postgres`. |
| `BACKUP_PG_PASSWORD` | Must match `POSTGRES_PASSWORD` in `datastore-sql/.env`. |
| `BACKUP_DOCKER_VOLUMES_PATH` | Host path to Docker's volumes directory, default `/var/lib/docker/volumes`; mounted read-only. |
| `BACKUP_HOST` | Restic snapshot host label, default `home-lab`. |
| `BACKUP_IMMICH_UPLOADS` | Host path to Immich uploads; must match `UPLOAD_LOCATION` in `immich/.env`. |
| `BACKUP_OPENCLOUD_CONFIG` | Host path to OpenCloud config; must match `SH_OC_CONFIG_DIR` in `opencloud/.env`. |
| `BACKUP_OPENCLOUD_DATA` | Host path to OpenCloud data; must match `SH_OC_DATA_DIR` in `opencloud/.env`. |
| `BACKUP_FUSIONAUTH_VOLUME` | Docker volume name for FusionAuth config, default `fusionauth_fusionauth_config`. |
| `BACKUP_LUNA_VOLUME` | Docker volume name for OpenWebUI data, default `luna_openwebui-data`. |
| `BACKUP_PORTAINER_VOLUME` | Docker volume name for Portainer, default `portainer_data`. |
| `BACKUP_CAMOFOX_PROFILES_VOLUME` | Docker volume name for camofox profiles, default `agents-stack_camofox-profiles`. |
| `BACKUP_GPT_RESEARCHER_VOLUME` | Docker volume name for GPT Researcher outputs, default `agents-stack_gpt-researcher-data`. |
| `BACKUP_KEEP_DAILY` | Daily snapshots to keep per service, default `7`. |
| `BACKUP_KEEP_WEEKLY` | Weekly snapshots to keep per service, default `4`. |
| `BACKUP_KEEP_MONTHLY` | Monthly snapshots to keep per service, default `12`. |
| `BACKUP_CHECK_ENABLED` | `true` adds the scheduled repository maintenance job. |
| `BACKUP_CHECK_CRON` | Cron expression for retention/prune/check, default `0 4 * * 0`. |
| `BACKUP_CHECK_READ_DATA_PERCENT` | Percentage of repository packs verified by `restic check --read-data-subset`, default `1`. |

Volume names assume the default Compose project name (the service directory name). If a stack was started with a custom `COMPOSE_PROJECT_NAME`, update the matching `BACKUP_*_VOLUME` value. Verify with `docker volume ls`.

## Running

### Pre-requisites

1. `docker` and `docker compose` on the host; Compose v2.24 or newer is required for the bind mount `create_host_path: false` setting.
2. The `home-lab-net` network: run `make create-network` once from the repo root.
3. A configured `datastore-sql` and the services you intend to back up.
4. A Discord webhook URL if you want notifications.
5. The iCloud account requirements described below.

Copy the example environment file and edit it:

```sh
cp .env.default .env
```

Do not commit `.env`, `rclone/`, or `restore/`; they are ignored.

### iCloud and rclone

rclone's `iclouddrive` backend is unofficial (Tier 4). It requires:

- your regular Apple ID password plus 2FA; **app-specific passwords are rejected**;
- `Settings > Apple Account > iCloud > Access iCloud Data on the Web` turned on;
- if Advanced Data Protection is enabled, Apple may require trusted-device approval when rclone obtains cookies;
- a home/residential network path; using rclone from a datacenter IP has been reported to lock Apple IDs;
- interactive re-authentication roughly every 30 days.

Create the remote inside the container:

```sh
make run
make rclone-config
```

Choose a new remote, name it `icloud`, select `iclouddrive`, keep `service = drive`, enter the Apple ID and password, and complete the 2FA prompt. Verify it:

```sh
make rclone-check
```

Initialize the restic repository once:

```sh
make init
```

Every ~30 days the trust token expires. Re-authenticate interactively and verify:

```sh
make rclone-reconnect
make rclone-check
```

The repository password is the only way to decrypt the backup. Store `RESTIC_PASSWORD` in a password manager and a physical offline copy. Losing it means the iCloud data cannot be recovered.

### First run and trial

The shipped `.env.default` enables only `actual` and leaves the schedule off:

```dotenv
BACKUP_SERVICES="actual"
BACKUP_SCHEDULE_ENABLED=false
```

Configure `APPRISE_DISCORD_URL`, `RESTIC_PASSWORD`, and, if you are enabling database-backed services, the PostgreSQL password, then:

```sh
make notify-test
make preflight
make backup-service SERVICE=actual
make snapshots
```

Check the Discord message and inspect the snapshot:

```sh
docker compose exec backup restic ls latest --tag service:actual
```

Run a non-destructive restore drill:

```sh
make restore SERVICE=actual SNAPSHOT=latest
```

Restored files appear under `backup/restore/actual/` with their original absolute prefixes (`cookbook/actual/...`). Compare them with the live data; do not overwrite the live instance during the drill. When `actual` is validated, enable `vaultwarden` next to validate the PostgreSQL dump path, then add the remaining services incrementally.

The full `BACKUP_SERVICES` list is:

```text
configs actual arr-stack datastore-sql fusionauth immich luna opencloud portainer vaultwarden agents-stack
```

### Automatic schedule

Enable or disable the schedule without editing `.env` by hand:

```sh
make enable-schedule
make disable-schedule
```

Or set `BACKUP_SCHEDULE_ENABLED` and recreate the container. The default is daily at `03:30` (`Europe/Bucharest`), with a weekly maintenance job on Sunday at `04:00`.

The schedule is intentionally disabled until the first manual trial succeeds. A lock prevents scheduled and manual runs from overlapping. If a scheduled run is still active when the next one fires, the second run exits with a warning.

### Manual backups

```sh
make backup                                  # every service in BACKUP_SERVICES
make backup-service SERVICE=vaultwarden      # one service
make snapshots                               # list snapshots
make check                                   # retention + prune + integrity check
make restore SERVICE=vaultwarden SNAPSHOT=latest
```

Inside the container, the same commands are available:

```sh
docker compose exec backup python3 -m backup_runner run-all
docker compose exec backup python3 -m backup_runner run immich
docker compose exec backup python3 -m backup_runner snapshots
```

## Restore

Restores are non-destructive: `make restore` runs inside the already-running `backup` container (start it with `make run` if needed), writes into the `backup/restore/` bind mount, and never modifies a live service or database.

The restored tree keeps the source paths:

- files from the repo: `restore/<service>/cookbook/...`;
- files from named volumes: `restore/<service>/docker-volumes/<volume>/_data/...`;
- external sources: `restore/<service>/sources/immich/...` or `restore/<service>/sources/opencloud-*/...`;
- database dumps: `restore/<service>/var/lib/backup/staging/<service>/...`.

### File services

1. Stop the affected service.
2. Restore the snapshot with `make restore SERVICE=<name>`.
3. Copy the restored files back to the original paths, preserving ownership and permissions.
4. Start the service and verify it.

For `actual`, the restored data is under `restore/actual/cookbook/actual/data/` and the restored `.env` is under `restore/actual/cookbook/actual/.env` if it existed at backup time.

### PostgreSQL services

Stop the consuming service before restoring its database. Restore into the matching database name; the `datastore-sql` image must still include the same extensions (for example `vchord` for Immich and the vector extension for Open WebUI).

```sh
# Single service database
pg_restore -h datastore-sql -U postgres -d vaultwarden --clean --if-exists \
  restore/vaultwarden/var/lib/backup/staging/vaultwarden/vaultwarden.dump

# Full cluster disaster recovery
psql -h datastore-sql -U postgres \
  -f restore/datastore-sql/var/lib/backup/staging/datastore-sql/all-databases.sql
```

For a restore drill, restore to a scratch database such as `vaultwarden_restore_test`, verify the tables, then drop it.

### OpenCloud xattrs

OpenCloud's PosixFS driver stores metadata in extended attributes. Restic preserves xattrs, but verify after a restore:

```sh
getfattr -d -m - restore/opencloud/sources/opencloud-data/<path>
```

Restore to a filesystem that supports xattrs (ext4, XFS, btrfs, ZFS). Losing xattrs loses OpenCloud metadata.

## Back-up

The backup stack has its own secrets and state:

- `backup/.env` contains the restic password, iCloud/rclone settings, PostgreSQL password and Discord webhook; keep an offline copy;
- `backup/rclone/rclone.conf` contains the iCloud session and obscured Apple ID password; keep a protected copy or be ready to re-authenticate;
- the restic password must be stored offline; it is not recoverable;
- `backup/restore/`, the `backup-cache` volume and the `backup-state` volume are disposable.

The `configs` service backs up every service `.env` (and the repo-root `.env`) into the encrypted repository. `backup/.env` is deliberately excluded because it contains the repository password and iCloud credentials.

## Security

- **Docker socket is root-equivalent.** The container can control the host Docker daemon. It is trusted, unreachable from the network (no published port), and uses read-only data mounts, but a compromise of this container is a host compromise.
- **The Docker volumes directory is mounted read-only.** This gives the container read access to every local volume, which is required for the named-volume backups.
- **Secrets live on the host.** `.env`, `rclone/rclone.conf` and the restic password are gitignored; protect file permissions and off-host copies.
- **iCloud is not a formal backup service.** rclone's iCloud backend is unofficial and can break when Apple changes its API. The restic repository is encrypted and versioned, but the only copy is in iCloud; consider a second independent target later.
- **Do not expose this container.** It has no host port and should stay on `home-lab-net`.
- **Restored files are root-owned.** The backup runs as root to read all sources; use `sudo`/`chown` when copying restored data back.
- **Discord webhook URL is a secret.** It can post to your channel; keep it in `.env` only.
- **Restic password loss is unrecoverable.** Losing it loses every snapshot.

## Troubleshooting

- `rclone ... 421 Invalid global session` or auth errors: the iCloud trust token expired; run `make rclone-reconnect` and approve 2FA.
- `restic repository is not initialized`: run `make init` after `make rclone-check` succeeds.
- `pg_dump: error: connection ... password authentication failed`: make `BACKUP_PG_PASSWORD` match `datastore-sql/.env`.
- `No running containers matched project=...`: the Compose project name differs from the service directory name, or the service is already stopped. Check `docker ps` and the `BACKUP_*_VOLUME`/project assumptions.
- `Service catalog not found` or `invalid service catalog`: `services.json` is missing or invalid; run `make preflight`. Edits do not require a rebuild, but the file must be present at `backup/services.json`.
- `Unknown backup service`: the name is not in `services.json`, or is not listed in `BACKUP_SERVICES`.
- `Another backup run is already in progress`: wait for the active run; the lock prevents overlap.
- `restic` reports a stale lock after a crash: stop any active run, then use `make unlock` (`restic unlock`). Do not use it while a backup is genuinely running.
- `restic prune` is slow on iCloud: pruning rewrites packs; it runs weekly. Avoid running it during the daily backup window.
- Healthcheck unhealthy: verify the mounts (`/cookbook`, `/docker-volumes`, `/config/rclone`, `/restore`) and `/var/run/docker.sock` are present.

## Validation notes

This repository is code-only and has no container runtime. Static checks (file layout, YAML, Python syntax, unit tests, env-key documentation, root metadata) run here. Run the Python package tests from this directory with:

```sh
make test
# or: python3 -m unittest discover -s tests -t . -v
```

The real validation must happen on the deployment host:

1. `make run`, `make rclone-config`, `make rclone-check`, `make init`, `make notify-test`.
2. `make preflight` with only `actual` enabled.
3. `make backup-service SERVICE=actual`, then inspect the snapshot and Discord message.
4. `make restore SERVICE=actual SNAPSHOT=latest` and compare the restored tree.
5. Enable `vaultwarden`, verify the PostgreSQL dump, and restore it to a scratch database.
6. Enable `immich` and `opencloud` one at a time; verify a subset restore and OpenCloud xattrs.
7. Enable the full service list, run a scheduled backup in a short test window, then restore the daily cron.
8. Run root `make run-update-all` and confirm `backup` is last and healthy.
