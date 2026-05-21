"""Judgement prompt and structured-output Module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .providers import StructuredRequest


@dataclass(frozen=True)
class JudgeScore:
    total_score: float
    max_score: float
    indicators: list[str]
    dimensions: dict[str, Any]
    feedback: str


def build_judge_schema(max_score: float, indicators: list[str]) -> dict[str, Any]:
    dimension_properties: dict[str, Any] = {}
    for indicator in indicators:
        dimension_properties[indicator] = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "description": f"{indicator} 维度得分"},
                "comment": {"type": "string", "description": f"{indicator} 维度评价"},
            },
            "required": ["score", "comment"],
        }

    return {
        "name": "submit_score",
        "description": f"提交评分结果，满分 {max_score} 分",
        "parameters": {
            "type": "object",
            "properties": {
                "total_score": {
                    "type": "number",
                    "description": f"总分（0-{max_score}）",
                },
                "dimensions": {
                    "type": "object",
                    "description": "各维度评分",
                    "properties": dimension_properties,
                    "required": indicators,
                },
                "feedback": {
                    "type": "string",
                    "description": "总体评价",
                },
            },
            "required": ["total_score", "dimensions", "feedback"],
        },
    }


def build_judge_request(
    prompt: str,
    reference: str,
    answer: str,
    indicators: list[str],
    max_score: float,
) -> StructuredRequest:
    indicators_list = "\n".join(f"- {indicator}" for indicator in indicators)
    base = f"""你是专业评审员。请根据以下信息评分：

## 原题目
{prompt}

## 参考答案/评分标准
{reference}

## 被测模型的回答
{answer}

## 评分维度（满分 {max_score} 分）
{indicators_list}
"""
    tool_prompt = base + "\n请调用 submit_score 工具提交评分结果。"
    text_prompt = (
        base
        + """
请严格按照以下 JSON 格式输出（不要输出其他内容）：
```json
{
  "total_score": <总分>,
  "dimensions": {
    "<维度名>": {"score": <得分>, "comment": "<简短评价>"}
  },
  "feedback": "<总体评价>"
}
```"""
    )
    return StructuredRequest(
        tool_prompt=tool_prompt,
        text_prompt=text_prompt,
        tool_schema=build_judge_schema(max_score, indicators),
    )


def normalize_judge_score(
    raw: dict[str, Any], max_score: float, indicators: list[str]
) -> JudgeScore:
    total_score_raw = raw.get("total_score")
    if total_score_raw is None:
        raise ValueError("评分输出缺少 total_score")
    try:
        total_score = float(total_score_raw)
    except (TypeError, ValueError) as e:
        raise ValueError(f"评分输出 total_score 非数字: {total_score_raw!r}") from e
    if total_score < 0 or total_score > max_score + 1e-6:
        raise ValueError(f"评分输出 total_score 越界: {total_score}/{max_score}")

    dimensions = raw.get("dimensions", {})
    if dimensions is None:
        dimensions = {}
    if not isinstance(dimensions, dict):
        raise ValueError(f"评分输出 dimensions 必须是对象: {type(dimensions).__name__}")

    feedback = raw.get("feedback", "")
    if feedback is None:
        feedback = ""
    if not isinstance(feedback, str):
        feedback = str(feedback)

    return JudgeScore(
        total_score=total_score,
        max_score=max_score,
        indicators=indicators,
        dimensions=dimensions,
        feedback=feedback,
    )
