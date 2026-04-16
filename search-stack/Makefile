.PHONY: pull run run-update update-run generate-settings

SEARXNG_DIR := searxng/core-config
TEMPLATE := ./settings-template.yml
SETTINGS := $(SEARXNG_DIR)/settings.yml
ENV_FILE := .env

generate-settings:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Error: $(ENV_FILE) not found. Copy .env.default to .env and configure it."; \
		exit 1; \
	fi
	@mkdir -p $(SEARXNG_DIR)
	@set -a; \
	. ./$(ENV_FILE); \
	set +a; \
	envsubst '$$DEBUG $$LIMITER_ENABLED $$SEARXNG_INSTANCE_NAME $$LOCALE $$COUNTRY_CODE $$WOLFRAM_API_KEY $$WOLFRAM_DISABLED' < $(TEMPLATE) > $(SETTINGS)
	@echo "Generated $(SETTINGS) from template"

pull:
	docker compose pull

run:
	$(MAKE) generate-settings
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update
