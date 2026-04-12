SHELL := /bin/bash
-include .env
.PHONY: pull run run-update update-run generate-override clean-override

pull:
	docker compose pull

clean-override:
	@rm -f docker-compose.override.yml

generate-override:
	$(MAKE) clean-override
	@if [ -n "$(EXTRA_FILESYSTEMS)" ]; then \
		counter=2; \
		echo "services:" > docker-compose.override.yml; \
		echo "  beszel-agent:" >> docker-compose.override.yml; \
		echo "    volumes:" >> docker-compose.override.yml; \
		IFS=',' read -ra PARTS <<< "$(EXTRA_FILESYSTEMS)"; \
		for part in "$${PARTS[@]}"; do \
			path="$${part%%:*}"; \
			label="$${part#*:}"; \
			echo "      - $${path}/.beszel:/extra-filesystems/sdc$${counter}__$${label}:ro" >> docker-compose.override.yml; \
			((counter++)); \
		done; \
		echo "Generated docker-compose.override.yml with $${counter}-1 extra filesystems"; \
	fi

run:
	docker compose down
	$(MAKE) generate-override
	docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

run-update:
	$(MAKE) pull
	$(MAKE) run

update-run: run-update
