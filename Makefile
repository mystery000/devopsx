.PHONY: docs

# set default shell
SHELL := $(shell which bash)

# src dirs and files
SRCDIRS = devopsx tests scripts train
SRCFILES = $(shell find ${SRCDIRS} -name '*.py')

# exclude files
EXCLUDES = tests/output scripts/build_changelog.py
SRCFILES = $(shell find ${SRCDIRS} -name '*.py' $(foreach EXCLUDE,$(EXCLUDES),-not -path $(EXCLUDE)))

build:
	poetry install

build-docker:
	docker build . -t gptme:latest -f scripts/Dockerfile
	docker build . -t gptme-eval:latest -f scripts/Dockerfile.eval

build-docker-full:
	docker build . -t gptme-eval:latest -f scripts/Dockerfile.eval --build-arg RUST=yes --build-arg BROWSER=yes

test:
	@# if SLOW is not set, pass `-m "not slow"` to skip slow tests
	poetry run pytest ${SRCDIRS} -v --log-level INFO --durations=5 \
		--cov=devopsx --cov-report=xml --cov-report=term-missing --cov-report=html \
		-n 16 \
		$(if $(EVAL), , -m "not eval") \
		$(if $(SLOW), --timeout 60 --retries 2 --retry-delay 5, --timeout 5 -m "not slow and not eval") \
		$(if $(PROFILE), --profile-svg)

eval:
	poetry run python3 -m devopsx.eval

typecheck:
	poetry run mypy --ignore-missing-imports --check-untyped-defs ${SRCDIRS} $(if $(EXCLUDES),$(foreach EXCLUDE,$(EXCLUDES),--exclude $(EXCLUDE)))
	RUFF_ARGS=${SRCDIRS} $(foreach EXCLUDE,$(EXCLUDES),--exclude $(EXCLUDE))

lint:
	poetry run ruff check ${RUFF_ARGS}

format:
	poetry run ruff check --fix-only ${RUFF_ARGS}
	poetry run ruff format ${RUFF_ARGS}

precommit: format lint typecheck

docs/.clean: docs/conf.py
	poetry run make -C docs clean
	touch docs/.clean

docs: docs/conf.py docs/*.rst docs/.clean
	poetry run make -C docs html SPHINXOPTS="-W --keep-going"

version:
	@./scripts/bump_version.sh

./scripts/build_changelog.py:
	wget -O $@ https://raw.githubusercontent.com/ActivityWatch/activitywatch/master/scripts/build_changelog.py
	chmod +x $@

dist/CHANGELOG.md: version ./scripts/build_changelog.py
	VERSION=$$(git describe --tags --abbrev=0) && \
	PREV_VERSION=$$(./scripts/get-last-version.sh $${VERSION}) && \
		./scripts/build_changelog.py --range $${PREV_VERSION}...$${VERSION} --project-title devopsx --org computer.com --repo devopsx --output $@

release: dist/CHANGELOG.md
	@VERSION=$$(git describe --tags --abbrev=0) && \
		echo "Releasing version $${VERSION}"; \
		read -p "Press enter to continue" && \
		git push origin master $${VERSION} && \
		gh release create $${VERSION} -t $${VERSION} -F dist/CHANGELOG.md

clean: clean-docs

clean-docs:
	poetry run make -C docs clean

clean-test:
	echo $$HOME/.local/share/devopsx/logs/*test-*-test_*
	rm -I $$HOME/.local/share/devopsx/logs/*test-*-test_*/*.jsonl || true
	rm --dir $$HOME/.local/share/devopsx/logs/*test-*-test_*/ || true

cloc: cloc-core cloc-tools cloc-server cloc-tests

cloc-core:
	cloc devopsx/*.py devopsx/tools/__init__.py devopsx/tools/base.py --by-file

cloc-tools:
	cloc devopsx/tools/*.py --by-file

cloc-server:
	cloc devopsx/server --by-file

cloc-tests:
	cloc tests/*.py --by-file

cloc-eval:
	cloc devopsx/eval/**.py --by-file

cloc-total:
	cloc ${SRCFILES} --by-file

bench-importtime:
	time poetry run python -X importtime -m devopsx --model openrouter --non-interactive 2>&1 | grep "import time" | cut -d'|' -f 2- | sort -n