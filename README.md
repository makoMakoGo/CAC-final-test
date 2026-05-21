# CAC-final-test

[![Run in Smithery](https://smithery.ai/badge/skills/t-auto)](https://smithery.ai/skills?ns=t-auto&utm_source=github&utm_medium=badge)

Benchmark for Evaluating the Performance of Natural Language Models and Agents / 自然语言模型 & Agent 性能评测基准

## 📖 项目简介 (Project Overview)

本项目旨在构建一个全面且高难度的 AI 能力评测体系，主要包含：

- **全方位题库**：涵盖大模型与 Agent 的核心能力测试
- **自动化评测**：使用 `cac/` 统一 CLI 工具实现自动化测试与评分
- **标准化格式**：题目采用 `meta.yaml` + `prompt.md` + `reference.md` 结构
- **开发工具**：Git hooks 验证 + AI 辅助创建题目（见 [AGENTS.md](./AGENTS.md)）

## 🚀 快速开始 (Quick Start)

```bash
pip install -r cac/requirements.txt
cp cac/config.yaml.example config.yaml  # 编辑填入 API key

# 运行测试
python cac.py                       # 交互式菜单
python cac.py --scope math          # 测试数理题库
python cac.py --mode all -j 4       # 测试+评分，4并发
```

## 💡 设计理念 (Design Philosophy)

- **自动化 (Automation)**
  面对日新月异的 AI 模型，我们的目标是实现**一键生成评分结果**，以快速响应模型的迭代更新。

- **经济实惠的高难度测评 (Economic & Challenging)**
  针对 GPT-5-pro 等昂贵的顶尖模型，我们采用**"少而精"**的策略。通过极高难度的题目进行手动或半自动测试，而基础测试默认满分。这既保证了评测的区分度，又将人工评分的工作量控制在可接受范围内。

## 🧩 LLM 能力基准测试 (LLM Benchmarks)

### 1. 数理能力基准测试
- **基础题目**：分层次的数学/物理题目，用于测定 AI 的基础数理能力（主要区分本地部署的小模型）。
- **Final-test 题目**：专门用于评测顶级模型的极限推理能力。

### 2. 代码能力基准测试
- **后端开发**：测试 AI 在 C / C++ / Python / Java / Golang / Rust 等语言中的编程能力。
- **前端审美**：测试 AI 的前端设计与实现能力（**注：此项仅展示效果，不进行评分**）。

### 3. 自然语言与逻辑能力基准测试
- **逻辑推理**：包含日常对话理解、逻辑陷阱（如"弱智吧"题目）及悬疑推理问题。
- **语言风格**：考察语言表达能力与文风（**注：此项仅展示，不评分**）。

## 📊 难度分级 (Difficulty Levels)

| 级别              | 描述                                                                                 | 目标模型                              |
| :---------------- | :----------------------------------------------------------------------------------- | :------------------------------------ |
| **Base-test**     | 较为简单，生活中常用的问题。                                                         | 3B~30B 本地/边缘计算小模型            |
| **Advanced-test** | 具有一定难度，8B/30B/70B 模型几乎无法完成。                                          | 500B+ (DeepSeek, GPT-4, Gemini 等)    |
| **Final-test**    | 极高难度，以 Google AI Studio 中 Gemini-1.5-pro 的最大思考上限为基准（需多次尝试）。 | 顶级模型 (SOTA)                       |
| **Final-test+**   | 当前所有顶级 AI 均无法解决，但人类可以解决的问题。                                   | 未来模型 (Gemini-Deepthink, GPT-5 等) |

## 🧪 其他测试 (Other Tests)

### LLM 日用体验测试
- **幻觉控制与指令遵循**：测评模型是否存在幻觉、是否能明确表达不确定性，以及是否能遵循约束指令（目录：`幻觉控制与指令遵循测试/`）。

### Agent 相关测试
- 由于此部分暂时无法自动化，当前阶段我们将优先专注于 LLM 基准能力的测试编写。

## ❓ 常见问题 (Q&A)

> **Q：为什么没有 LLM 自带文科能力测试或者知识储量基准测试？**
>
> **A**：随着 Agent 技术与联网搜索能力的普及，如果您有解决此类问题的需求，与其向一个"知识更丰富"的模型提问，不如使用可以灵活上网搜索的 Agent 来解决此类问题。

> **Q：题库泄露导致模型刷分怎么办？**
>
> **A**：那真是我们的荣幸。不过，本项目仍然会把题目分为**公开题库**和**私有题库**两部分。如果一个模型在公开题库和私有题库的表现差距过大，我们会明确指出其"刷分"现象。

## 🤝 投稿需求 (Contribution)

我们需要您提供：
1. **题目与标准答案**：清晰的问题描述及对应的正确解答。
2. **考察点说明**：说明该题目主要考察 LLM 的哪一项能力。
3. **裁判标准**：为了满足自动化评测需求，我们需要一个裁判 LLM 能对照标准答案判断回答问题的模型的对错。
   - ❌ **不可**是纯粹的证明题。
   - ❌ **不可**是没有标准答案的发散性问题（难以判断"对错"）。

### 📁 题目文件结构

每个题目目录需要包含以下文件：

```
NNN-problem-name/
├── README.md       # 给人看的完整文档
├── meta.yaml       # 元数据（id、评分指标等）
├── prompt.md       # 发给被测模型的 prompt
├── reference.md    # 标准答案/评判依据
└── test-results/   # 测试结果
```

详细格式规范请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md#题目编写规范)。

---

### 📝 题目示例 (Example)

**Question (Final-test 难度，Gemini 正确作答率约 30%)**

> Whether the local deformation functor of Sheaf $O(-1) \oplus O(1)$ in $\mathbb{P}^1_k$ is miniversal? How about the crude deformation functor $F_1$?

#### Analysis

> **1. Problem Statement**
>
> Let $k$ be an algebraically closed field. We study the local deformations of the vector bundle $F_0 = \mathcal{O}_{\mathbb{P}^1}(-1) \oplus \mathcal{O}_{\mathbb{P}^1}(1)$ on the projective line $X_0 = \mathbb{P}^1_k$.
> ...
>
> *(See full analysis in `数理能力基准测试题库/final-test/001-sheaf-deformation-functor/README.md`)*
>
> **Conclusion**
> The local deformation functor $F$ ... is **miniversal**.
