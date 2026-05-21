import json
import subprocess
import sys
from pathlib import Path


def test_cli_dry_run_json_lists_scope_questions(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
test-model:
  name: demo
  provider: custom
  api_key: test-key
  base_url: https://example.test
question_banks: cac/data/question_banks.yaml
""".lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cac",
            "--config",
            str(config_path),
            "--scope",
            "math/base-test",
            "--range",
            "001",
            "--dry-run",
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == "001-chicken-rabbit-cage"
