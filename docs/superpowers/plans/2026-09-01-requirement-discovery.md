# Requirement Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Testing Agent Skills 前增加独立 `requirement-discovery` Skill，让 Agent 能从运行中的 Web 页面基于 DOM / Accessibility、Vision 补充和少量安全交互生成普通 Markdown `requirements.md`，再由现有 `test-design` 继续处理。

**Architecture:** 新能力只作为现有链路的前置入口，不修改 Test Suite Schema、Test Context、Orchestrator 或 Browser 执行器。`requirement-discovery` 复用现有 `playwright-cli` 完成页面操作，自身只定义探索策略、事实归纳、REQ / INF / Q 分类和 Markdown 输出规则。

**Tech Stack:** Markdown Skill 文件、现有 Microsoft Playwright CLI Skill、现有仓库文档；不新增 Python/Node 依赖，不新增 JSON Schema 或执行服务。

**Spec:** `docs/superpowers/specs/2026-09-01-requirement-discovery-design.md`

## Global Constraints

- 第一版只改仓库，不把真实页面验收、DOM-only / Vision-only Benchmark 或人工验收作为实施前置条件。
- 新增能力必须保持独立 Skill：`skills/requirement-discovery/SKILL.md`。
- Browser 能力必须复用 `skills/playwright-cli/`，不新增 Browser Crawler、Selector Engine、截图工具或 DOM Parser。
- 输出只使用普通 Markdown `requirements.md`，不新增 JSON 中间态、Schema 或 Validator。
- `requirement-discovery` 不生成 Test Case、Locator、Playwright Test，也不修改 Expected。
- 页面观察采用 DOM / Accessibility 为主，Vision 仅补充 DOM 难表达的信息。
- 所有确定需求必须有直接页面证据；不能证明的内容必须降级为 `INF-*` 或 `Q-*`。
- 默认不执行删除、支付、发布、发送、密码修改、账号删除、真实交易、未知上传、生产任务等明显高风险或不可逆操作。
- `test-design`、`test-orchestrator` 的 Schema 和脚本保持不变。
- 实施完成后只做仓库一致性检查，不运行真实业务页面验收。

---

## File Structure

本次实施只创建或修改以下文件：

- Create: `skills/requirement-discovery/SKILL.md` — 新 Skill 的完整行为契约。
- Modify: `README.md` — 在项目概览、架构、模块职责、目录中加入可选的 Requirement Discovery 入口。
- Modify: `USAGE.md` — 增加“只有网页、没有需求文档”时的独立使用方式，并把“三个 Skill”更新为“四个 Skill”。
- Modify: `docs/architecture.md` — 把 `requirement-discovery` 加到总体架构入口，但不改变现有测试执行数据流。
- Modify: `docs/implementation-plan.md` — 更新“当前实现说明”，增加 Requirement Discovery 的职责和与现有 Test Suite 流程的边界。

明确不创建：

- `skills/requirement-discovery/schema.json`
- `skills/requirement-discovery/scripts/*`
- `facts.json`
- `discovery-report.json`
- Browser Crawler / Runner / Database / Config 文件

---

### Task 1: 新增 `requirement-discovery` Skill

**Files:**
- Create: `skills/requirement-discovery/SKILL.md`
- Reference: `skills/playwright-cli/SKILL.md`
- Reference: `skills/test-design/SKILL.md`
- Reference: `docs/superpowers/specs/2026-09-01-requirement-discovery-design.md`

**Interfaces:**
- Consumes: 一个已经运行、Agent 可访问的 Web 页面 URL，以及现有 `playwright-cli` Skill。
- Produces: 普通 Markdown `requirements.md`。
- Does not produce: `test-cases.json`、Locator、Playwright Test、JSON 中间态。

- [ ] **Step 1: 先检查目标 Skill 尚不存在**

Run:

```bash
test ! -e skills/requirement-discovery/SKILL.md
```

Expected: exit code `0`。

- [ ] **Step 2: 创建 Skill frontmatter 和职责边界**

`skills/requirement-discovery/SKILL.md` 开头固定使用：

