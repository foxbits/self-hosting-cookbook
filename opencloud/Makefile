SHELL := /bin/sh
.PHONY: pull init-config init-storage run run-update update-run

pull:
	docker compose pull

init-config:
	@if [ ! -d config ]; then \
		cp -r config-example config; \
		echo "Seeded ./config from ./config-example"; \
	else \
		echo "./config exists, leaving untouched"; \
	fi

init-storage:
	@CFG=$$(grep -E '^SH_OC_CONFIG_DIR=' .env | cut -d'=' -f2) ; \
	DAT=$$(grep -E '^SH_OC_DATA_DIR=' .env | cut -d'=' -f2) ; \
	for d in "$$CFG" "$$DAT"; do \
		[ -d "$$d" ] || sudo mkdir -p "$$d" ; \
		[ "$$(stat -c '%u:%g' "$$d")" = "1000:1000" ] || sudo chown 1000:1000 "$$d" ; \
	done ; \
	echo "Storage ready: $$CFG, $$DAT"

run:
	$(MAKE) init-config
	$(MAKE) init-storage
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update
