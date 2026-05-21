# AGENTS.md

## Build & Test

```bash
# 安装依赖
pip install -r cac/requirements.txt

# 验证题目格式
python scripts/validate_questions.py

# 运行测试
python cac.py --scope math              # 测试数理题库
python cac.py --scope math/base-test    # 测试基础题
python cac.py --scope math --range 001-005  # 指定范围
python cac.py --mode all --scope math -j 4  # 测试+评分，4并发
python cac.py --scope logic --dry-run   # 预览题目
```

## Architecture Overview

CLI 驱动的 LLM 评测系统。`cac.py` 为入口，`cac/` 是统一评测 Module，支持交互式菜单和命令行模式。`cac/scope.py` 解析测试范围，`cac/question.py` 集中管理题目文件与结果文件，`cac/execution.py` 集中管理重试与并发执行，`cac/runner.py` 执行测试与评分，`cac/reporting.py` 输出结果（Rich/Plain）。`cac/providers/` 封装 OpenAI/Anthropic/Gemini/Custom/Doubao LLM Adapter。题库按 `{类别}/{难度}/{NNN-题目名}/` 组织，每题包含 `meta.yaml`、`prompt.md`、`reference.md`，结果输出到 `test-results/`。

## Security

- API Key 通过 `config.yaml` 配置，支持 `${ENV_VAR}` 环境变量引用
- `config.yaml` 已加入 `.gitignore`，禁止提交
- 敏感文件：`config.yaml`、`.env`、`*credentials*`
- 无远程端点暴露，纯本地 CLI 工具

## Git Workflows

- 主分支：`main`
- 开发分支：`main-fish`
- Commit 格式：`[emoji] [type]: [描述]`
  - 类型：`feat|fix|docs|style|refactor|perf|test|build|ci|chore|deps`
  - 示例：`🎨 style: Panel全宽显示统一边框对齐`
- Pre-commit Hook：验证 commit message 格式和题目格式
- 启用 hooks：`git config core.hooksPath .githooks`

## Conventions & Patterns

```
CAC-final-test/
├── cac/                    # 统一评测系统
│   ├── cli.py              # CLI Adapter
│   ├── config.py           # 配置加载
│   ├── scope.py            # Scope 解析
│   ├── question.py         # 题目 artifact Module
│   ├── execution.py        # 重试/并发执行 Module
│   ├── runner.py           # 测试与评分执行
│   ├── reporting.py        # 输出报告
│   ├── interactive.py      # 交互菜单
│   ├── data/               # 题库与评分指标配置
│   └── providers/          # LLM Adapter
├── 数理能力基准测试题库/    # 题库
├── 代码能力基准测试题库/
├── 自然语言与逻辑能力基准测试题库/
├── 幻觉控制与指令遵循测试/
└── scripts/                # 工具脚本
```

- 代码风格：Python 3.10+，UTF-8 编码
- 命名：snake_case（变量/函数），PascalCase（类）
- 题目 ID：`{category}-{difficulty}-{number}`（如 `math-base-001`）
- 输出文件：`test-results/{model-name}.md`、`{model-name}.judge.yaml`
