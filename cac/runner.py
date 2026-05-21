"""Benchmark run Module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

from .config import RetryConfig
from .execution import BatchExecutor, PendingItem, RetryExhaustedError
from .indicators import max_score_from_meta, scoring_indicators_from_meta
from .judgement import build_judge_request, normalize_judge_score
from .providers import BaseProvider
from .question import Question
from .reporting import Event, EventType, Phase, Reporter


@dataclass(frozen=True)
class TestItemResult:
    index: int
    question_id: str
    question_path: Path
    status: Literal["done", "skipped", "failed"]
    output_file: Optional[Path] = None
    elapsed_s: Optional[float] = None
    attempts: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class TestRunSummary:
    model_name: str
    total: int
    done: int
    skipped: int
    failed: int
    items: list[TestItemResult]


@dataclass(frozen=True)
class JudgeItemResult:
    index: int
    question_id: str
    question_path: Path
    target_model: str
    status: Literal["done", "skipped", "failed", "no_answer"]
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    dimensions: Optional[dict[str, Any]] = None
    feedback: Optional[str] = None
    output_file: Optional[Path] = None
    elapsed_s: Optional[float] = None
    attempts: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class JudgeSummary:
    judge_name: str
    target_model: str
    total: int
    done: int
    skipped: int
    failed: int
    no_answer: int
    avg_score: Optional[float]
    items: list[JudgeItemResult]


class TestRunner:
    def __init__(self, provider: BaseProvider, retry_config: RetryConfig, incremental: bool = True):
        self.provider = provider
        self.executor = BatchExecutor(retry_config)
        self.incremental = incremental
        self.model_name = provider.get_model_name()

    def run(
        self,
        questions: list[Question],
        concurrency: int = 1,
        reporter: Optional[Reporter] = None,
    ) -> TestRunSummary:
        total = len(questions)
        items_by_index: dict[int, TestItemResult] = {}
        pending: list[PendingItem[Question]] = []

        for index, question in enumerate(questions, 1):
            output_file = question.answer_file(self.model_name)
            if self.incremental and output_file.exists():
                result = TestItemResult(
                    index=index,
                    question_id=question.id,
                    question_path=question.path,
                    status="skipped",
                    output_file=output_file,
                )
                items_by_index[index] = result
                self._emit(
                    reporter,
                    Event(
                        phase=Phase.TEST,
                        event_type=EventType.SKIP,
                        index=index,
                        total=total,
                        question_id=question.id,
                        output_file=output_file,
                    ),
                )
                continue
            pending.append(PendingItem(index, question))

        def run_one(index: int, question: Question) -> TestItemResult:
            return self._run_one(index, total, question, reporter)

        for result in self.executor.run_pending(pending, concurrency, run_one):
            items_by_index[result.index] = result

        items = [items_by_index[index] for index in sorted(items_by_index)]
        done = sum(1 for item in items if item.status == "done")
        skipped = sum(1 for item in items if item.status == "skipped")
        failed = sum(1 for item in items if item.status == "failed")
        return TestRunSummary(self.model_name, total, done, skipped, failed, items)

    def _run_one(
        self,
        index: int,
        total: int,
        question: Question,
        reporter: Optional[Reporter],
    ) -> TestItemResult:
        started = time.monotonic()
        attempts: Optional[int] = None
        output_file = question.answer_file(self.model_name)
        try:
            self._emit(
                reporter,
                Event(
                    phase=Phase.TEST,
                    event_type=EventType.START,
                    index=index,
                    total=total,
                    question_id=question.id,
                ),
            )
            prompt = question.read_prompt()
            response, attempts = self.executor.request_with_retry(
                lambda: self.provider.chat(prompt),
                phase=Phase.TEST,
                index=index,
                total=total,
                question_id=question.id,
                reporter=reporter,
            )
            output_file = question.write_answer(self.model_name, response)
            elapsed = time.monotonic() - started
            self._emit(
                reporter,
                Event(
                    phase=Phase.TEST,
                    event_type=EventType.DONE,
                    index=index,
                    total=total,
                    question_id=question.id,
                    elapsed_s=elapsed,
                    attempt=attempts,
                ),
            )
            return TestItemResult(
                index=index,
                question_id=question.id,
                question_path=question.path,
                status="done",
                output_file=output_file,
                elapsed_s=elapsed,
                attempts=attempts,
            )
        except Exception as e:
            elapsed = time.monotonic() - started
            if isinstance(e, RetryExhaustedError) and attempts is None:
                attempts = e.attempts
            error = f"{type(e).__name__}: {e}"
            self._emit(
                reporter,
                Event(
                    phase=Phase.TEST,
                    event_type=EventType.FAIL,
                    index=index,
                    total=total,
                    question_id=question.id,
                    elapsed_s=elapsed,
                    attempt=attempts,
                    error=error,
                ),
            )
            return TestItemResult(
                index=index,
                question_id=question.id,
                question_path=question.path,
                status="failed",
                output_file=output_file,
                elapsed_s=elapsed,
                attempts=attempts,
                error=error,
            )

    def _emit(self, reporter: Optional[Reporter], event: Event) -> None:
        if reporter is not None:
            reporter.on_event(event)


class JudgeRunner:
    def __init__(self, provider: BaseProvider, retry_config: RetryConfig, incremental: bool = True):
        self.provider = provider
        self.executor = BatchExecutor(retry_config)
        self.incremental = incremental
        self.judge_name = provider.get_model_name()

    def judge(
        self,
        questions: list[Question],
        target_model: str,
        concurrency: int = 1,
        reporter: Optional[Reporter] = None,
    ) -> JudgeSummary:
        total = len(questions)
        items_by_index: dict[int, JudgeItemResult] = {}
        pending: list[PendingItem[Question]] = []

        for index, question in enumerate(questions, 1):
            answer_file = question.answer_file(target_model)
            output_file = question.judge_file(target_model)
            if not answer_file.exists():
                error = f"缺少测试结果: {answer_file.name}"
                result = JudgeItemResult(
                    index=index,
                    question_id=question.id,
                    question_path=question.path,
                    target_model=target_model,
                    status="no_answer",
                    error=error,
                )
                items_by_index[index] = result
                self._emit(
                    reporter,
                    Event(
                        phase=Phase.JUDGE,
                        event_type=EventType.NO_ANSWER,
                        index=index,
                        total=total,
                        question_id=question.id,
                        error=error,
                    ),
                )
                continue

            if self.incremental and output_file.exists():
                result = JudgeItemResult(
                    index=index,
                    question_id=question.id,
                    question_path=question.path,
                    target_model=target_model,
                    status="skipped",
                    output_file=output_file,
                )
                items_by_index[index] = result
                self._emit(
                    reporter,
                    Event(
                        phase=Phase.JUDGE,
                        event_type=EventType.SKIP,
                        index=index,
                        total=total,
                        question_id=question.id,
                        output_file=output_file,
                    ),
                )
                continue

            pending.append(PendingItem(index, question))

        def judge_one(index: int, question: Question) -> JudgeItemResult:
            return self._judge_one(index, total, question, target_model, reporter)

        for result in self.executor.run_pending(pending, concurrency, judge_one):
            items_by_index[result.index] = result

        items = [items_by_index[index] for index in sorted(items_by_index)]
        done = sum(1 for item in items if item.status == "done")
        skipped = sum(1 for item in items if item.status == "skipped")
        failed = sum(1 for item in items if item.status == "failed")
        no_answer = sum(1 for item in items if item.status == "no_answer")
        scored_items = [
            item for item in items if item.status == "done" and item.total_score is not None
        ]
        avg_score = None
        if scored_items:
            avg_score = sum(item.total_score or 0 for item in scored_items) / len(scored_items)
        return JudgeSummary(
            self.judge_name,
            target_model,
            total,
            done,
            skipped,
            failed,
            no_answer,
            avg_score,
            items,
        )

    def _judge_one(
        self,
        index: int,
        total: int,
        question: Question,
        target_model: str,
        reporter: Optional[Reporter],
    ) -> JudgeItemResult:
        started = time.monotonic()
        attempts: Optional[int] = None
        output_file = question.judge_file(target_model)
        try:
            self._emit(
                reporter,
                Event(
                    phase=Phase.JUDGE,
                    event_type=EventType.START,
                    index=index,
                    total=total,
                    question_id=question.id,
                ),
            )
            meta = question.read_meta()
            indicators = scoring_indicators_from_meta(meta)
            max_score = max_score_from_meta(meta)
            request = build_judge_request(
                question.read_prompt(),
                question.read_reference(),
                question.read_answer(target_model),
                indicators,
                max_score,
            )
            raw, attempts = self.executor.request_with_retry(
                lambda: self.provider.structured(request),
                phase=Phase.JUDGE,
                index=index,
                total=total,
                question_id=question.id,
                reporter=reporter,
            )
            score = normalize_judge_score(raw, max_score, indicators)
            self._write_result(output_file, question.id, target_model, score)
            elapsed = time.monotonic() - started
            self._emit(
                reporter,
                Event(
                    phase=Phase.JUDGE,
                    event_type=EventType.DONE,
                    index=index,
                    total=total,
                    question_id=question.id,
                    elapsed_s=elapsed,
                    attempt=attempts,
                    score=score.total_score,
                    max_score=score.max_score,
                ),
            )
            return JudgeItemResult(
                index=index,
                question_id=question.id,
                question_path=question.path,
                target_model=target_model,
                status="done",
                total_score=score.total_score,
                max_score=score.max_score,
                dimensions=score.dimensions,
                feedback=score.feedback,
                output_file=output_file,
                elapsed_s=elapsed,
                attempts=attempts,
            )
        except Exception as e:
            elapsed = time.monotonic() - started
            if isinstance(e, RetryExhaustedError) and attempts is None:
                attempts = e.attempts
            error = f"{type(e).__name__}: {e}"
            self._emit(
                reporter,
                Event(
                    phase=Phase.JUDGE,
                    event_type=EventType.FAIL,
                    index=index,
                    total=total,
                    question_id=question.id,
                    elapsed_s=elapsed,
                    attempt=attempts,
                    error=error,
                ),
            )
            return JudgeItemResult(
                index=index,
                question_id=question.id,
                question_path=question.path,
                target_model=target_model,
                status="failed",
                elapsed_s=elapsed,
                attempts=attempts,
                error=error,
            )

    def _write_result(
        self,
        output_file: Path,
        question_id: str,
        target_model: str,
        score: Any,
    ) -> None:
        output_file.parent.mkdir(exist_ok=True)
        result = {
            "judge_model": self.judge_name,
            "target_model": target_model,
            "question_id": question_id,
            "judged_at": datetime.now(timezone.utc).isoformat(),
            "total_score": score.total_score,
            "max_score": score.max_score,
            "indicators": score.indicators,
            "dimensions": score.dimensions,
            "feedback": score.feedback,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(result, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _emit(self, reporter: Optional[Reporter], event: Event) -> None:
        if reporter is not None:
            reporter.on_event(event)
