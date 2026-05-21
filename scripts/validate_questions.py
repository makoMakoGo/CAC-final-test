#!/usr/bin/env python3
"""
题目格式验证脚本

检查所有题目目录是否包含必需的文件，以及文件格式是否正确。

使用方法：
    python scripts/validate_questions.py
"""

import sys
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    print("⚠️ 需要安装 pyyaml: pip install pyyaml")
    sys.exit(1)

# 题库路径
QUESTION_BANKS = [
    "代码能力基准测试题库",
    "数理能力基准测试题库",
    "自然语言与逻辑能力基准测试题库",
]

COMPREHENSIVE_BANK = "综合能力测评"

# 难度级别
DIFFICULTY_LEVELS = ["base-test", "advanced-test", "final-test", "final-test+"]

# 必需文件
REQUIRED_FILES = ["README.md", "meta.yaml", "prompt.md", "reference.md"]

# 有效的 category 值
VALID_CATEGORIES = ["math", "code", "logic", "comprehensive", "design", "theory"]

# 有效的 difficulty 值
VALID_DIFFICULTIES = ["base", "advanced", "final", "final+"]

# 有效的 indicators
VALID_INDICATORS = [
    "ans_correct",
    "code_quality",
    "efficiency",
    "robustness",
    "completeness",
    "accuracy",
    "clarity",
    "depth",
    "example_quality",
    "practicality",
    "correct_max_1",
]


class ValidationError:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"❌ {self.path}: {self.message}"


class ValidationWarning:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"⚠️ {self.path}: {self.message}"


def is_question_dir(path: Path) -> bool:
    """判断是否是题目目录（以数字编号开头）"""
    return bool(re.match(r"^\d{3}-", path.name))


def validate_meta_yaml(meta_path: Path) -> tuple:
    """验证 meta.yaml 文件格式"""
    errors = []
    warnings = []

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(ValidationError(str(meta_path), f"YAML 解析错误: {e}"))
        return errors, warnings
    except Exception as e:
        errors.append(ValidationError(str(meta_path), f"文件读取错误: {e}"))
        return errors, warnings

    if not isinstance(meta, dict):
        errors.append(ValidationError(str(meta_path), "meta.yaml 必须是一个字典"))
        return errors, warnings

    # 检查必需字段
    required_fields = ["id", "brief", "category", "difficulty", "scoring_std"]
    for field in required_fields:
        if field not in meta:
            errors.append(ValidationError(str(meta_path), f"缺少必需字段: {field}"))

    # 检查 category
    if "category" in meta and meta["category"] not in VALID_CATEGORIES:
        errors.append(ValidationError(str(meta_path), f"无效的 category: {meta['category']}"))

    # 检查 difficulty
    if "difficulty" in meta and meta["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(ValidationError(str(meta_path), f"无效的 difficulty: {meta['difficulty']}"))

    # 检查 scoring_std
    if "scoring_std" in meta:
        scoring = meta["scoring_std"]
        if isinstance(scoring, dict):
            if "max_score" not in scoring:
                errors.append(ValidationError(str(meta_path), "scoring_std 缺少 max_score"))
            if "indicators" not in scoring:
                errors.append(ValidationError(str(meta_path), "scoring_std 缺少 indicators"))
            elif isinstance(scoring["indicators"], list):
                for indicator in scoring["indicators"]:
                    if indicator not in VALID_INDICATORS:
                        warnings.append(
                            ValidationWarning(str(meta_path), f"未知的 indicator: {indicator}")
                        )

    return errors, warnings


def validate_question_dir(question_path: Path) -> tuple:
    """验证单个题目目录"""
    errors = []
    warnings = []

    # 检查必需文件
    for required_file in REQUIRED_FILES:
        if not (question_path / required_file).exists():
            errors.append(ValidationError(str(question_path), f"缺少必需文件: {required_file}"))

    # 验证 meta.yaml
    meta_path = question_path / "meta.yaml"
    if meta_path.exists():
        meta_errors, meta_warnings = validate_meta_yaml(meta_path)
        errors.extend(meta_errors)
        warnings.extend(meta_warnings)

    # 检查 prompt.md 不为空
    prompt_path = question_path / "prompt.md"
    if prompt_path.exists():
        if not prompt_path.read_text(encoding="utf-8").strip():
            errors.append(ValidationError(str(prompt_path), "prompt.md 不能为空"))

    # 检查 reference.md 不为空
    reference_path = question_path / "reference.md"
    if reference_path.exists():
        if not reference_path.read_text(encoding="utf-8").strip():
            errors.append(ValidationError(str(reference_path), "reference.md 不能为空"))

    return errors, warnings


def validate_comprehensive_dir(question_path: Path) -> tuple:
    """验证综合能力测评目录"""
    errors = []
    warnings = []

    required_files = ["prompt.md", "meta.yaml", "reference.md"]
    for required_file in required_files:
        if not (question_path / required_file).exists():
            errors.append(ValidationError(str(question_path), f"缺少必需文件: {required_file}"))

    meta_path = question_path / "meta.yaml"
    if meta_path.exists():
        meta_errors, meta_warnings = validate_meta_yaml(meta_path)
        errors.extend(meta_errors)
        warnings.extend(meta_warnings)

    return errors, warnings


def main():
    all_errors = []
    all_warnings = []
    validated_count = 0

    print("🔍 开始验证题目格式...\n")

    # 验证三大基准测试题库
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
                    errors, warnings = validate_question_dir(item)
                    all_errors.extend(errors)
                    all_warnings.extend(warnings)
                    validated_count += 1
                    print(f"  {'❌' if errors else '✅'} {item.name}")

    # 验证综合能力测评
    comp_path = Path(COMPREHENSIVE_BANK)
    if comp_path.exists():
        print(f"\n📁 检查题库: {COMPREHENSIVE_BANK}")

        for item in comp_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                errors, warnings = validate_comprehensive_dir(item)
                all_errors.extend(errors)
                all_warnings.extend(warnings)
                validated_count += 1
                print(f"  {'❌' if errors else '✅'} {item.name}")

    # 输出结果
    print(f"\n{'=' * 50}")
    print(f"验证完成: 共检查 {validated_count} 个题目")

    if all_warnings:
        print(f"\n⚠️ 警告 ({len(all_warnings)} 个):")
        for w in all_warnings:
            print(f"  {w}")

    if all_errors:
        print(f"\n❌ 错误 ({len(all_errors)} 个):")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\n✅ 所有题目格式验证通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
