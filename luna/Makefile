.PHONY: build run run-update update-run create-db delete-db

build:
	docker compose pull
	docker compose build --no-cache

create-db:
	@if [ "$$(grep -E '^DATABASE_TYPE=' .env | cut -d'=' -f2)" = "postgresql" ]; then \
		docker exec -e PGPASSWORD=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) datastore-sql psql -U $$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) -c "CREATE DATABASE openwebui;" 2>/dev/null || true; \
	fi

delete-db:
	@if [ "$$(grep -E '^DATABASE_TYPE=' .env | cut -d'=' -f2)" = "postgresql" ]; then \
		docker exec -e PGPASSWORD=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) datastore-sql psql -U $$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) -c "DROP DATABASE openwebui;" 2>/dev/null || true; \
	fi

run:
	docker compose down
	docker compose up -d
	$(MAKE) create-db

run-update:
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update
