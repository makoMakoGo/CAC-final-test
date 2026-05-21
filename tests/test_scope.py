from pathlib import Path

from cac.question import model_artifact_name
from cac.scope import ScopeResolver


def _write_question(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "prompt.md").write_text("prompt", encoding="utf-8")


def test_resolve_scope_with_difficulty_and_range(tmp_path: Path) -> None:
    bank = tmp_path / "数理能力基准测试题库"
    _write_question(bank / "base-test" / "001-first")
    _write_question(bank / "base-test" / "003-third")
    _write_question(bank / "advanced-test" / "002-advanced")

    config_path = tmp_path / "cac" / "data" / "question_banks.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("banks: []\n", encoding="utf-8")

    resolver = ScopeResolver(str(config_path))
    questions = resolver.resolve("math/base", "002-003")

    assert [question.id for question in questions] == ["003-third"]
    assert questions[0].number == 3
    assert questions[0].prompt_file == bank / "base-test" / "003-third" / "prompt.md"


def test_resolve_scope_uses_configured_bank(tmp_path: Path) -> None:
    bank = tmp_path / "custom-bank"
    _write_question(bank / "final-test+" / "010-final-plus")

    config_path = tmp_path / "cac" / "data" / "question_banks.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
banks:
  - path: ../custom-bank
    category: custom
""".lstrip(),
        encoding="utf-8",
    )

    resolver = ScopeResolver(str(config_path))
    questions = resolver.resolve("custom/final+")

    assert [question.id for question in questions] == ["010-final-plus"]


def test_question_owns_result_paths(tmp_path: Path) -> None:
    bank = tmp_path / "数理能力基准测试题库"
    _write_question(bank / "base-test" / "001-first")
    config_path = tmp_path / "cac" / "data" / "question_banks.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("banks: []\n", encoding="utf-8")

    question = ScopeResolver(str(config_path)).resolve("math/base", "001")[0]

    assert model_artifact_name("vendor/model:1") == "vendor_model_1"
    assert (
        question.answer_file("vendor/model:1")
        == question.path / "test-results" / "vendor_model_1.md"
    )
    assert (
        question.judge_file("vendor/model:1")
        == question.path / "test-results" / "vendor_model_1.judge.yaml"
    )


def test_resolve_unknown_category_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "cac" / "data" / "question_banks.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("banks: []\n", encoding="utf-8")

    resolver = ScopeResolver(str(config_path))

    try:
        resolver.resolve("missing")
    except ValueError as exc:
        assert str(exc) == "未知的题库类别: missing"
    else:
        raise AssertionError("expected ValueError")
