PORT_NUMBER ?= 8009
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
THIS_DIR_NAME := $(notdir $(patsubst %/,%,$(THIS_DIR)))
TEST_DIR := tests/$(THIS_DIR_NAME)

debug:
	@echo "THIS_DIR: $(THIS_DIR)"
	@echo "THIS_DIR_NAME: $(THIS_DIR_NAME)"
	@echo "PORT_NUMBER: $(PORT_NUMBER)"

serve:
	uv run -m http.server --directory $(THIS_DIR) $(PORT_NUMBER)

build:
	echo "Nothing to do"

docs:
	# Markdown
	uvx --from md-toc md_toc --in-place github --header-levels 4 *.md
	uvx rumdl check --fix --config ../../pyproject.toml *.md

format:
	# Code Formatting
	npx -y prettier './**/*.{js,css,html}' --write --print-width 120    

test: 
	uv run pytest ../../"$(TEST_DIR)" -vvv --base-url http://localhost:$(PORT_NUMBER)/index.html --browser chromium


clean:
	# No build artifacts to clean
	echo "Nothing to clean"