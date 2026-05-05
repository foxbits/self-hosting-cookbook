.PHONY: build run run-update update-run create-db delete-db delete-volume

build:
	docker compose pull

create-db:
	@DB_PASS=$$(grep -E '^DB_PASSWORD=' .env | cut -d'=' -f2) ; \
	DB_USER=$$(grep -E '^DB_USERNAME=' .env | cut -d'=' -f2) ; \
	DB_NAME=$$(grep -E '^DB_DATABASE_NAME=' .env | cut -d'=' -f2) ; \
	DB_EXISTS=$$(docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$$DB_NAME'" 2>/dev/null) ; \
	if [ "$$DB_EXISTS" != "1" ]; then \
		echo "Creating database $$DB_NAME..." ; \
		docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -c "CREATE DATABASE $$DB_NAME;" ; \
		echo "Creating extensions..." ; \
		docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -d $$DB_NAME -c "CREATE EXTENSION vchord CASCADE;" ; \
		docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -d $$DB_NAME -c "CREATE EXTENSION earthdistance CASCADE;" ; \
	else \
		echo "Database $$DB_NAME already exists, skipping creation." ; \
	fi

run:
	docker compose down
	$(MAKE) create-db
	docker compose up -d

run-update:
	$(MAKE) build
	$(MAKE) run

update-run: run-update
