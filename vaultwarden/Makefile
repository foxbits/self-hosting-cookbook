.PHONY: pull run run-update update-run create-db delete-db generate-admin-token

pull:
	docker compose pull

create-db:
	@DB_PASS=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) ; \
	DB_USER=$$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) ; \
	DB_EXISTS=$$(docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='vaultwarden'" 2>/dev/null) ; \
	if [ "$$DB_EXISTS" != "1" ]; then \
		echo "Creating database vaultwarden..." ; \
		docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -c "CREATE DATABASE vaultwarden;" ; \
	else \
		echo "Database vaultwarden already exists, skipping creation." ; \
	fi

delete-db:
	@DB_PASS=$$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2) ; \
	DB_USER=$$(grep -E '^POSTGRES_USER=' .env | cut -d'=' -f2) ; \
	docker exec -e PGPASSWORD=$$DB_PASS datastore-sql psql -U $$DB_USER -c "DROP DATABASE vaultwarden;" 2>/dev/null || true

run:
	docker compose down
	$(MAKE) generate-admin-token
	$(MAKE) create-db
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update

# Interactive helper, called automatically by `run` on every invocation (and so
# also by `run-update`). Its guards make it a no-op unless it is a first run,
# so wiring it in is safe for headless `run-update-all` runs.
# Runs the image's built-in `vaultwarden hash` (pulls the image on first use,
# prompts for the passphrase twice) and writes the resulting Argon2 PHC string
# into .env as ADMIN_TOKEN automatically — no manual pasting.
# First run = ENABLE_ADMIN=true in .env AND ADMIN_TOKEN empty/missing/CHANGE_ME.
# If ADMIN_TOKEN is already set, or automation is disabled, the target does
# nothing (exit 0 — never overwrites, never blocks `run`). Only a missing .env
# or a failed hash extraction aborts (exit 1) with .env untouched.
generate-admin-token:
	@if [ ! -f .env ]; then \
		echo "No .env found — copy .env.default to .env first, set ENABLE_ADMIN=true, then re-run." ; \
		exit 1 ; \
	fi ; \
	ADMIN_ON=$$(grep -E '^ENABLE_ADMIN=' .env | cut -d'=' -f2 | tr -d ' \t\r' | tr '[:upper:]' '[:lower:]') ; \
	if [ "$$ADMIN_ON" != "true" ]; then \
		echo "Token auto-generation disabled (ENABLE_ADMIN is not 'true') — skipping." ; \
		exit 0 ; \
	fi ; \
	TOKEN=$$(grep -E '^ADMIN_TOKEN=' .env | cut -d'=' -f2- | tr -d "'\" \t\r") ; \
	if [ -n "$$TOKEN" ] && [ "$$TOKEN" != "CHANGE_ME" ]; then \
		echo "ADMIN_TOKEN is already set in .env — nothing to do." ; \
	else \
		echo "Type the new admin passphrase (you will be prompted twice)..." ; \
		HASH=$$(docker run --rm -it vaultwarden/server /vaultwarden hash | grep -o '\$$argon2[^[:space:]]*' | tr -d "'\"") ; \
		if [ -z "$$HASH" ]; then \
			echo "ERROR: could not obtain an Argon2 hash (is docker running, were both prompts answered?). .env untouched." ; \
			exit 1 ; \
		fi ; \
		grep -v '^ADMIN_TOKEN=' .env > .env.tmp && echo "ADMIN_TOKEN='$$HASH'" >> .env.tmp && mv .env.tmp .env ; \
		echo "ADMIN_TOKEN written to .env." ; \
	fi
