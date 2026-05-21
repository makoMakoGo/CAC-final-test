.PHONY: ci test validate lint typecheck security quality doctor secret-scan

PYTHON_PATHS := cac scripts tests
REQUIREMENTS := cac/requirements.txt
SECRET_SCAN_EXCLUDE_FILES := (^|/)\.git/|(^|/)uv\.lock$$|(^|/)\.coverage$$|(^|/)\.mypy_cache/|(^|/)\.pytest_cache/|(^|/)\.ruff_cache/|(^|/)\.venv/
SECRET_SCAN_EXCLUDE_LINES := api_key: test-key|OPENAI_API_KEY=|ANTHROPIC_API_KEY=|GEMINI_API_KEY=|GH_TOKEN:|github\.token|sk-live|secret-token|secret-value|password=hunter2|token:abcd|x-api-key: gemini-key|secret-key|api_key: key|api_key=key|judge-key|api_key="key"|api_key: judge-key|api_key="judge-key"

ci: validate lint test typecheck doctor security quality

test:
	uvx --with-requirements $(REQUIREMENTS) pytest

validate:
	uv pip compile --no-header $(REQUIREMENTS)
	uv run --no-project --with pyyaml==6.0.3 python scripts/validate_questions.py

lint:
	uvx ruff check $(PYTHON_PATHS)
	uvx ruff format --check $(PYTHON_PATHS)

typecheck:
	uvx mypy --config-file pyproject.toml $(PYTHON_PATHS)

doctor:
	uvx --with-requirements $(REQUIREMENTS) python scripts/doctor.py

security:
	uvx bandit -r cac scripts --confidence-level medium --severity-level medium
	uvx pip-audit -r $(REQUIREMENTS)
	$(MAKE) secret-scan

secret-scan:
	uvx detect-secrets scan --all-files . --exclude-files '$(SECRET_SCAN_EXCLUDE_FILES)' --exclude-lines '$(SECRET_SCAN_EXCLUDE_LINES)' | python -c 'import json, sys; data = json.load(sys.stdin); results = data.get("results", {}); print("No secrets detected" if not results else json.dumps(results, indent=2, ensure_ascii=False)); sys.exit(1 if results else 0)'

quality:
	uvx deptry $(PYTHON_PATHS) --requirements-files $(REQUIREMENTS) --known-first-party cac --known-first-party scripts --package-module-name-map pyyaml=yaml --per-rule-ignores "DEP002=pytest|pytest-cov"
	uvx radon cc $(PYTHON_PATHS) --min D --show-complexity --average --exclude .git,.venv,venv,__pycache__,test-results
	uvx vulture $(PYTHON_PATHS) --min-confidence 80
	npx --yes jscpd --config .jscpd.json --noTips
