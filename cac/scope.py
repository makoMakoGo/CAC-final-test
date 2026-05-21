"""Scope resolution Module."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional, cast

import yaml

from .question import Question


CATEGORY_MAP = {
    "math": "数理能力基准测试题库",
    "code": "代码能力基准测试题库",
    "logic": "自然语言与逻辑能力基准测试题库",
    "comp": "综合能力测评",
    "comprehensive": "综合能力测评",
    "hallucination": "幻觉控制与指令遵循测试",
}


class ScopeResolver:
    def __init__(self, banks_config_path: str | Path = "data/question_banks.yaml"):
        self.banks_config_path = Path(banks_config_path).resolve()
        self.banks_config = self._load_banks_config()
        self.base_dir = self.banks_config_path.parent.parent

    def _load_banks_config(self) -> dict[str, Any]:
        with open(self.banks_config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"题库配置必须是对象: {self.banks_config_path}")
        return cast(dict[str, Any], data)

    def resolve(self, scope_str: str, range_str: Optional[str] = None) -> list[Question]:
        parts = scope_str.strip("/").split("/")
        category = parts[0]
        difficulty = parts[1] if len(parts) > 1 else None
        range_start, range_end = self._parse_range(range_str)

        bank_path = self._get_bank_path(category)
        if bank_path is None:
            raise ValueError(f"未知的题库类别: {category}")

        questions = self._scan_questions(bank_path, difficulty, range_start, range_end)
        return sorted(questions, key=lambda q: (q.path.parent.name, q.number))

    def _parse_range(self, range_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        if not range_str:
            return None, None
        if "-" in range_str:
            start, end = range_str.split("-", 1)
            return int(start), int(end)
        num = int(range_str)
        return num, num

    def _get_bank_path(self, category: str) -> Optional[Path]:
        if category in CATEGORY_MAP:
            return (self.base_dir.parent / CATEGORY_MAP[category]).resolve()

        for bank in self.banks_config.get("banks", []):
            if bank.get("category") == category:
                return (self.base_dir / str(bank["path"])).resolve()

        return None

    def _scan_questions(
        self,
        bank_path: Path,
        difficulty: Optional[str],
        range_start: Optional[int],
        range_end: Optional[int],
    ) -> list[Question]:
        questions: list[Question] = []

        def is_in_range(number: int) -> bool:
            if range_start is not None and number < range_start:
                return False
            if range_end is not None and number > range_end:
                return False
            return True

        def scan_difficulty_dir(difficulty_dir: Path) -> None:
            if not difficulty_dir.exists():
                return

            for item in difficulty_dir.iterdir():
                if not item.is_dir():
                    continue
                match = re.match(r"^(\d+)", item.name)
                if not match:
                    continue
                question = Question(path=item, id=item.name, number=int(match.group(1)))
                if not question.prompt_file.exists():
                    continue
                if not is_in_range(question.number):
                    continue
                questions.append(question)

        if difficulty:
            scan_difficulty_dir(bank_path / self._normalize_difficulty(difficulty))
            return questions

        for diff_dir in ["base-test", "advanced-test", "final-test", "final-test+"]:
            scan_difficulty_dir(bank_path / diff_dir)
        return questions

    def _normalize_difficulty(self, difficulty: str) -> str:
        difficulty = difficulty.rstrip("/")
        if difficulty in {"base-test", "advanced-test", "final-test", "final-test+"}:
            return difficulty
        if difficulty.endswith("-test"):
            return difficulty
        if difficulty == "final+":
            return "final-test+"
        return f"{difficulty}-test"
