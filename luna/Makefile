.PHONY: build build-base pull-repos run run-update update-run create-db delete-db delete-volume

ENV_FILE := .env

build-base:
	@set -e; \
	OPENWEBUI_PATH=$$(grep -h -E '^OPENWEBUI_PATH=' $(ENV_FILE) .env.default 2>/dev/null | head -n 1 | cut -d'=' -f2-); \
	OPENWEBUI_BASE_IMAGE=$$(grep -h -E '^OPENWEBUI_BASE_IMAGE=' $(ENV_FILE) .env.default 2>/dev/null | head -n 1 | cut -d'=' -f2-); \
	if [ -z "$$OPENWEBUI_PATH" ]; then echo "Error: OPENWEBUI_PATH not set in $(ENV_FILE) or .env.default"; exit 1; fi; \
	: "$${OPENWEBUI_BASE_IMAGE:=luna-openwebui-base:local}"; \
	HASH=$$(git -C "$$OPENWEBUI_PATH" rev-parse --short HEAD 2>/dev/null || echo dev-build); \
	docker build -f "$$OPENWEBUI_PATH/Dockerfile" -t "$$OPENWEBUI_BASE_IMAGE" --build-arg USE_SLIM=true --build-arg BUILD_HASH="$$HASH" "$$OPENWEBUI_PATH"

build:
	$(MAKE) build-base
	docker compose pull
	docker compose build

pull-repos:
	@set -e; \
	ORIG_DIR=$$(pwd); \
	OPENWEBUI_PATH=$$(grep -h -E '^OPENWEBUI_PATH=' $(ENV_FILE) .env.default 2>/dev/null | head -n 1 | cut -d'=' -f2-); \
	if [ -z "$$OPENWEBUI_PATH" ]; then echo "Error: OPENWEBUI_PATH not set in $(ENV_FILE) or .env.default"; exit 1; fi; \
	echo "Updating $$OPENWEBUI_PATH..."; \
	cd "$$OPENWEBUI_PATH" && git pull && cd "$$ORIG_DIR";

create-db:
	@if [ "$$(grep -E '^DATABASE_TYPE=' .env | cut -d'=' -f2)" = "postgresql" ]; then \
		docker exec -e PGPASSWORD=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) datastore-sql psql -U $$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) -c "CREATE DATABASE openwebui;" 2>/dev/null || true; \
	fi

delete-db:
	@if [ "$$(grep -E '^DATABASE_TYPE=' .env | cut -d'=' -f2)" = "postgresql" ]; then \
		docker exec -e PGPASSWORD=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) datastore-sql psql -U $$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) -c "DROP DATABASE openwebui;" 2>/dev/null || true; \
	fi

delete-volume:
	docker volume rm luna_openwebui-data

run:
	docker compose down
	$(MAKE) create-db
	docker compose up -d

run-update:
	$(MAKE) pull-repos
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update
