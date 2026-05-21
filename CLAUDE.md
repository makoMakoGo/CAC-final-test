# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Validate question format
python scripts/validate_questions.py

# Run benchmark tests
python cac.py --scope math              # Test all math questions
python cac.py --scope math/base-test    # Test math base level
python cac.py --scope logic --dry-run   # Preview questions to test

# Enable git hooks
 git config core.hooksPath .githooks
```

## Environment Setup

```bash
pip install -r cac/requirements.txt
cp cac/config.yaml.example config.yaml
# Edit config.yaml with your API key
```

## Project Architecture

LLM/Agent benchmark suite with CLI-driven test runner.

### Evaluation System (`cac/`)

- `cac.py`: root CLI entry point
- `cac/cli.py`: CLI Adapter with rich help, scope/range/force options
- `cac/config.py`: config loading with `${ENV_VAR}` support
- `cac/scope.py`: resolves `math/base-test` to question paths
- `cac/question.py`: owns question source/result artifact paths
- `cac/execution.py`: shared retry and concurrent dispatch Module
- `cac/runner.py`: executes test and judge phases
- `cac/judgement.py`: judge prompt, schema, and normalized score parsing
- `cac/reporting.py`: event-driven output (PlainReporter/RichReporter)
- `cac/providers/`: LLM provider Adapters (OpenAI, Anthropic, Gemini, Custom, Doubao)
- `cac/indicators.py`: canonical scoring indicator catalog

### Configuration

```yaml
# config.yaml
test-model:
  name: gpt-4o
  provider: openai              # gemini | anthropic | openai | custom | doubao
  api_key: ${OPENAI_API_KEY}
  base_url: https://api.openai.com/v1
  model_id: gpt-4o
  params:
    temperature: 0.3
    max_tokens: 8192

judge-model:
  name: gpt-4o-judge
  provider: openai
  api_key: ${OPENAI_API_KEY}
  base_url: https://api.openai.com/v1
  model_id: gpt-4o
```

### Provider Types

| Provider | URL Handling | Use Case |
|----------|-------------|----------|
| `openai` | Auto-append `/chat/completions` | OpenAI/DeepSeek/Qwen/Doubao-compatible endpoints |
| `doubao` | Auto-append `/chat/completions` | Volcengine Ark OpenAI-compatible endpoints |
| `anthropic` | `/v1/messages` | Claude |
| `gemini` | `/v1beta/models/{model}:generateContent` | Google Gemini |
| `custom` | Use URL as-is | Ollama Cloud or fully specified endpoints |

### Question Bank Structure

```
{Category}/
└── {Difficulty}/               # base-test, advanced-test, final-test, final-test+
    └── NNN-problem-name/
        ├── meta.yaml           # ID, difficulty, scoring indicators
        ├── prompt.md           # Exact prompt for tested model
        ├── reference.md        # Answer/criteria for judge model
        ├── README.md           # Human documentation
        └── test-results/       # Output: {model-name}.md and {model-name}.judge.yaml
```

### Scoring Indicator Categories

| Category | Indicators |
|----------|------------|
| code | `ans_correct`, `code_quality`, `efficiency`, `robustness` |
| theory | `completeness`, `accuracy`, `clarity`, `depth`, `logic` |
| design | `ans_correct`, `example_quality`, `completeness`, `practicality` |
| easy | `correct_max_1` |
| rule | `format_and_constraints` |

## Creating Questions

Use the `question-creator` skill (`.claude/skills/question-creator/`) for guided question creation.

**ID format**: `{category}-{difficulty}-{number}` (e.g., `math-base-001`, `code-final-003`)
- Categories: `math`, `code`, `logic`, `comp`, `hallucination`
- Difficulties: `base`, `advanced`, `final`, `final+`

**Required files**: `meta.yaml`, `prompt.md`, `reference.md`

## Adding LLM Providers

1. Create a file in `cac/providers/` inheriting `BaseProvider` or `ToolCapableProvider`.
2. Implement `chat(prompt: str) -> str`.
3. For structured judge output, implement `chat_with_tool(prompt: str, tool_schema: dict) -> dict` by inheriting `ToolCapableProvider`.
4. Register the Adapter in `cac/providers/__init__.py` `PROVIDER_REGISTRY`.

## Judge Mode Structured Output

Judge mode asks the provider Interface for structured output. Tool-capable Adapters use provider-native tool/function calling internally; text-only Adapters receive a JSON-only prompt and parse text at the provider seam.

## Commit Messages

Follow Conventional Commits with Chinese + emoji: `[emoji][type](scope): description`

Common types: `✨ feat`, `🐛 fix`, `📝 docs`, `♻️ refactor`, `✅ test`, `🧹 chore`, `🛠️ ci`
