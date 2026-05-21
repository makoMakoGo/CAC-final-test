"""Command line Adapter for CAC benchmark runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from .config import load_config
from .providers import create_provider
from .reporting import Phase, create_reporter, is_tty
from .runner import JudgeRunner, JudgeSummary, TestRunSummary, TestRunner
from .scope import ScopeResolver


def print_rich_help() -> None:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console(emoji=False)
    console.print()
    console.print(
        Panel(
            "[bold cyan]CAC Benchmark[/] [dim]Test Runner[/]\n[dim]LLM/Agent Capability Assessment CLI[/]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
            padding=(0, 2),
        )
    )
    console.print("\n[bold]Usage:[/]")
    console.print("  python -m cac [OPTIONS] --scope <SCOPE>", style="green")

    args_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2), show_edge=False)
    args_table.add_column("Arg", style="cyan bold", width=20)
    args_table.add_column("Desc")
    args_table.add_row(
        "-s, --scope", "Scope: math, code, logic, comp, hallucination or math/base-test"
    )
    console.print("\n[bold]Required:[/]")
    console.print(args_table)

    opts_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2), show_edge=False)
    opts_table.add_column("Arg", style="cyan bold", width=20)
    opts_table.add_column("Desc")
    opts_table.add_row("-m, --mode", "Mode: test (default), judge, all")
    opts_table.add_row("-c, --config", "Config path (default: config.yaml)")
    opts_table.add_row("-r, --range", "Range: 001-005 or 003")
    opts_table.add_row("-t, --target", "Target model for judge mode")
    opts_table.add_row("-j, --concurrency", "Concurrency (default: 1)")
    opts_table.add_row("-f, --force", "Force retry (ignore existing results)")
    opts_table.add_row("--dry-run", "Preview only")
    opts_table.add_row("--json", "Output JSON to stdout")
    opts_table.add_row("--profile-output", "Write cProfile stats to file")
    opts_table.add_row("-h, --help", "Show this message")
    console.print("\n[bold]Options:[/]")
    console.print(opts_table)
    console.print()


def make_json_base(args: Any, config: Any) -> dict[str, Any]:
    judge_model = None
    if getattr(config, "judge_model", None) is not None:
        judge_model = {
            "name": config.judge_model.name,
            "provider": config.judge_model.provider,
        }
    return {
        "ok": True,
        "mode": args.mode,
        "scope": args.scope,
        "range": args.range,
        "concurrency": args.concurrency,
        "incremental": not args.force,
        "test_model": {
            "name": config.test_model.name,
            "provider": config.test_model.provider,
        },
        "judge_model": judge_model,
        "error": None,
        "dry_run": bool(getattr(args, "dry_run", False)),
        "total": 0,
        "items": [],
        "test": None,
        "judge": None,
    }


def _make_stub_config() -> SimpleNamespace:
    return SimpleNamespace(
        test_model=SimpleNamespace(name=None, provider=None),
        judge_model=None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CAC Benchmark Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument("--mode", "-m", choices=["test", "judge", "all"], default="test")
    parser.add_argument("--scope", "-s", required=True)
    parser.add_argument("--target", "-t")
    parser.add_argument("--concurrency", "-j", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--range", "-r")
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile-output")
    return parser


def run_once(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        if is_tty():
            print_rich_help()
        else:
            print(__doc__)
        return 0

    if not argv:
        build_parser().print_help(sys.stdout)
        return 0

    args = build_parser().parse_args(argv)
    if args.concurrency < 1:
        error = "--concurrency/-j 必须 >= 1"
        if args.json:
            result = make_json_base(args, _make_stub_config())
            result["ok"] = False
            result["error"] = error
            print(json.dumps(result, ensure_ascii=False))
            return 1
        print(f"错误: {error}", file=sys.stderr)
        return 1

    log_stream = sys.stderr if args.json else sys.stdout
    reporter = create_reporter(stream=log_stream, use_rich=not args.json)

    def log(message: str = "") -> None:
        print(message, file=log_stream)

    def emit_json(payload: dict[str, Any]) -> None:
        print(json.dumps(payload, ensure_ascii=False))

    def json_error(error: str, cfg: Any = None) -> int:
        result = make_json_base(args, cfg or _make_stub_config())
        result["ok"] = False
        result["error"] = error
        emit_json(result)
        return 1

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        error = f"配置文件不存在: {args.config}"
        return json_error(error) if args.json else _plain_error(log, error)
    except ValueError as e:
        error = f"配置无效: {e}"
        return json_error(error) if args.json else _plain_error(log, error)

    log(f"test-model: {config.test_model.name} ({config.test_model.provider})")
    if config.judge_model is not None:
        log(f"judge-model: {config.judge_model.name} ({config.judge_model.provider})")

    resolver = ScopeResolver(config.question_banks)
    try:
        questions = resolver.resolve(args.scope, args.range)
    except ValueError as e:
        return json_error(str(e), cfg=config) if args.json else _plain_error(log, str(e))

    if not questions:
        if args.json:
            result = make_json_base(args, config)
            emit_json(result)
            return 0
        log("未找到匹配的题目")
        return 0

    log(f"找到 {len(questions)} 道题目")
    repo_root = resolver.base_dir.parent

    if args.dry_run:
        if args.json:
            result = make_json_base(args, config)
            result["dry_run"] = True
            result["total"] = len(questions)
            result["items"] = [{"id": q.id, "path": _rel(q.path, repo_root)} for q in questions]
            emit_json(result)
            return 0
        log("\n将测试以下题目:")
        for question in questions:
            log(f"  - {_rel(question.path, repo_root)}")
        return 0

    if args.mode in ("judge", "all") and config.judge_model is None:
        error = "judge/all 模式需要配置 judge-model"
        return json_error(error, cfg=config) if args.json else _plain_error(log, error)

    target_model = args.target or config.test_model.name
    test_summary: Optional[TestRunSummary] = None
    judge_summary: Optional[JudgeSummary] = None

    if args.mode in ("test", "all"):
        provider = create_provider(config.test_model)
        runner = TestRunner(provider, config.retry, incremental=not args.force)
        _safe_reporter_call(
            reporter, log, "on_phase_start", Phase.TEST, len(questions), config.test_model.name
        )
        test_summary = runner.run(questions, concurrency=args.concurrency, reporter=reporter)
        _safe_reporter_call(
            reporter,
            log,
            "on_phase_end",
            Phase.TEST,
            test_summary.done,
            test_summary.skipped,
            test_summary.failed,
        )

    if args.mode in ("judge", "all"):
        if config.judge_model is None:
            return json_error("judge/all 模式需要配置 judge-model", cfg=config)
        judge_provider = create_provider(config.judge_model)
        judge_runner = JudgeRunner(judge_provider, config.retry, incremental=not args.force)
        _safe_reporter_call(
            reporter, log, "on_phase_start", Phase.JUDGE, len(questions), target_model
        )
        judge_summary = judge_runner.judge(
            questions, target_model=target_model, concurrency=args.concurrency, reporter=reporter
        )
        _safe_reporter_call(
            reporter,
            log,
            "on_phase_end",
            Phase.JUDGE,
            judge_summary.done,
            judge_summary.skipped,
            judge_summary.failed,
            judge_summary.no_answer,
            judge_summary.avg_score,
        )

    if args.json:
        emit_json(_json_result(args, config, questions, repo_root, test_summary, judge_summary))

    failed = 0
    if test_summary:
        failed += test_summary.failed
    if judge_summary:
        failed += judge_summary.failed + judge_summary.no_answer
    return 0 if failed == 0 else 1


def _plain_error(log: Any, error: str) -> int:
    log(f"错误: {error}")
    return 1


def _safe_reporter_call(reporter: Any, log: Any, method: str, *args: Any) -> None:
    fn = getattr(reporter, method, None)
    if fn is None:
        return
    try:
        fn(*args)
    except Exception as exc:
        log(f"reporter.{method} 异常: {exc}")


def _rel(path: Optional[Path], root: Path) -> Optional[str]:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _json_result(
    args: Any,
    config: Any,
    questions: Any,
    repo_root: Path,
    test_summary: Optional[TestRunSummary],
    judge_summary: Optional[JudgeSummary],
) -> dict[str, Any]:
    result = make_json_base(args, config)
    result["total"] = len(questions)
    if test_summary:
        result["ok"] = result["ok"] and test_summary.failed == 0
        result["test"] = {
            "model": config.test_model.name,
            "total": test_summary.total,
            "done": test_summary.done,
            "skipped": test_summary.skipped,
            "failed": test_summary.failed,
            "items": [
                {
                    "index": item.index,
                    "id": item.question_id,
                    "path": _rel(item.question_path, repo_root),
                    "status": item.status,
                    "output_file": _rel(item.output_file, repo_root),
                    "elapsed_s": item.elapsed_s,
                    "attempts": item.attempts,
                    "error": item.error,
                }
                for item in test_summary.items
            ],
        }
    if judge_summary:
        result["ok"] = result["ok"] and judge_summary.failed == 0 and judge_summary.no_answer == 0
        result["judge"] = {
            "judge_model": judge_summary.judge_name,
            "target_model": judge_summary.target_model,
            "total": judge_summary.total,
            "done": judge_summary.done,
            "skipped": judge_summary.skipped,
            "failed": judge_summary.failed,
            "no_answer": judge_summary.no_answer,
            "avg_score": judge_summary.avg_score,
            "items": [
                {
                    "index": item.index,
                    "id": item.question_id,
                    "path": _rel(item.question_path, repo_root),
                    "status": item.status,
                    "score": item.total_score,
                    "max_score": item.max_score,
                    "output_file": _rel(item.output_file, repo_root),
                    "elapsed_s": item.elapsed_s,
                    "attempts": item.attempts,
                    "error": item.error,
                }
                for item in judge_summary.items
            ],
        }
    return result


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        if is_tty():
            from rich.console import Console

            from .interactive import InteractiveMenu

            console = Console(emoji=False)
            menu = InteractiveMenu(console=console)
            while True:
                try:
                    result = menu.run()
                    if result is None:
                        return 0
                    run_once(result.to_argv())
                    console.print("\n[dim]按 Enter 返回主菜单...[/]")
                    try:
                        input()
                    except (KeyboardInterrupt, EOFError):
                        return 0
                except KeyboardInterrupt:
                    return 0
        print_rich_help()
        return 0

    try:
        profile_output = _profile_output_from_argv(argv)
        if profile_output is not None:
            return _profiled_run_once(argv, profile_output)
        return run_once(argv)
    except KeyboardInterrupt:
        return 130


def _profile_output_from_argv(argv: list[str]) -> Optional[Path]:
    for index, arg in enumerate(argv):
        if arg == "--profile-output" and index + 1 < len(argv):
            return Path(argv[index + 1])
        if arg.startswith("--profile-output="):
            return Path(arg.split("=", 1)[1])
    return None


def _profiled_run_once(argv: list[str], output_path: Path) -> int:
    import cProfile

    profiler = cProfile.Profile()
    profiler.enable()
    try:
        return run_once(argv)
    finally:
        profiler.disable()
        profiler.dump_stats(output_path)
