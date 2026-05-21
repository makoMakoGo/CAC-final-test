from pathlib import Path
from typing import Any

import yaml

from cac.config import ModelConfig, RetryConfig
from cac.providers.base import BaseProvider, StructuredRequest
from cac.question import Question
from cac.runner import JudgeRunner, TestRunner


class EchoProvider(BaseProvider):
    def chat(self, prompt: str) -> str:
        return f"answer:{prompt}"


class StructuredProvider(BaseProvider):
    def chat(self, prompt: str) -> str:
        raise AssertionError("judge should use structured Interface")

    def structured(self, request: StructuredRequest) -> dict[str, Any]:
        assert "原题目" in request.text_prompt
        return {
            "total_score": 1,
            "dimensions": {"correct_max_1": {"score": 1, "comment": "ok"}},
            "feedback": "ok",
        }


def _config(name: str = "demo") -> ModelConfig:
    return ModelConfig(
        name=name, provider="custom", api_key="key", base_url="https://example.test", model_id=name
    )


def _question(path: Path) -> Question:
    path.mkdir(parents=True)
    (path / "prompt.md").write_text("prompt", encoding="utf-8")
    (path / "reference.md").write_text("reference", encoding="utf-8")
    (path / "meta.yaml").write_text(
        """
id: q-001
brief: demo
category: logic
difficulty: base
scoring_std:
  max_score: 1
  indicators:
    - correct_max_1
""".lstrip(),
        encoding="utf-8",
    )
    return Question(path=path, id=path.name, number=1)


def test_runner_writes_answer_through_question_artifact(tmp_path: Path) -> None:
    question = _question(tmp_path / "001-demo")
    runner = TestRunner(EchoProvider(_config("model/name:1")), RetryConfig(max_attempts=1, delay=0))

    summary = runner.run([question])

    assert summary.done == 1
    output_file = question.path / "test-results" / "model_name_1.md"
    assert output_file.read_text(encoding="utf-8") == "answer:prompt"
    assert summary.items[0].output_file == output_file


def test_judge_runner_uses_provider_structured_interface(tmp_path: Path) -> None:
    question = _question(tmp_path / "001-demo")
    question.write_answer("target", "model answer")
    runner = JudgeRunner(StructuredProvider(_config("judge")), RetryConfig(max_attempts=1, delay=0))

    summary = runner.judge([question], target_model="target")

    assert summary.done == 1
    output_file = question.judge_file("target")
    result = yaml.safe_load(output_file.read_text(encoding="utf-8"))
    assert result["total_score"] == 1
    assert result["indicators"] == ["correct_max_1"]


def test_judge_runner_reports_no_answer_without_calling_provider(tmp_path: Path) -> None:
    question = _question(tmp_path / "001-demo")
    runner = JudgeRunner(StructuredProvider(_config("judge")), RetryConfig(max_attempts=1, delay=0))

    summary = runner.judge([question], target_model="missing")

    assert summary.no_answer == 1
    assert summary.items[0].status == "no_answer"
