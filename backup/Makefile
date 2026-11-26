SHELL := /bin/sh

SNAPSHOT ?= latest
PYTHON := python3
CLI := /usr/local/bin/backup.py
EXEC_CLI := docker compose exec backup $(PYTHON) $(CLI)
RUN_CLI := docker compose run --rm --entrypoint $(PYTHON) backup $(CLI)

.PHONY: build pull run run-update update-run init rclone-config rclone-reconnect rclone-check preflight backup backup-service snapshots check restore notify-test unlock enable-schedule disable-schedule

build:
	docker compose build --pull

pull:
	docker compose pull

run:
	docker compose up -d --build

run-update:
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update

init:
	$(RUN_CLI) init

rclone-config:
	docker compose run --rm -it --entrypoint rclone backup config

rclone-reconnect:
	docker compose run --rm -it --entrypoint rclone backup config reconnect icloud:

rclone-check:
	docker compose run --rm --entrypoint rclone backup lsd icloud:

preflight:
	$(EXEC_CLI) preflight

backup:
	$(EXEC_CLI) run-all

backup-service:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make backup-service SERVICE=<name>" ; exit 1 ; fi
	$(EXEC_CLI) run "$(SERVICE)"

snapshots:
	$(EXEC_CLI) snapshots

check:
	$(EXEC_CLI) check

restore:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make restore SERVICE=<name> [SNAPSHOT=<id|latest>]" ; exit 1 ; fi
	$(EXEC_CLI) restore "$(SERVICE)" "$(SNAPSHOT)"

notify-test:
	$(EXEC_CLI) notify-test

unlock:
	docker compose exec backup restic unlock

enable-schedule:
	sed -i 's/^BACKUP_SCHEDULE_ENABLED=.*/BACKUP_SCHEDULE_ENABLED=true/' .env
	docker compose up -d --force-recreate backup

disable-schedule:
	sed -i 's/^BACKUP_SCHEDULE_ENABLED=.*/BACKUP_SCHEDULE_ENABLED=false/' .env
	docker compose up -d --force-recreate backup
