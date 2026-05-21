#!/usr/bin/env python3
"""Question format validator."""

from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    print("⚠️ 需要安装 pyyaml: pip install pyyaml")
    sys.exit(1)

from cac.indicators import (  # noqa: E402
    IndicatorCatalog,
    default_indicator_path,
    scoring_indicators_from_meta,
)


QUESTION_BANKS = [
    "代码能力基准测试题库",
    "数理能力基准测试题库",
    "自然语言与逻辑能力基准测试题库",
]
HALLUCINATION_BANK = "幻觉控制与指令遵循测试"
COMPREHENSIVE_BANK = "综合能力测评"
DIFFICULTY_LEVELS = ["base-test", "advanced-test", "final-test", "final-test+"]
REQUIRED_FILES = ["README.md", "meta.yaml", "prompt.md", "reference.md"]
COMPREHENSIVE_REQUIRED_FILES = ["prompt.md", "meta.yaml", "reference.md"]
VALID_CATEGORIES = [
    "math",
    "code",
    "logic",
    "comprehensive",
    "comp",
    "design",
    "theory",
    "hallucination",
]
VALID_DIFFICULTIES = ["base", "advanced", "final", "final+"]


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"❌ {self.path}: {self.message}"


@dataclass(frozen=True)
class ValidationWarning:
    path: str
    message: str

    def __str__(self) -> str:
        return f"⚠️ {self.path}: {self.message}"


def is_question_dir(path: Path) -> bool:
    return bool(re.match(r"^\d{3}-", path.name))


def validate_meta_yaml(
    meta_path: Path, catalog: IndicatorCatalog
) -> tuple[list[ValidationError], list[ValidationWarning]]:
    errors: list[ValidationError] = []
    warnings: list[ValidationWarning] = []

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [ValidationError(str(meta_path), f"YAML 解析错误: {e}")], warnings
    except Exception as e:
        return [ValidationError(str(meta_path), f"文件读取错误: {e}")], warnings

    if not isinstance(meta, dict):
        return [ValidationError(str(meta_path), "meta.yaml 必须是一个字典")], warnings

    required_fields = ["id", "brief", "category", "difficulty", "scoring_std"]
    for field in required_fields:
        if field not in meta:
            errors.append(ValidationError(str(meta_path), f"缺少必需字段: {field}"))

    if "category" in meta and meta["category"] not in VALID_CATEGORIES:
        errors.append(ValidationError(str(meta_path), f"无效的 category: {meta['category']}"))

    if "difficulty" in meta and meta["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(ValidationError(str(meta_path), f"无效的 difficulty: {meta['difficulty']}"))

    if "scoring_std" in meta:
        scoring = meta["scoring_std"]
        if not isinstance(scoring, dict):
            errors.append(ValidationError(str(meta_path), "scoring_std 必须是字典"))
        else:
            if "max_score" not in scoring:
                errors.append(ValidationError(str(meta_path), "scoring_std 缺少 max_score"))
            if "indicators" not in scoring:
                errors.append(ValidationError(str(meta_path), "scoring_std 缺少 indicators"))
            else:
                try:
                    indicators = scoring_indicators_from_meta(meta)
                except ValueError as e:
                    errors.append(ValidationError(str(meta_path), str(e)))
                else:
                    for indicator in catalog.unknown(indicators):
                        warnings.append(
                            ValidationWarning(str(meta_path), f"未知的 indicator: {indicator}")
                        )

    return errors, warnings


def validate_question_dir(
    question_path: Path,
    catalog: IndicatorCatalog,
    required_files: list[str],
) -> tuple[list[ValidationError], list[ValidationWarning]]:
    errors: list[ValidationError] = []
    warnings: list[ValidationWarning] = []

    for required_file in required_files:
        if not (question_path / required_file).exists():
            errors.append(ValidationError(str(question_path), f"缺少必需文件: {required_file}"))

    meta_path = question_path / "meta.yaml"
    if meta_path.exists():
        meta_errors, meta_warnings = validate_meta_yaml(meta_path, catalog)
        errors.extend(meta_errors)
        warnings.extend(meta_warnings)

    for file_name in ["prompt.md", "reference.md"]:
        path = question_path / file_name
        if path.exists() and not path.read_text(encoding="utf-8").strip():
            errors.append(ValidationError(str(path), f"{file_name} 不能为空"))

    return errors, warnings


def main() -> None:
    catalog = IndicatorCatalog.from_file(default_indicator_path())
    all_errors: list[ValidationError] = []
    all_warnings: list[ValidationWarning] = []
    validated_count = 0

    print("🔍 开始验证题目格式...\n")

    for bank in QUESTION_BANKS:
        bank_path = Path(bank)
        if not bank_path.exists():
            continue
        print(f"📁 检查题库: {bank}")
        for level in DIFFICULTY_LEVELS:
            level_path = bank_path / level
            if not level_path.exists():
                continue
            for item in level_path.iterdir():
                if item.is_dir() and is_question_dir(item):
                    errors, warnings = validate_question_dir(item, catalog, REQUIRED_FILES)
                    all_errors.extend(errors)
                    all_warnings.extend(warnings)
                    validated_count += 1
                    print(f"  {'❌' if errors else '✅'} {item.name}")

    hallucination_path = Path(HALLUCINATION_BANK)
    if hallucination_path.exists():
        print(f"\n📁 检查题库: {HALLUCINATION_BANK}")
        for level in DIFFICULTY_LEVELS:
            level_path = hallucination_path / level
            if not level_path.exists():
                continue
            for item in level_path.iterdir():
                if item.is_dir() and is_question_dir(item):
                    errors, warnings = validate_question_dir(
                        item, catalog, COMPREHENSIVE_REQUIRED_FILES
                    )
                    all_errors.extend(errors)
                    all_warnings.extend(warnings)
                    validated_count += 1
                    print(f"  {'❌' if errors else '✅'} {item.name}")
    comp_path = Path(COMPREHENSIVE_BANK)
    if comp_path.exists():
        print(f"\n📁 检查题库: {COMPREHENSIVE_BANK}")
        for item in comp_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                errors, warnings = validate_question_dir(
                    item, catalog, COMPREHENSIVE_REQUIRED_FILES
                )
                all_errors.extend(errors)
                all_warnings.extend(warnings)
                validated_count += 1
                print(f"  {'❌' if errors else '✅'} {item.name}")

    print(f"\n{'=' * 50}")
    print(f"验证完成: 共检查 {validated_count} 个题目")

    if all_warnings:
        print(f"\n⚠️ 警告 ({len(all_warnings)} 个):")
        for warning in all_warnings:
            print(f"  {warning}")

    if all_errors:
        print(f"\n❌ 错误 ({len(all_errors)} 个):")
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)

    print("\n✅ 所有题目格式验证通过！")
    sys.exit(0)


if __name__ == "__main__":
    main()
