SHELL := /bin/bash
-include .env
.PHONY: pull run run-update update-run clean-override generate-override

pull:
	docker compose pull

clean-override:
	@rm -f docker-compose.override.yml

generate-override:
	$(MAKE) clean-override
	@if [ -n "$(MOVIES_MEDIA_SOURCES)" ]; then \
		echo "services:" > docker-compose.override.yml; \
		echo "  radarr:" >> docker-compose.override.yml; \
		echo "    volumes:" >> docker-compose.override.yml; \
		IFS=',' read -ra PARTS <<< "$(MOVIES_MEDIA_SOURCES)"; \
		for part in "$${PARTS[@]}"; do \
			path="$${part%%:*}"; \
			label="$${part#*:}"; \
			echo "      - $${path}:/data/$${label}" >> docker-compose.override.yml; \
		done; \
	fi; \
	if [ -n "$(SHOWS_MEDIA_SOURCES)" ]; then \
		echo "  sonarr:" >> docker-compose.override.yml; \
		echo "    volumes:" >> docker-compose.override.yml; \
		IFS=',' read -ra PARTS <<< "$(SHOWS_MEDIA_SOURCES)"; \
		for part in "$${PARTS[@]}"; do \
			path="$${part%%:*}"; \
			label="$${part#*:}"; \
			echo "      - $${path}:/data/$${label}" >> docker-compose.override.yml; \
		done; \
	fi; \
	if [ -n "$(MOVIES_MEDIA_SOURCES)" ] || [ -n "$(SHOWS_MEDIA_SOURCES)" ]; then \
		echo "Generated docker-compose.override.yml"; \
	fi

run:
	docker compose down
	$(MAKE) generate-override
	docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

update-run: run-update
