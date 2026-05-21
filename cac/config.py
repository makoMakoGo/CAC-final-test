"""Configuration loading Module."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    api_key: str
    base_url: str
    model_id: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    delay: float = 10.0


@dataclass(frozen=True)
class Config:
    test_model: ModelConfig
    judge_model: Optional[ModelConfig]
    retry: RetryConfig
    question_banks: str = "data/question_banks.yaml"


def expand_env_vars(value: str) -> str:
    if not isinstance(value, str):
        return value

    pattern = r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1) or match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ValueError(f"环境变量未设置: {var_name}")
        return env_value

    return re.sub(pattern, replace, value)


def expand_env_vars_recursive(obj: Any) -> Any:
    if isinstance(obj, str):
        return expand_env_vars(obj)
    if isinstance(obj, dict):
        return {key: expand_env_vars_recursive(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [expand_env_vars_recursive(item) for item in obj]
    return obj


def _parse_model(data: dict[str, Any], section: str) -> ModelConfig:
    try:
        name = data.get("name", data.get("model_name"))
        if name is None:
            raise KeyError("name")
        provider = data["provider"]
        api_key = data["api_key"]
        base_url = data["base_url"]
        return ModelConfig(
            name=str(name),
            provider=str(provider),
            api_key=str(api_key),
            base_url=str(base_url),
            model_id=str(data.get("model_id", name)),
            params=data.get("params", {}),
        )
    except KeyError as e:
        raise ValueError(f"{section} 缺少字段: {e.args[0]}") from e


def load_config(config_path: str | Path) -> Config:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("配置格式无效: 顶层必须是 YAML map/object")

    test_model_data = raw.get("test-model")
    if test_model_data is None:
        test_models = raw.get("test")
        if isinstance(test_models, list) and test_models:
            test_model_data = test_models[0]
    if test_model_data is None:
        raise ValueError("配置缺少 test-model")
    if not isinstance(test_model_data, dict):
        raise ValueError("test-model 必须是对象")
    test_model = _parse_model(expand_env_vars_recursive(test_model_data), "test-model")

    judge_model_data = raw.get("judge-model", raw.get("judge"))
    if judge_model_data is None:
        judge_model = None
    else:
        if not isinstance(judge_model_data, dict):
            raise ValueError("judge-model 必须是对象")
        judge_model = _parse_model(expand_env_vars_recursive(judge_model_data), "judge-model")

    retry_data = raw.get("retry", {})
    if retry_data is None:
        retry_data = {}
    if not isinstance(retry_data, dict):
        raise ValueError("retry 必须是对象")
    retry_data = expand_env_vars_recursive(retry_data)
    retry = RetryConfig(
        max_attempts=int(retry_data.get("max_attempts", 3)),
        delay=float(retry_data.get("delay", 10.0)),
    )

    question_banks = expand_env_vars(raw.get("question_banks", "data/question_banks.yaml"))
    return Config(
        test_model=test_model,
        judge_model=judge_model,
        retry=retry,
        question_banks=question_banks,
    )
