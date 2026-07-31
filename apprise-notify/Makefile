.PHONY: pull run run-update update-run

pull:
	docker compose pull

run:
	docker compose down
	docker compose up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

# Alias for run-update
update-run: run-update