```markdown
---
name: requirement-discovery
description: Use when 只有已经运行的 Web 页面、缺少正式需求文档，需要从页面可观察行为中反向提取候选需求并输出 Markdown 需求文档时。
---

# 页面需求发现

## 目标

从当前运行中的 Web 页面提取可观察功能、约束和状态行为，生成普通 Markdown `requirements.md`，供人工阅读、修改，或继续交给 `test-design` 生成 Test Suite。

REQUIRED SUB-SKILL: `playwright-cli`

本 Skill 只负责“从页面发现候选需求”，不负责生成 Test Case、Locator、Playwright Test，也不执行 `test-orchestrator`。
```

- [ ] **Step 3: 写入 DOM-first + Vision fallback 观察规则**

必须明确写入以下规则：

```text
页面观察优先级：
Accessibility / Snapshot > Rendered DOM > Raw HTML

DOM / Accessibility 主要用于：
heading、button、link、textbox、checkbox、radio、combobox、tab、table、list、dialog、navigation、可见文字、selected/disabled/required 等状态。

只有需要确认 maxlength、minlength、required、disabled、pattern 等用户可观察约束时，才针对目标元素读取 DOM 属性。

Vision 只补充：
页面区域与视觉层级、列表/详情关系、图表、Canvas、图片、Modal/Drawer、颜色/选中态、DOM 无法解释的视觉变化。

不要让 Vision 重复枚举 DOM 已能准确识别的按钮、输入框和文本。
```

- [ ] **Step 4: 写入 Evidence → Fact → Requirement 原则和分类规则**

Skill 中必须明确：

```text
Evidence
  ↓
Fact
  ↓
REQ / INF / Q
```

并定义：

```text
REQ-*：有直接页面证据支持的确定候选需求。
INF-*：页面有较强迹象，但无法证明一定属于正式产品要求。
Q-*：仅凭当前页面无法确认的规则或约束。
```

每条 `REQ-*` 必须有“页面证据”，Evidence 来源只需简单标注 `DOM`、`Interaction`、`Vision`。

同时写入以下反例：

```text
当前页面恰好显示 10 条数据
≠
“每页必须显示 10 条”

POST /api/v1/news
≠
“产品必须使用 POST /api/v1/news”
```

`<input maxlength="20">` 可以支持“用户输入上限为 20”这类用户可观察候选需求。

- [ ] **Step 5: 写入安全探索策略**

允许自动探索：

```text
Tab 切换
Accordion 展开/收起
分页
代表列表项详情
非破坏性搜索/筛选
Dropdown 展开
Modal 打开/关闭
Tooltip/Hover
同一应用内普通导航
```

默认不自动执行：

```text
删除
支付
发布
发送消息
修改密码
注销或删除账号
真实交易
上传未知文件
生产任务
其他明显不可逆或影响真实业务数据的操作
```

`保存`、`提交`、`确认`、`创建`、`发送`、`同步` 等灰区操作默认只记录入口，不执行；只有明确确认环境安全且操作可逆时才允许执行。

- [ ] **Step 6: 写入页面探索流程和停止规则**

固定流程：

```text
1. 使用 playwright-cli 打开目标页面
2. 获取 Initial Snapshot
3. 做一次初始视觉补充
4. 在内部形成 Facts
5. 按交互类型选择代表行为
6. 每次交互按 Before → Action → After → Delta 比较
7. 只有必要时再次调用 Vision
8. 满足停止条件后生成 requirements.md
```

默认探索边界：

```text
max_depth = 2
max_interactions = 20
no_new_fact_limit = 3
```

停止条件任一成立即可：

```text
主要安全交互类型已经各探索至少一个代表
连续 3 次安全交互没有发现新的功能事实
达到 depth 2
达到 20 次交互
```

同构元素只探索代表项；外部 Origin 只记录跳转能力，不继续深入；SPA 状态变化不能只依赖 URL，需比较 Snapshot/DOM/可见文字/selected/dialog 等变化。

- [ ] **Step 7: 写入 Markdown 输出格式**

Skill 中给出以下固定输出骨架：

```markdown
# <页面或功能名称>需求

> 本文档根据当前运行中的产品页面反向提取，不等同于正式产品需求。

## 页面概述

## 功能需求

### REQ-001 <标题>

<需求描述>

**页面证据**

- DOM：直接观察到的结构或文字
- Interaction：安全交互前后的明确变化
- Vision：仅在视觉证据确有必要时写入

**可信度：高**

## 推断需求

### INF-001 <标题>

**推断**

<推断内容>

**依据**

- <页面依据>

**为什么不是确定需求**

<无法直接证明的原因>

**可信度：中**

## 待确认项

### Q-001 <标题>

<当前页面无法确认的规则>
```

