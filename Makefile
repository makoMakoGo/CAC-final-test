.PHONY: ci test validate lint typecheck security quality doctor

PYTHON_PATHS := cac scripts tests
REQUIREMENTS := cac/requirements.txt

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

quality:
	uvx deptry $(PYTHON_PATHS) --requirements-files $(REQUIREMENTS) --known-first-party cac --known-first-party scripts --package-module-name-map pyyaml=yaml --per-rule-ignores "DEP002=pytest|pytest-cov"
	uvx radon cc $(PYTHON_PATHS) --min D --show-complexity --average --exclude .git,.venv,venv,__pycache__,test-results
	uvx vulture $(PYTHON_PATHS) --min-confidence 80
	npx --yes jscpd --config .jscpd.json --noTips
