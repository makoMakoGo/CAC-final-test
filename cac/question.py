"""Question artifact Module.

This Module owns the benchmark question directory contract: source files,
result files, and model-name-to-artifact-name conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml


_MODEL_ARTIFACT_TRANSLATION = str.maketrans({"/": "_", "\\": "_", ":": "_"})


def model_artifact_name(model_name: str) -> str:
    name = model_name.strip()
    if not name:
        raise ValueError("模型名称不能为空")
    return name.translate(_MODEL_ARTIFACT_TRANSLATION)


@dataclass(frozen=True)
class Question:
    path: Path
    id: str
    number: int

    @property
    def prompt_file(self) -> Path:
        return self.path / "prompt.md"

    @property
    def reference_file(self) -> Path:
        return self.path / "reference.md"

    @property
    def meta_file(self) -> Path:
        return self.path / "meta.yaml"

    @property
    def results_dir(self) -> Path:
        return self.path / "test-results"

    def answer_file(self, model_name: str) -> Path:
        return self.results_dir / f"{model_artifact_name(model_name)}.md"

    def judge_file(self, target_model: str) -> Path:
        return self.results_dir / f"{model_artifact_name(target_model)}.judge.yaml"

    def read_prompt(self) -> str:
        return self._read_text(self.prompt_file, "prompt.md")

    def read_reference(self) -> str:
        return self._read_text(self.reference_file, "reference.md")

    def read_answer(self, model_name: str) -> str:
        return self._read_text(
            self.answer_file(model_name), f"{model_artifact_name(model_name)}.md"
        )

    def read_meta(self) -> dict[str, Any]:
        if not self.meta_file.exists():
            raise FileNotFoundError(f"缺少 meta.yaml: {self.meta_file}")
        with open(self.meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        if not isinstance(meta, dict):
            raise ValueError(f"meta.yaml 必须是对象: {self.meta_file}")
        return cast(dict[str, Any], meta)

    def write_answer(self, model_name: str, response: str) -> Path:
        output_file = self.answer_file(model_name)
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text(response, encoding="utf-8")
        return output_file

    def _read_text(self, path: Path, label: str) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"缺少 {label}: {path}") from e
