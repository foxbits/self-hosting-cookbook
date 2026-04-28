.PHONY: build run run-update update-run

build:
	docker compose pull
	docker compose build --no-cache

run:
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update
