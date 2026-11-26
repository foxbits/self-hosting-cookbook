This is the docker compose setup for a backup stack built on [restic](https://restic.net/) and [rclone](https://rclone.org/), storing an encrypted, deduplicated repository on iCloud Drive and sending Discord notifications through the [Apprise CLI](https://appriseit.com/cli/). The first pattern is intentionally limited to `actual`.

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

The stack starts **one container**, `backup`, with **no published host port**. It uses the host Docker socket to stop and restart `actual_server` while its SQLite data is snapshotted.

The container contains:

- a Python package (`src/backup_runner/`) for orchestration, validation, locking, stop/start and notifications;
- the JSON service catalog (`services.json`), mounted read-only at `/etc/backup/services.json`;
- `restic` for encrypted, deduplicated snapshots and retention;
- `rclone` for the iCloud Drive remote;
- the Docker CLI for the `actual_server` stop/start;
- the Apprise CLI for Discord notifications;
- `supercronic` for the container-friendly cron schedule.

The `actual` backup is one restic snapshot tagged `service:actual`. If a run is interrupted, the next container start restarts `actual_server` if the backup had stopped it.

### What is backed up

| Service | State | Method | Runtime handling |
| --- | --- | --- | --- |
| `actual` | `actual/data`, `actual/.env` | restic | stop `actual_server` |

`actual/data` holds the SQLite database and attachments. The service `.env` is included when present so the deployment can be reconstructed. Other cookbook services are deliberately not part of this first pattern; they can be added later with the same catalog model.

### Service catalog

The definition lives in [`services.json`](services.json), which is tracked in git and mounted read-only at `/etc/backup/services.json`. No shell script is needed to add another file-based service.

The `actual` entry has:

| Field | Meaning |
| --- | --- |
| `name` | Service name used by `BACKUP_SERVICES` and `make backup-service SERVICE=<name>`. |
| `description` | Human-readable description. |
| `sources` | Required paths or files to snapshot. |
| `optional_sources` | Paths included when present; missing optional paths are logged and skipped. |
| `stop` | `{ "project": "<compose project>", "services": ["..."] }` to stop containers briefly during the snapshot. |

The catalog is validated by `make preflight`; `BACKUP_SERVICES` selects and orders services for a run. The catalog is read on every run, so an edit takes effect on the next `make backup` without rebuilding the image.

```json
{
  "name": "actual",
  "description": "Actual Budget server data",
  "sources": ["/cookbook/actual/data"],
  "optional_sources": ["/cookbook/actual/.env"],
  "stop": { "project": "actual", "services": ["actual_server"] }
}
```

## Environment variables

The setup uses [`.env`](.env), copied from [`.env.default`](.env.default). All keys:

| Variable | Description |
| --- | --- |
| `BACKUP_SCHEDULE_ENABLED` | `true` starts `supercronic`; `false` keeps the container idle so manual runs still work. |
| `BACKUP_CRON` | Cron expression for the automatic `run-all`, default `30 3 * * *`. |
| `BACKUP_TIMEZONE` | Container timezone, default `Europe/Bucharest`; used by cron. |
| `BACKUP_SERVICES` | Space-separated service names to back up; currently `actual`. |
| `BACKUP_NOTIFY_ENABLED` | `true` enables Apprise notifications. |
| `BACKUP_NOTIFY_ON_SUCCESS` | `true` sends one success message per service; failures are always sent. |
| `APPRISE_DISCORD_URL` | Discord webhook in Apprise form: `discord://<webhook_id>/<webhook_token>`. |
| `RESTIC_REPOSITORY` | Restic repository, default `rclone:icloud:Backups/self-hosting-cookbook/restic`. |
| `RESTIC_PASSWORD` | Encryption password for the restic repository. Generate with `openssl rand -base64 32` and store it offline. |
| `RESTIC_PACK_SIZE` | Optional restic pack size in MiB (commented by default; restic uses 16 MiB). Raise only after testing iCloud upload performance. |
| `BACKUP_HOST` | Restic snapshot host label, default `home-lab`. |
| `BACKUP_KEEP_DAILY` | Daily snapshots to keep, default `7`. |
| `BACKUP_KEEP_WEEKLY` | Weekly snapshots to keep, default `4`. |
| `BACKUP_KEEP_MONTHLY` | Monthly snapshots to keep, default `12`. |
| `BACKUP_CHECK_ENABLED` | `true` adds the scheduled repository maintenance job. |
| `BACKUP_CHECK_CRON` | Cron expression for retention/prune/check, default `0 4 * * 0`. |
| `BACKUP_CHECK_READ_DATA_PERCENT` | Percentage of repository packs verified by `restic check --read-data-subset`, default `1`. |

## Running

### Pre-requisites

1. `docker` and `docker compose` on the host.
2. The `home-lab-net` network: run `make create-network` once from the repo root.
3. A running `actual` stack.
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

Configure `APPRISE_DISCORD_URL` and `RESTIC_PASSWORD`, then:

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

Restored files appear under `backup/restore/actual/cookbook/actual/` with their original absolute prefixes. Compare them with the live data; do not overwrite the live instance during the drill.

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
make backup                                  # actual, from BACKUP_SERVICES
make backup-service SERVICE=actual           # one service
make snapshots                               # list snapshots
make check                                   # retention + prune + integrity check
make restore SERVICE=actual SNAPSHOT=latest
```

Inside the container, the same commands are available:

```sh
docker compose exec backup python3 -m backup_runner run-all
docker compose exec backup python3 -m backup_runner run actual
docker compose exec backup python3 -m backup_runner snapshots
```

## Restore

Restores are non-destructive: `make restore` runs inside the already-running `backup` container (start it with `make run` if needed), writes into the `backup/restore/` bind mount, and never modifies the live service.

The restored tree keeps the source paths:

- data: `restore/actual/cookbook/actual/data/`;
- environment file: `restore/actual/cookbook/actual/.env` when it existed at backup time.

1. Stop `actual_server`.
2. Restore the snapshot with `make restore SERVICE=actual SNAPSHOT=latest`.
3. Copy the restored `data` directory back to `actual/data`, preserving ownership and permissions.
4. Start `actual_server` and verify the application.

## Back-up

The backup stack has its own secrets and state:

- `backup/.env` contains the restic password, iCloud/rclone settings and Discord webhook; keep an offline copy;
- `backup/rclone/rclone.conf` contains the iCloud session and obscured Apple ID password; keep a protected copy or be ready to re-authenticate;
- the restic password must be stored offline; it is not recoverable;
- `backup/restore/`, the `backup-cache` volume and the `backup-state` volume are disposable.

The `actual` service includes `actual/.env` when present, so the deployment configuration is inside the encrypted repository. `backup/.env` is not included because it contains the repository password and iCloud credentials.

## Security

- **Docker socket is root-equivalent.** The container can control the host Docker daemon. It is trusted, unreachable from the network (no published port), and uses read-only data mounts, but a compromise of this container is a host compromise.
- **Secrets live on the host.** `.env`, `rclone/rclone.conf` and the restic password are gitignored; protect file permissions and off-host copies.
- **iCloud is not a formal backup service.** rclone's iCloud backend is unofficial and can break when Apple changes its API. The restic repository is encrypted and versioned, but the only copy is in iCloud; consider a second independent target later.
- **Do not expose this container.** It has no host port and should stay on `home-lab-net`.
- **Restored files are root-owned.** The backup runs as root to read all sources; use `sudo`/`chown` when copying restored data back.
- **Discord webhook URL is a secret.** It can post to your channel; keep it in `.env` only.
- **Restic password loss is unrecoverable.** Losing it loses every snapshot.

## Troubleshooting

- `rclone ... 421 Invalid global session` or auth errors: the iCloud trust token expired; run `make rclone-reconnect` and approve 2FA.
- `restic repository is not initialized`: run `make init` after `make rclone-check` succeeds.
- `No running containers matched project=actual`: the Compose project name differs from the service directory name, or `actual_server` is already stopped. Check `docker ps` and the project name.
- `Service catalog not found` or `invalid service catalog`: `services.json` is missing or invalid; run `make preflight`. Edits do not require a rebuild, but the file must be present at `backup/services.json`.
- `Unknown backup service`: the name is not in `services.json`, or is not listed in `BACKUP_SERVICES`.
- `Another backup run is already in progress`: wait for the active run; the lock prevents overlap.
- `restic` reports a stale lock after a crash: stop any active run, then use `make unlock` (`restic unlock`). Do not use it while a backup is genuinely running.
- `restic prune` is slow on iCloud: pruning rewrites packs; it runs weekly. Avoid running it during the daily backup window.
- Healthcheck unhealthy: verify the mounts (`/cookbook`, `/config/rclone`, `/restore`) and `/var/run/docker.sock` are present.

## Validation notes

This repository is code-only and has no container runtime. Static checks (file layout, YAML, Python syntax, unit tests, env-key documentation, root metadata) run here. Run the Python package tests from this directory with:

```sh
make test
# or: python3 -m unittest discover -s tests -t . -v
```

The real validation must happen on the deployment host:

1. `make run`, `make rclone-config`, `make rclone-check`, `make init`, `make notify-test`.
2. `make preflight` with `actual` enabled.
3. `make backup-service SERVICE=actual`, then inspect the snapshot and Discord message.
4. `make restore SERVICE=actual SNAPSHOT=latest` and compare the restored tree.
5. Run root `make run-update-all` and confirm `backup` is last and healthy.
