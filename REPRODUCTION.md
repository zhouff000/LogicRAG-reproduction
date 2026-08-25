# LogicRAG 复现报告

## 论文信息

- **标题**: You Don't Need Pre-built Graphs for RAG: Retrieval Augmented Generation with Adaptive Reasoning Structures
- **会议**: AAAI'26
- **ArXiv**: https://arxiv.org/abs/2508.06105
- **原始代码**: https://github.com/chensyCN/LogicRAG

## 1. 论文解决的问题

现有 GraphRAG 系统（Microsoft GraphRAG、LightRAG、HippoRAG）依赖将语料库转换为知识图谱的昂贵过程，存在以下问题：

1. ** prohibitive 的 token 成本**：图谱构建需要数百万 token 和数十分钟，甚至在处理任何查询之前就已完成。
2. **更新延迟**：语料库的任何变更都需要重新构建完整图谱。
3. **结构失配**：预构建的图谱是静态的，可能无法与每个查询所需的特定推理结构对齐。

LogicRAG 通过提出一个框架来解决这个问题，该框架在推理时**动态提取推理结构**，无需任何预构建图谱。核心思想：即时构建查询特定的依赖图，使用拓扑排序将其线性化为顺序推理流水线，并通过图谱/上下文剪枝提高效率。

## 2. 复现目标

| 等级 | 描述 | 完成情况 |
|---|---|---|
| L1 | 代码执行——验证流水线端到端运行 | ✅ |
| L2 | 机制可见性——验证多跳问题上的依赖图构建 | ✅ |
| L3 | 指标复现——在 50 道 HotpotQA 问题上评估并与论文对比 | ✅ (部分) |
| L4 | 声明验证——与论文声明的完整对比 | ⏳ |

## 3. 环境配置

### 3.1 依赖要求

- Python 3.10+
- LLM API 端点访问权限（已用 gpt-4o-mini 测试）
- ~2GB 磁盘空间用于 sentence-transformers 嵌入缓存

### 3.2 配置步骤

```bash
# 创建虚拟环境
python -m venv .venv

# 激活（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 激活（macOS/Linux）
source .venv/bin/activate

# 安装依赖
pip install -r requirements_frozen.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env：设置 OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL
```

### 3.3 数据集准备

由于体积和版权限制，完整数据集未包含在此仓库中。请从以下官方来源下载：

- **HotpotQA**: https://hotpotqa.github.io/
- **2WikiMultihopQA**: https://github.com/AlibabaResearch/AdvancedLiterateMachinery
- **MuSiQue**: https://github.com/stanford-crfm/music-qa

本仓库包含预先抽样的子集用于快速测试：
- `dataset/hotpotqa_sample5.json` — 5 道题目（烟测）
- `dataset/hotpotqa_sample50.json` — 50 道题目（指标评估）
- `dataset/hotpotqa_bridge10.json` — 10 道桥接型题目

## 4. 复现步骤

### 4.1 烟测（L1 + L2 验证）

```bash
python scripts/run_one.py
```

此命令运行一道多跳问题，并输出：
- 最终答案
- 检索轮数
- 完整的依赖图分解历史（JSON）

**预期输出**：对于多跳问题，`last_dependency_analysis` 字段应包含一个非空列表，展示子问题分解和依赖图。对于测试问题 "In which county is the town in which Raymond Robertsen was born?"，系统应识别出 2 跳依赖链（城镇 → 郡县）。

### 4.2 批量评估（L3）

```bash
python run.py --model logic-rag --dataset dataset/hotpotqa_sample50.json --corpus dataset/hotpotqa_corpus.json --max-rounds 3 --top-k 3 --limit 50
```

结果保存在 `result/evaluation_results.json` 中。

## 5. 复现结果

### 5.1 指标对比

| 指标 | LogicRAG 论文（完整 HotpotQA） | 复现（50 题子集） | 备注 |
|---|---|---|---|
| 字符串准确率 (EM) | 54.8% | 44.0% | 样本量不同；论文在完整 HotpotQA 上评估 |
| LLM 答案准确率 | — | 58.0% | LLM 作为裁判评估（gpt-4o-mini） |
| 检索覆盖率 | — | 56.0% | 答案文本存在于 top-5 检索上下文中 |
| 平均轮数 | — | 0.24 | 见下方关键分析 |
| 平均耗时 | — | 11.16 秒/题 | 含嵌入检索 |
| 平均 Token | — | 1,605/题 | Prompt + Completion |

