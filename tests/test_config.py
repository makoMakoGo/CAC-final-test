from pathlib import Path

import pytest

from src.config import ModelConfig, RetryConfig, expand_env_vars, load_config


def test_expand_env_vars_supports_braced_and_plain_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAC_API_KEY", "secret-key")
    monkeypatch.setenv("CAC_MODEL", "demo")

    assert expand_env_vars("${CAC_API_KEY}:$CAC_MODEL") == "secret-key:demo"


def test_expand_env_vars_raises_for_missing_variable() -> None:
    with pytest.raises(ValueError, match="环境变量未设置: CAC_MISSING"):
        expand_env_vars("${CAC_MISSING}")


def test_load_config_expands_env_and_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAC_API_KEY", "secret-key")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
test-model:
  name: demo-model
  provider: openai
  api_key: ${CAC_API_KEY}
  base_url: https://api.example.test/v1
retry:
  max_attempts: 2
  delay: 0.5
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.test_model == ModelConfig(
        name="demo-model",
        provider="openai",
        api_key="secret-key",
        base_url="https://api.example.test/v1",
        model_id="demo-model",
        params={},
    )
    assert config.judge_model is None
    assert config.retry == RetryConfig(max_attempts=2, delay=0.5)
    assert config.question_banks == "data/question_banks.yaml"


def test_load_config_rejects_missing_test_model(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("retry: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="配置缺少 test-model"):
        load_config(str(config_path))