并明确：内部 Facts 不要求落盘；`requirements.md` 是该 Skill 的最终产物。

- [ ] **Step 8: 写入明确禁止事项**

Skill 末尾至少包含：

```text
不从页面现状反推正式业务真理
不把模糊视觉解释直接升级成高可信需求
不从内部 API、class 名、框架实现细节制造业务需求
不生成 test-cases.json
不生成 Locator 或 Playwright Test
不进行根因分析
不执行明显危险或不可逆操作
不为了覆盖率遍历所有同构元素
不无限追踪外部链接或深层页面
```

- [ ] **Step 9: 做仓库级文本契约检查**

Run:

```bash
test -f skills/requirement-discovery/SKILL.md

grep -q '^name: requirement-discovery$' skills/requirement-discovery/SKILL.md
grep -q 'REQUIRED SUB-SKILL: `playwright-cli`' skills/requirement-discovery/SKILL.md
grep -q 'DOM-first' skills/requirement-discovery/SKILL.md
grep -q 'REQ-' skills/requirement-discovery/SKILL.md
grep -q 'INF-' skills/requirement-discovery/SKILL.md
grep -q 'Q-' skills/requirement-discovery/SKILL.md
grep -q 'max_depth = 2' skills/requirement-discovery/SKILL.md
grep -q 'max_interactions = 20' skills/requirement-discovery/SKILL.md
```

Expected: 全部 exit code `0`。

- [ ] **Step 10: Commit**

```bash
git add skills/requirement-discovery/SKILL.md
git commit -m "feat: add requirement discovery skill"
```

---

### Task 2: 更新 README 和总体架构说明

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`

**Interfaces:**
- Consumes: Task 1 的 `skills/requirement-discovery/SKILL.md`。
- Produces: 对外项目架构说明，明确存在“正式 PRD”与“只有网页”两种入口。

- [ ] **Step 1: 更新 README 开头定位**

把 README 的项目定位从“输入只包括需求文档”扩展为：

```text
既支持 PRD / 验收标准 / 业务规则 / 接口契约直接进入 test-design，
也支持只有运行中的 Web 页面时先通过 requirement-discovery 生成候选 requirements.md。
```

保持原有“输出为可追溯 Test Suite、就绪检查和统一测试报告”的描述不变。

- [ ] **Step 2: 更新 README 架构图**

架构图增加独立前置入口：

```text
运行中的网页
     │
     ▼
requirement-discovery
     │ requirements.md
     └──────────────┐
                    ▼
Requirement / PRD → test-design
                    │
                    ▼
              Test Suite
                    │
                    ▼
            test-orchestrator
```

不要把 `requirement-discovery` 放进 `test-orchestrator` 内部。

- [ ] **Step 3: 更新 README 模块职责表**

新增一行：

```markdown
| `requirement-discovery` | 从运行中的网页基于 DOM / Accessibility、Vision 补充和安全交互提取候选需求，输出 `requirements.md` |
```

并保留现有 `test-design`、`test-orchestrator`、`playwright-cli` 三行职责不变。

- [ ] **Step 4: 更新 README 数据流和目录树**

在数据流前增加可选入口：

```text
网页 → requirement-discovery → requirements.md
                             ↓
                        test-design
```

目录树增加：

```text
skills/
├── requirement-discovery/
│   └── SKILL.md
├── test-design/
├── test-orchestrator/
└── playwright-cli/
```

同时在 `docs/superpowers/` 下列出 `specs/` 和 `plans/` 即可，不需要展开每份文件。

- [ ] **Step 5: 更新 `docs/architecture.md` 的总体链路**

把开头总体链路改为两个入口汇合：

```text
运行中的网页 → requirement-discovery → requirements.md ┐
                                                     ├→ test-design
Requirement / PRD ───────────────────────────────────┘
                                                          ↓
                                             Test Suite + execution_requirements
                                                          ↓
                                             现有测试执行链路保持不变