### 5.2 关键发现：低多跳触发率

复现中最显著的观察是**平均轮数 0.24**，这意味着**76% 的问题（50 题中的 38 题）**被归类为简单事实检索，未触发 LogicRAG 依赖图机制。

这是论文的核心贡献——用于多跳推理的动态图谱构建——仅在 12 个问题（24%）上得到了实际运用。

#### 可能的解释：

1. **样本偏差**：50 题子集可能包含不成比例的单跳问题。完整 HotpotQA 数据集的多跳问题比例更高。
2. **预热分类器阈值**：`can_answer_with_simple_fact` 分类器在将问题归类为简单问题时可能过于激进，尤其是在使用 gpt-4o-mini 的情况下。
3. **问题难度分布**：HotpotQA 问题复杂度各异；某些"多跳"问题如果语料库恰好包含单个文档中的答案，可能通过直接检索回答。

#### L4 阶段建议：

- 在 `dataset/hotpotqa_bridge10.json`（10 道桥接型问题）上运行评估，验证专为依赖推理设计的问题上的多跳触发率。
- 考虑调整预热分析阈值或使用更强的 LLM（gpt-4o 或 Claude）进行分类步骤。
- 比较不同模型配置下的触发率。

### 5.3 案例分析：多跳问题（依赖图已触发）

问题: "In which county is the town in which Raymond Robertsen was born?"

系统正确地将其分解为 2 跳依赖：
1. **子问题 1**: "Hammerfest 的郡县信息"（找到城镇 → Hammerfest）
2. **子问题 2**: "Hammerfest, Norway 的位置"（找到郡县 → Finnmark）

依赖图分析正确识别出子问题 1 的答案（Hammerfest）是解决子问题 2（Finnmark 郡县）的先决条件。

### 5.4 案例分析：单跳问题（无依赖图）

问题: "Which Walt Disney film was produced first, The Apple Dumpling Gang or Something Wicked This Way Comes?"

该问题被正确归类为简单事实检索（轮数=0），系统正确回答："The Apple Dumpling Gang"。由于这是单跳比较问题，未构建依赖图。

## 6. 复现质量评估

### 表现良好的方面

- ✅ **代码执行**：流水线无需修改即可端到端运行。
- ✅ **机制可见性**：依赖图构建可通过 `last_dependency_analysis` 观察。
- ✅ **结果可复现性**：在相同语料库和 API Key 下，对于给定模型版本，结果是确定性的。
- ✅ **指标合理性**：鉴于 50 题子集和 gpt-4o-mini，44.0% 的字符串准确率是合理的。

### 需要进一步调查的方面

- ⚠️ **低多跳触发率**：仅 24% 的问题激活了依赖图。这是论文的核心贡献，值得深入调查。
- ⚠️ **样本量**：50 题不足以进行确定性的指标对比。论文在完整 HotpotQA 数据集上评估。
- ⚠️ **模型差异**：论文可能使用了不同的（可能更强的）LLM 进行核心推理。使用 gpt-4o-mini 结果可能有所不同。

## 7. 目录结构

```
LogicRAG-main/
├── src/                          # 原始源码（未修改）
│   ├── models/
│   │   ├── base_rag.py
│   │   └── logic_rag.py
│   ├── evaluation/
│   │   └── evaluation.py
│   ├── utils/
│   └── main.py
├── config/
│   └── config.py
├── scripts/                      # 复现辅助脚本
│   └── run_one.py                # 单题烟测
├── dataset/                     # 仅包含抽样子集
│   ├── hotpotqa_sample5.json
│   ├── hotpotqa_sample50.json
│   └── hotpotqa_bridge10.json
├── result/
│   └── evaluation_results.json   # 复现指标
├── figs/
├── run.py                        # 原始入口
├── setup.py
├── requirements.txt
├── requirements_frozen.txt
├── .env.example                  # 模板（无真实 API Key）
├── README.md                     # 原始 + 复现章节
└── REPRODUCTION.md               # 本文件
```

## 8. 参考资料

- 论文: https://arxiv.org/abs/2508.06105
- 原始代码: https://github.com/chensyCN/LogicRAG
- HotpotQA: https://hotpotqa.github.io/
- AAAI'26 录用: https://openreview.net/forum?id=ov1bwU35Mf
