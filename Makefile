.PHONY: docs eval

# set default shell
SHELL := $(shell which bash)

# src dirs and files
SRCDIRS = devopsx tests scripts train eval
SRCFILES = $(shell find ${SRCDIRS} -name '*.py')

# exclude files
EXCLUDES = tests/output scripts/build_changelog.py
SRCFILES = $(shell find ${SRCDIRS} -name '*.py' $(foreach EXCLUDE,$(EXCLUDES),-not -path $(EXCLUDE)))

build:
	poetry install

test:
	@# if SLOW is not set, pass `-m "not slow"` to skip slow tests
	poetry run pytest ${SRCDIRS} -v --log-level INFO --durations=5 \
		--cov=devopsx --cov-report=xml --cov-report=term-missing --cov-report=html \
		-n 8 \
		$(if $(SLOW), --timeout 60, --timeout 5 -m "not slow") \
		$(if $(EVAL), , -m "not eval") \
		$(if $(PROFILE), --profile-svg)

eval:
	poetry run python3 -m eval

typecheck:
	poetry run mypy --ignore-missing-imports ${SRCDIRS} $(if $(EXCLUDES),$(foreach EXCLUDE,$(EXCLUDES),--exclude $(EXCLUDE)))

lint:
	poetry run ruff ${SRCDIRS}

format:
	poetry run ruff --fix-only ${SRCDIRS}
	poetry run pyupgrade --py310-plus --exit-zero-even-if-changed ${SRCFILES}
	poetry run black ${SRCDIRS}

precommit: format lint typecheck test

docs/.clean: docs/conf.py
	poetry run make -C docs clean
	touch docs/.clean

docs: docs/conf.py docs/*.rst docs/.clean
	poetry run make -C docs html

clean-test:
	echo $$HOME/.local/share/devopsx/logs/*test-*-test_*
	rm -I $$HOME/.local/share/devopsx/logs/*test-*-test_*/*.jsonl || true
	rm --dir $$HOME/.local/share/devopsx/logs/*test-*-test_*/ || true

cloc: cloc-core cloc-tools

cloc-core:
	cloc devopsx/*.py --by-file

cloc-tools:
	cloc devopsx/tools --by-file

cloc-tests:
	cloc tests/*.py --by-file