.PHONY: pull build pull-repos run run-update update-run generate-settings

SEARXNG_DIR := searxng/core-config
TEMPLATE := ./settings-template.yml
SETTINGS := $(SEARXNG_DIR)/settings.yml
ENV_FILE := .env

generate-settings:
	@if [ -f $(SETTINGS) ]; then \
		echo "$(SETTINGS) already exists, skipping generation"; \
		exit 0; \
	fi; \
	if [ ! -f $(ENV_FILE) ]; then \
		echo "Error: $(ENV_FILE) not found. Copy .env.default to .env and configure it."; \
		exit 1; \
	fi; \
	mkdir -p $(SEARXNG_DIR); \
	if [ -d "$(SEARXNG_DIR)" ]; then sudo chown -R $$USER:$(id -gn) $(SEARXNG_DIR); fi; \
	set -a; \
	. ./$(ENV_FILE); \
	set +a; \
	envsubst '$$DEBUG $$LIMITER_ENABLED $$SEARXNG_INSTANCE_NAME $$LOCALE $$COUNTRY_CODE $$WOLFRAM_API_KEY $$WOLFRAM_DISABLED' < $(TEMPLATE) > $(SETTINGS); \
	echo "Generated $(SETTINGS) from template"

build:
	docker compose pull
	docker compose build --pull

pull-repos:
	@set -e; \
	ORIG_DIR=$$(pwd); \
	set -a; \
	if [ -f $(ENV_FILE) ]; then . ./$(ENV_FILE); else . ./.env.default; fi; \
	set +a; \
	echo "Updating $$GPT_RESEARCHER_PATH..."; \
	cd "$$GPT_RESEARCHER_PATH" && git pull && cd "$$ORIG_DIR"; \
	echo "Updating $$OPENCRAWL_PATH..."; \
	cd "$$OPENCRAWL_PATH" && git pull && cd "$$ORIG_DIR"; \
	echo "Updating $$CAMOFOX_BROWSER_PATH..."; \
	cd "$$CAMOFOX_BROWSER_PATH" && git pull && cd "$$ORIG_DIR"; \
	echo "Updating $$CRW_PATH..."; \
	cd "$$CRW_PATH" && git pull && cd "$$ORIG_DIR";

run:
	$(MAKE) generate-settings
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull-repos
	$(MAKE) build
	$(MAKE) run

# Alias for run-update
update-run: run-update