```

新增一个简短的 `Requirement Discovery` 小节，说明：

```text
它只负责从现有页面提取候选需求；
浏览器操作复用 playwright-cli；
输出 requirements.md；
不属于 Test Suite、Context、Readiness、Report JSON 公共契约的一部分。
```

- [ ] **Step 6: 做文档一致性检查**

Run:

```bash
grep -q 'requirement-discovery' README.md
grep -q 'requirements.md' README.md
grep -q 'requirement-discovery' docs/architecture.md
grep -q 'playwright-cli' docs/architecture.md
```

Expected: 全部 exit code `0`。

- [ ] **Step 7: Commit**

```bash
git add README.md docs/architecture.md
git commit -m "docs: document requirement discovery architecture"
```

---

### Task 3: 更新 USAGE 的用户工作流

**Files:**
- Modify: `USAGE.md`

**Interfaces:**
- Consumes: Task 1 的 Skill 行为和 Task 2 的项目架构。
- Produces: 用户可直接复制的 Requirement Discovery 使用方式。

- [ ] **Step 1: 把“三个 Skill”更新为“四个 Skill”**

Skill 职责表新增：

```markdown
| `requirement-discovery` | 从运行中的网页提取候选需求并输出 `requirements.md` | 不生成 Test Case，不决定正式产品需求 |
```

其余三项职责不改变。

- [ ] **Step 2: 更新 Agent 加载说明**

Skill 目录列表改为：

```text
skills/requirement-discovery/
skills/test-design/
skills/test-orchestrator/
skills/playwright-cli/
```

说明：

```text
只有网页、没有需求文档时，先读取 requirement-discovery + playwright-cli；
已有正式需求时，可以直接从 test-design 开始；
requirement-discovery 不要求每次测试都执行。
```

- [ ] **Step 3: 在 Test Suite 步骤之前增加“可选：从网页发现需求”章节**

加入可直接复制的推荐指令：

```text
请先读取并遵守：
- skills/requirement-discovery/SKILL.md
- skills/playwright-cli/SKILL.md

目标页面：<运行中的页面 URL>
输出文件：requirements.md

要求：
1. DOM / Accessibility 为主要事实源；
2. Vision 只补充 DOM 难表达的信息；
3. 只进行安全、非破坏性的代表交互；
4. 确定需求使用 REQ-*，必须附页面证据；
5. 无法直接证明的内容写入 INF-* 或 Q-*；
6. 不生成 Test Case，不执行测试；
7. 最终只输出普通 Markdown requirements.md。
```

- [ ] **Step 4: 增加最小 `requirements.md` 示例**

示例必须同时出现三类内容：

```markdown
## 功能需求
### REQ-001 用户可以切换快讯分类
**页面证据**
- DOM：存在多个分类 Tab
- Interaction：切换后列表内容发生变化
**可信度：高**

## 推断需求
### INF-001 当前分类应有可区分的选中状态
**依据**
- DOM：Tab 存在 selected 状态
- Vision：当前分类具有视觉高亮
**为什么不是确定需求**
当前页面能证明现状，但无法证明它一定是正式验收要求。
**可信度：中**

