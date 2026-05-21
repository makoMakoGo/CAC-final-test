"""Scoring indicator Module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, cast

import yaml


@dataclass(frozen=True)
class IndicatorCatalog:
    descriptions: dict[str, str]

    @classmethod
    def from_file(cls, path: str | Path) -> "IndicatorCatalog":
        catalog_path = Path(path)
        with open(catalog_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, list):
            raise ValueError(f"indicators.yaml 必须是列表: {catalog_path}")

        descriptions: dict[str, str] = {}
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError(f"indicator category 必须是对象: {entry!r}")
            indicators = entry.get("indicators", {})
            if not isinstance(indicators, dict):
                raise ValueError(f"indicators 必须是对象: {entry!r}")
            for name, description in indicators.items():
                if not isinstance(name, str):
                    raise ValueError(f"indicator 名称必须是字符串: {name!r}")
                descriptions[name] = str(description)
        return cls(descriptions=descriptions)

    @property
    def names(self) -> set[str]:
        return set(self.descriptions)

    def unknown(self, indicators: Iterable[str]) -> list[str]:
        names = self.names
        return [indicator for indicator in indicators if indicator not in names]

    def validate(self, indicators: Iterable[str]) -> None:
        unknown = self.unknown(indicators)
        if unknown:
            raise ValueError(f"未知的 indicator: {', '.join(unknown)}")


def default_indicator_path(start: str | Path | None = None) -> Path:
    base = Path.cwd() if start is None else Path(start)
    candidates = [
        base / "cac" / "data" / "indicators.yaml",
        base / "data" / "indicators.yaml",
        base.parent / "cac" / "data" / "indicators.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_indicator_catalog(path: str | Path | None = None) -> IndicatorCatalog:
    return IndicatorCatalog.from_file(path or default_indicator_path())


def scoring_indicators_from_meta(meta: dict[str, Any]) -> list[str]:
    scoring_std = meta.get("scoring_std", {})
    if not isinstance(scoring_std, dict):
        raise ValueError("meta.yaml scoring_std 必须是对象")
    indicators = scoring_std.get("indicators")
    if indicators is None:
        raise ValueError("meta.yaml scoring_std 缺少 indicators")
    if not isinstance(indicators, list):
        raise ValueError(
            f"meta.yaml scoring_std.indicators 必须是列表: {type(indicators).__name__}"
        )
    for indicator in indicators:
        if not isinstance(indicator, str):
            raise ValueError(f"indicator 必须是字符串: {indicator!r}")
    return cast(list[str], indicators)


def max_score_from_meta(meta: dict[str, Any]) -> float:
    scoring_std = meta.get("scoring_std", {})
    if not isinstance(scoring_std, dict):
        raise ValueError("meta.yaml scoring_std 必须是对象")
    raw = scoring_std.get("max_score")
    if raw is None:
        raise ValueError("meta.yaml scoring_std 缺少 max_score")
    try:
        return float(raw)
    except (TypeError, ValueError) as e:
        raise ValueError(f"meta.yaml scoring_std.max_score 非数字: {raw!r}") from e
