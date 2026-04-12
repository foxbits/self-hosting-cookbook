.PHONY: run-update-all create-network clean-disk

SHELL := /bin/sh

run-update-all:
	@if [ -f .env ]; then . ./.env; fi ; \
	EXCLUDE="$${EXCLUDE}" ; \
	echo "Exclusions: $${EXCLUDE:-<none>}" ; \
	for dir in */; do \
		name=$${dir%/} ; \
		skip=0 ; \
		for e in $$EXCLUDE; do \
			if [ "$$name" = "$$e" ]; then \
				skip=1 ; break ; \
			fi ; \
		done ; \
		if [ $$skip -eq 1 ]; then \
			echo "Skipping $$dir" ; \
			continue ; \
		fi ; \
		if [ -f "$$dir/Makefile" ]; then \
			$(MAKE) -C "$$dir" update-run ; \
		fi ; \
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