## 待确认项
### Q-001 快讯默认排序规则
当前页面无法确认排序依据。
```

- [ ] **Step 5: 明确与 `test-design` 的衔接**

写清：

```text
requirement-discovery 到 requirements.md 即结束。
如果后续要测试，再把经人工确认或直接接受的 requirements.md 交给 test-design。
```

同时继续保留现有重要原则：

```text
正式需求和 Test Suite Expected 是测试验收基准；
页面实际行为不能在测试执行阶段反向修改 Expected。
```

- [ ] **Step 6: 做文档文本检查**

Run:

```bash
grep -q 'requirement-discovery' USAGE.md
grep -q 'REQ-001' USAGE.md
grep -q 'INF-001' USAGE.md
grep -q 'Q-001' USAGE.md
grep -q 'requirements.md' USAGE.md
```

Expected: 全部 exit code `0`。

- [ ] **Step 7: Commit**

```bash
git add USAGE.md
git commit -m "docs: add requirement discovery usage"
```

---

### Task 4: 更新当前实现说明并做仓库一致性收尾

**Files:**
- Modify: `docs/implementation-plan.md`
- Inspect only: `skills/test-design/schema.json`
- Inspect only: `skills/test-orchestrator/*.schema.json`

**Interfaces:**
- Consumes: Task 1-3 的最终仓库状态。
- Produces: 与仓库当前实现一致的实现说明；不新增运行时能力。

- [ ] **Step 1: 更新当前实现说明的顶层数据流**

在现有固定测试执行流之前增加可选前置入口：

```text
运行中的网页
  → requirement-discovery
  → requirements.md
  → test-design
```

同时保留：

```text
已有 Requirement / PRD
  → test-design
```

两种入口在 `test-design` 汇合。

- [ ] **Step 2: 增加 `Requirement Discovery` 小节**

说明当前实现事实：

```text
- `skills/requirement-discovery/SKILL.md` 是独立 Skill；
- 输出普通 Markdown requirements.md；
- Browser 操作复用 playwright-cli；
- 不新增 JSON Schema；
- 不改变 Test Suite 1.4、Test Context 1.2、Readiness 1.0、Report 1.3；
- 不修改 test-orchestrator 的 Preflight / Provision / Report 逻辑。
```

- [ ] **Step 3: 确认没有误改公共 JSON 契约**

Run:

```bash
git diff --name-only HEAD~3..HEAD | grep -E 'skills/(test-design/schema.json|test-orchestrator/.*schema.json)' && exit 1 || true
```

Expected: 不输出任何 Schema 路径，exit code `0`。

如果实施过程中提交数量不同，则改用当前 feature 工作起点 SHA 与 HEAD 比较；判断标准仍是本次 Requirement Discovery 不改任何 Schema。

- [ ] **Step 4: 运行最终仓库一致性检查**

Run:

```bash
test -f skills/requirement-discovery/SKILL.md

grep -q 'requirement-discovery' README.md
grep -q 'requirement-discovery' USAGE.md
grep -q 'requirement-discovery' docs/architecture.md
grep -q 'requirement-discovery' docs/implementation-plan.md

grep -q 'REQUIRED SUB-SKILL: `playwright-cli`' skills/requirement-discovery/SKILL.md

git diff --check
```

Expected: 全部 exit code `0`，`git diff --check` 无输出。

- [ ] **Step 5: 确认没有引入过度设计文件**

Run:

```bash
test ! -e skills/requirement-discovery/schema.json
test ! -d skills/requirement-discovery/scripts
test ! -e facts.json
test ! -e discovery-report.json
```

Expected: 全部 exit code `0`。

- [ ] **Step 6: 不执行真实页面验收**

本次实施到仓库一致性检查结束为止。明确不在这一阶段运行：

```text
真实业务页面 Requirement Discovery
DOM-only / Vision-only / Hybrid Benchmark
人工需求准确率评审
真实页面危险操作验证
完整 Test Suite / Orchestrator 验收
```

这些在后续单独验收阶段进行，不作为本次仓库改动的阻塞条件。

- [ ] **Step 7: Commit**

```bash
git add docs/implementation-plan.md
git commit -m "docs: update current implementation for requirement discovery"
```

---

## Final Repository State

实施完成后的核心目录应为：

```text
testing-agent-skills/
├── README.md
├── USAGE.md
├── docs/
│   ├── architecture.md
│   ├── implementation-plan.md
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-09-01-requirement-discovery-design.md
│       └── plans/
│           └── 2026-09-01-requirement-discovery.md
└── skills/
    ├── requirement-discovery/
    │   └── SKILL.md
    ├── test-design/
    ├── test-orchestrator/
    └── playwright-cli/
```

最终运行边界保持：

```text
只有网页
  ↓
requirement-discovery
  ↓
requirements.md
  ↓
（可选人工修改）
  ↓
test-design

已有正式需求
  ↓
test-design

两条路径从 test-design 开始继续复用现有测试执行链路。
```

## Self-Review Checklist

实施前后都按以下条件检查：

- [ ] Spec 中的独立 Skill、DOM-first、Vision fallback、安全交互、REQ/INF/Q、停止规则和 Markdown 输出均在 Task 1 覆盖。
- [ ] README、USAGE、Architecture、Current Implementation 四处不会继续把仓库描述成“只有三个 Skill”。
- [ ] 没有任务修改 Test Suite / Context / Readiness / Report Schema。
- [ ] 没有任务新增 Browser Crawler、Runner、数据库、JSON 中间态或 Validator。
- [ ] 没有真实页面验收步骤作为当前实施前置条件。
- [ ] 所有实施文件和提交边界都可以独立审查和回滚。
