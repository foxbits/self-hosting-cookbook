SHELL := /bin/sh
.PHONY: pull init-storage run run-update update-run

pull:
	docker compose pull

init-storage:
	@CFG=$$(grep -E '^OC_CONFIG_DIR=' .env | cut -d'=' -f2) ; \
	DAT=$$(grep -E '^OC_DATA_DIR=' .env | cut -d'=' -f2) ; \
	for d in "$$CFG" "$$DAT"; do \
		[ -d "$$d" ] || sudo mkdir -p "$$d" ; \
		[ "$$(stat -c '%u:%g' "$$d")" = "1000:1000" ] || sudo chown 1000:1000 "$$d" ; \
	done ; \
	echo "Storage ready: $$CFG, $$DAT"

run:
	$(MAKE) init-storage
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update
