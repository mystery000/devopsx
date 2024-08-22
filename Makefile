.PHONY: docs

# set default shell
SHELL := $(shell which bash)

UV_PATH = $(HOME)/.cargo/bin
export PATH := $(UV_PATH):$(PATH)

# src dirs and files
SRCDIRS = devopsx tests scripts train
SRCFILES = $(shell find ${SRCDIRS} -name '*.py')

# exclude files
EXCLUDES = tests/output scripts/build_changelog.py
SRCFILES = $(shell find ${SRCDIRS} -name '*.py' $(foreach EXCLUDE,$(EXCLUDES),-not -path $(EXCLUDE)))

build:
	@echo "Checking if uv is installed..."
	@if ! command -v uv &> /dev/null; then \
		echo "uv not found. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	else \
		echo "uv is already installed."; \
	fi
	@echo "Checking for Python 3.10.12..."
	@if ! uv python find 3.10.12 &> /dev/null; then \
		echo "Python 3.10.12 not found. Installing..."; \
		uv python install 3.10.12; \
	else \
		echo "Python 3.10.12 is already installed."; \
	fi
	@echo "Creating virtual environment with Python 3.10.12..."
	uv venv --python=3.10.12 .venv
	@echo "Activating virtual environment and installing dependencies..."
	. .venv/bin/activate && uv pip install -e ".[server]"
	
	@echo "Creating symbolic link to /usr/local/bin/devopsx..."
	@if [ -f /usr/local/bin/devopsx ]; then \
			echo "Symbolic link already exists. Skipping."; \
	else \
			sudo ln -s $(PWD)/.venv/bin/devopsx /usr/local/bin/devopsx; \
			echo "Symbolic link created."; \
	fi
test:
	@# if SLOW is not set, pass `-m "not slow"` to skip slow tests
	pytest ${SRCDIRS} -v --log-level INFO --durations=5 \
		--cov=devopsx --cov-report=xml --cov-report=term-missing --cov-report=html \
		-n auto \
		$(if $(EVAL), , -m "not eval") \
		$(if $(SLOW), --timeout 60, --timeout 5 -m "not slow and not eval") \
		$(if $(PROFILE), --profile-svg)

eval:
	python3 -m devopsx.eval

typecheck:
	mypy --ignore-missing-imports --check-untyped-defs ${SRCDIRS} $(if $(EXCLUDES),$(foreach EXCLUDE,$(EXCLUDES),--exclude $(EXCLUDE)))

lint:
	ruff ${SRCDIRS}

format:
	ruff --fix-only ${SRCDIRS}
	pyupgrade --py310-plus --exit-zero-even-if-changed ${SRCFILES}
	black ${SRCDIRS}

precommit: format lint typecheck test

docs/.clean: docs/conf.py
	make -C docs clean
	touch docs/.clean

docs: docs/conf.py docs/*.rst docs/.clean
	make -C docs html

version:
	@./scripts/bump_version.sh

./scripts/build_changelog.py:
	wget -O $@ https://raw.githubusercontent.com/ActivityWatch/activitywatch/master/scripts/build_changelog.py
	chmod +x $@

dist/CHANGELOG.md: version ./scripts/build_changelog.py
	VERSION=$$(git describe --tags --abbrev=0) && \
	PREV_VERSION=$$(./scripts/get-last-version.sh $${VERSION}) && \
		./scripts/build_changelog.py --range $${PREV_VERSION}...$${VERSION} --project-title devopsx --org ErikBjare --repo devopsx --output $@

release: dist/CHANGELOG.md
	@VERSION=$$(git describe --tags --abbrev=0) && \
		echo "Releasing version $${VERSION}"; \
		read -p "Press enter to continue" && \
		gh release create $${VERSION} -t $${VERSION} -F dist/CHANGELOG.md

clean: clean-docs

clean-docs:
	uv pip run make -C docs clean

clean-test:
	echo $$HOME/.local/share/devopsx/logs/*test-*-test_*
	rm -I $$HOME/.local/share/devopsx/logs/*test-*-test_*/*.jsonl || true
	rm --dir $$HOME/.local/share/devopsx/logs/*test-*-test_*/ || true

cloc: cloc-core cloc-tools cloc-server cloc-tests

cloc-core:
	cloc devopsx/*.py devopsx/*/__init__.py devopsx/*/base.py --by-file

cloc-tools:
	cloc devopsx/tools/*.py --by-file

cloc-server:
	cloc devopsx/server --by-file

cloc-tests:
	cloc tests/*.py --by-file
