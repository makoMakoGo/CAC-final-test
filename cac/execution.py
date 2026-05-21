"""Shared benchmark execution Module."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from .config import RetryConfig
from .reporting import Event, EventType, Phase, Reporter


T = TypeVar("T")
R = TypeVar("R")


class RetryExhaustedError(RuntimeError):
    def __init__(self, max_attempts: int, last_error: BaseException):
        self.attempts = max_attempts
        super().__init__(f"请求失败 ({max_attempts} 次尝试): {last_error}")


@dataclass(frozen=True)
class PendingItem(Generic[T]):
    index: int
    item: T


class BatchExecutor:
    def __init__(self, retry_config: RetryConfig):
        self.retry_config = retry_config

    def run_pending(
        self,
        pending: list[PendingItem[T]],
        concurrency: int,
        run_one: Callable[[int, T], R],
    ) -> list[R]:
        if concurrency < 1:
            raise ValueError("concurrency 必须 >= 1")
        if concurrency == 1:
            return [run_one(item.index, item.item) for item in pending]

        results: dict[int, R] = {}
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(run_one, item.index, item.item) for item in pending]
            for future in as_completed(futures):
                result = future.result()
                index = getattr(result, "index")
                if not isinstance(index, int):
                    raise TypeError("批量执行结果必须包含 int 类型的 index 字段")
                results[index] = result
        return [results[item.index] for item in sorted(pending, key=lambda item: item.index)]

    def request_with_retry(
        self,
        request: Callable[[], R],
        *,
        phase: Phase,
        index: int,
        total: int,
        question_id: str,
        reporter: Optional[Reporter],
        sleep: Callable[[float], None] = time.sleep,
    ) -> tuple[R, int]:
        max_attempts = self.retry_config.max_attempts
        delay = self.retry_config.delay
        last_error: Optional[BaseException] = None

        for attempt in range(1, max_attempts + 1):
            try:
                return request(), attempt
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    if reporter is not None:
                        reporter.on_event(
                            Event(
                                phase=phase,
                                event_type=EventType.RETRY,
                                index=index,
                                total=total,
                                question_id=question_id,
                                attempt=attempt,
                                max_attempts=max_attempts,
                                error=f"{type(e).__name__}: {e}",
                            )
                        )
                    sleep(delay)

        raise RetryExhaustedError(
            max_attempts=max_attempts, last_error=last_error or RuntimeError("unknown error")
        )
