from pathlib import Path

from scripts.doctor import overall_ok, run_health_checks


def test_doctor_passes_for_repository() -> None:
    root = Path(__file__).resolve().parents[1]

    checks = run_health_checks(root)

    assert overall_ok(checks)
    assert any(check.name == "question bank config" for check in checks)
    assert any(check.name == "import: cac.cli" for check in checks)
