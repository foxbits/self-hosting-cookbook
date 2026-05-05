.PHONY: run-update-all create-network clean-disk

SHELL := /bin/sh

run-update-all:
	@if [ -f .env ]; then . ./.env; fi ; \
	if [ -z "$$EXECUTION_ORDER" ] && [ -f .env.default ]; then . ./.env.default; fi ; \
	if [ -z "$$EXECUTION_ORDER" ]; then \
		echo "ERROR: EXECUTION_ORDER is not set in .env or .env.default" >&2 ; \
		exit 1 ; \
	fi ; \
	echo "Execution order: $${EXECUTION_ORDER:-<none>}" ; \
	for name in $$EXECUTION_ORDER; do \
		dir="$$name/" ; \
		if [ ! -d "$$dir" ]; then \
			echo "Directory $$dir does not exist, skipping" ; \
			continue ; \
		fi ; \
		if [ ! -f "$$dir/Makefile" ]; then \
			echo "No Makefile in $$dir, skipping" ; \
			continue ; \
		fi ; \
		echo "==> Updating $$name" ; \
		$(MAKE) -C "$$dir" update-run ; \
		echo "==> Waiting for $$name to be healthy" ; \
		(cd "$$dir" && while :; do \
			sleep 5 ; \
			count=$$(docker compose ps --format json 2>/dev/null | jq -s '[.[] | select(.State == "running" and (.Health == null or .Health == "healthy") or .State == "started") | length' 2>/dev/null || echo "0") ; \
			total=$$(docker compose ps --format json 2>/dev/null | jq -s 'length' 2>/dev/null || echo "0") ; \
			if [ "$$count" -ge "$$total" ] && [ "$$total" -gt 0 ]; then break; fi ; \
			echo "    Waiting... ($$count/$$total service(s) ready)" ; \
		done) ; \
		echo "==> $$name is healthy" ; \
	done

create-network:
	docker network create home-lab-net || true

clean-disk:
	@echo "=== Disk before ==="
	@df -h /
	sudo apt clean
	sudo apt autoremove --purge -y
	sudo journalctl --vacuum-time=7d
	sudo find /var/log -type f -name "*.gz" -delete
	sudo find /var/log -type f -name "*.1" -delete
	docker system prune -f 2>/dev/null || true
	@echo "=== Disk after ==="
	@df -h /
