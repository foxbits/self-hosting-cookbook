.PHONY: build run run-update update-run

build:
	docker compose pull
	DOCKER_GID=$(stat -c '%g' /var/run/docker.sock) docker compose build --no-cache

run:
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update
