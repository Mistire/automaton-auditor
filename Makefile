# Makefile for easy access to audit commands
.PHONY: audit local install clean

# This allows passing the URL directly after 'make audit'
# Usage: make audit https://github.com/...
audit:
	@if [ -z "$(url)" ] && [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Usage: make audit url=<url> or make local"; \
		exit 1; \
	fi
	./audit.sh $(or $(url),$(filter-out $@,$(MAKECMDGOALS)))

# Ignore unknown targets (to support positional args in make audit)
%:
	@:

local:
	./audit.sh .

install:
	uv venv && uv pip install -e .

clean:
	rm -rf audit/report_*/*.md
