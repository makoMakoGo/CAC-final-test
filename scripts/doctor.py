#!/usr/bin/env python3
"""Local repository health checks."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_PATHS = (
    "pyproject.toml",
    "cac/requirements.txt",
    "cac/data/question_banks.yaml",
    "scripts/validate_questions.py",
)
REQUIRED_IMPORTS = ("cac.cli", "cac.config", "cac.scope", "yaml", "requests", "rich")


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str


def run_health_checks(root: Path) -> list[HealthCheck]:
    root = root.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    checks: list[HealthCheck] = []
    checks.extend(_check_required_paths(root))
    checks.extend(_check_imports())
    checks.extend(_check_question_banks(root))
    return checks


def overall_ok(checks: list[HealthCheck]) -> bool:
    return all(check.ok for check in checks)


def _check_required_paths(root: Path) -> list[HealthCheck]:
    checks = []
    for relative_path in REQUIRED_PATHS:
        path = root / relative_path
        checks.append(
            HealthCheck(
                name=f"required path: {relative_path}",
                ok=path.exists(),
                detail="found" if path.exists() else "missing",
            )
        )
    return checks


def _check_imports() -> list[HealthCheck]:
    checks = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            checks.append(
                HealthCheck(
                    name=f"import: {module_name}",
                    ok=False,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
        else:
            checks.append(HealthCheck(name=f"import: {module_name}", ok=True, detail="ok"))
    return checks


def _check_question_banks(root: Path) -> list[HealthCheck]:
    config_path = root / "cac/data/question_banks.yaml"
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [
            HealthCheck(
                name="question bank config",
                ok=False,
                detail=f"{type(exc).__name__}: {exc}",
            )
        ]

    if not isinstance(raw, dict):
        return [HealthCheck(name="question bank config", ok=False, detail="top-level is not a map")]

    banks = raw.get("banks")
    if not isinstance(banks, list) or not banks:
        return [HealthCheck(name="question bank config", ok=False, detail="banks list is empty")]

    checks = [
        HealthCheck(
            name="question bank config",
            ok=True,
            detail=f"{len(banks)} banks configured",
        )
    ]
    for bank in banks:
        checks.append(_check_question_bank(root, bank))
    return checks


def _check_question_bank(root: Path, bank: Any) -> HealthCheck:
    if not isinstance(bank, dict):
        return HealthCheck(name="question bank", ok=False, detail="entry is not a map")

    category = str(bank.get("category", "<missing>"))
    raw_path = bank.get("path")
    if not isinstance(raw_path, str):
        return HealthCheck(name=f"question bank: {category}", ok=False, detail="path is missing")

    bank_path = (root / "cac" / raw_path).resolve()
    if not bank_path.is_dir():
        return HealthCheck(
            name=f"question bank: {category}",
            ok=False,
            detail=f"missing directory: {bank_path}",
        )

    question_count = _count_questions(bank_path)
    return HealthCheck(
        name=f"question bank: {category}",
        ok=question_count > 0,
        detail=f"{question_count} questions found",
    )


def _count_questions(bank_path: Path) -> int:
    return sum(
        1
        for meta_path in bank_path.rglob("meta.yaml")
        if (meta_path.parent / "prompt.md").exists()
        and (meta_path.parent / "reference.md").exists()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CAC repository health checks")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    checks = run_health_checks(args.root)
    ok = overall_ok(checks)
    if args.json:
        print(json.dumps({"ok": ok, "checks": [asdict(check) for check in checks]}))
    else:
        for check in checks:
            status = "OK" if check.ok else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
