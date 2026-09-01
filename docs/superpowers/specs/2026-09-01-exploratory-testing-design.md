# Exploratory Testing 设计文档

日期：2026-09-01

状态：已批准设计，待实施计划

本设计取代 `docs/superpowers/specs/2026-09-01-requirement-discovery-design.md` 中针对 URL-only 场景的主流程设计。旧文档保留作为设计演进记录，但后续实现以本文为准。

## 1. 背景

当前 Testing Agent Skills 已经有一条适合“需求已知”的正式测试链路：

```text
Requirement / PRD
  ↓
test-design
  ↓
Test Suite
  ↓
test-orchestrator
  ↓
Browser / API / Log-Trace / Static Inspection
  ↓
Evidence
  ↓
PASS / FAIL / BLOCKED
```

此前为了覆盖“只有运行中的 Web 页面、没有正式需求”的场景，仓库新增了 `requirement-discovery`：

```text
URL
  ↓
requirement-discovery
  ↓
requirements.md
  ↓
test-design
  ↓
test-cases.json
  ↓
执行测试
```

真实页面盲测暴露出两个结构性问题。

第一，`requirements.md` 会把丰富的页面状态、交互轨迹、Before/After 差异和异常信号压缩成一份静态文字文档；随后 `test-design` 又把这份文档再次压缩成 Test Case。关键探索上下文容易在两次转换中丢失。

第二，URL-only 场景没有独立于当前产品实现的正式 Expected。若 Agent 太激进，可能把 Buggy Actual 反向吸收成 Requirement；若 Agent 太谨慎，则关键行为会大量进入 INF / Q，最终被 `test-design` 判成 NEEDS_CLARIFICATION / BLOCKED，隐藏 Bug 仍然无法被有效追踪。

因此 URL-only 场景不再强制经过“需求文档 → 测试用例”的静态流水线，而改成真正的探索式测试闭环。

同时，原 `requirement-discovery` 的职责已经超出“需求发现”，正式改名为：

```text
exploratory-testing
```

目标目录：

```text
skills/exploratory-testing/SKILL.md
```

## 2. 核心决策

Testing Agent 明确分成两种模式。

### 2.1 Requirements-driven Testing

有正式 Requirement / PRD / AC 时，保持现有流程不变：

```text
Requirement / PRD
  ↓
test-design
  ↓
Test Suite
  ↓
test-orchestrator
  ↓
Evidence
  ↓
PASS / FAIL / BLOCKED
```

这一模式存在明确的 Expected，因此适合正式断言、PASS / FAIL 判定和统一执行契约。

### 2.2 URL-only Exploratory Testing

只有 URL、缺少正式需求时，使用 `exploratory-testing`：

```text
URL
 ↓
Initial Observation
 ↓
Application Map
 ↓
Exploration Planner
 ↓
Exploration Missions
 ↓
Execute → Observe → Update Map
   ↑                 ↓
   └──── Plan Next ──┘
            ↓
       Coverage Gate
            ↓
         Findings
            ↓
   exploration-report.md
```

探索完成后，可以按需从探索结果导出候选 `requirements.md`，但 `requirements.md` 不再是 URL-only 测试流程的强制中间输入。

## 3. 设计原则

### 3.1 未知系统使用 Mission，已知 Contract 使用 Test Case

Exploration Mission 的问题是：

> 我还不知道这个功能的精确 Expected，我应该进行什么操作来最大化对产品行为的理解？

Test Case 的问题是：

> 已知 Expected 后，怎样证明 Actual 是否满足 Contract？

因此：

```text
未知系统 → Exploration Mission
已知需求 → Test Case
```

不要用正式 Test Case Schema 约束开放式探索，也不要让探索 Agent 为了满足 Test Case 格式而提前虚构 Expected。

### 3.2 探索与测试是同一个闭环

URL-only 场景不再先“完整发现需求”再“开始测试”。

正确关系是：

```text
Observe
  ↓
Plan
  ↓
Act
  ↓
Observe Delta
  ↓
Update Map
  ↓
Plan Next
```

探索过程中发现新的未知关系或异常后，Planner 可以动态插入新的 Mission。

### 3.3 先规划，再执行

Agent 不应看到控件就自由点击。

初始观察后必须先建立 Feature Inventory 和 Application Map，再生成第一批 Exploration Missions。

### 3.4 有覆盖下限，也有预算上限

`max_interactions`、`max_depth` 只负责防止探索失控，不代表探索已经完成。

正常完成必须通过 Coverage Gate。

### 3.5 不从当前产品现状制造正式 Expected

探索模式允许判断“行为高度异常”，但在缺少正式 Contract 时，不把异常直接伪装成严格 FAIL。

## 4. 参考实现与取舍

本设计吸收两个开源项目中的关键思想，但不复制其完整架构。

### 4.1 从 Autospec 吸收

Autospec 的核心流程是：先扫描页面并获取 Accessibility Snapshot，再由 Planner 生成多个可测试 Spec；每个 Spec 独立执行，并在每个 Browser Action 后重新读取 Accessibility Snapshot。

本设计吸收：

- Plan before Execute；
- 一个页面生成多个目标明确的探索任务；
- happy path / edge case / common interaction 的覆盖思想；
- significant action 后重新观察页面状态。

不吸收：

- 自研 Crawler；
- 独立执行框架；
- Playwright codegen 作为探索主流程。

### 4.2 从 Agentic Test Explorer 吸收

Agentic Test Explorer 显式维护 Action Tape、Explored Paths、Bugs Found 和 step_count，并使用多种 QA Persona；当一个探索区域达到 step limit 时，会要求 Agent 返回基础状态并选择完全不同的区域继续，而不是直接结束整个任务。

本设计吸收：

- 探索覆盖意识；
- 记录已经探索过的 Area / Mission；
- 当前区域饱和后切换区域，不直接 Finish；
- persona 思想压缩成 Normal / Edge / Combination 三种探索视角；
- 可疑行为需要 Confirmation Probe；
- significant interaction 后检查错误、loading、empty state 等健康信号。

不吸收：

- LangGraph Swarm；
- Supervisor / Multi-agent；
- SQLite Checkpointer；
- 跨会话 Semantic / Episodic / Procedural Memory；
- Langmem / Prompt Optimizer；
- 自研 Browser Engine；
- JSONL Action Tape；
- Bug Catalog 服务。

第一版仍保持 Skill-level architecture。

## 5. Skill 重命名与职责变化

### 5.1 名称

旧：

```text
requirement-discovery
```

新：

```text
exploratory-testing
```

目标路径：

```text
skills/exploratory-testing/SKILL.md
```

旧目录 `skills/requirement-discovery/` 在实施时移除，不保留两个语义重叠的 Skill。

### 5.2 新职责

`exploratory-testing` 负责：

- 只有 URL 时理解运行中的 Web App；
- 建立 Feature Inventory；
- 建立和持续更新 Application Map；
- 规划 Exploration Missions；
- 使用 Normal / Edge / Combination 三种视角主动探索；
- 维护轻量 Exploration Ledger；
- 使用隐式 Oracle 识别一致行为、可疑行为和未知区域；
- 对可疑行为执行 Confirmation Probe；
- 根据 Coverage Gate 决定是否允许正常结束；
- 输出 `exploration-report.md`；
- 按需从探索结果导出候选 `requirements.md`。

### 5.3 非职责

`exploratory-testing` 第一版不负责：

- 生成正式 `test-cases.json`；
- 修改 `test-design` Schema；
- 修改 `test-orchestrator` Schema；
- 用产品当前行为构造正式 Expected；
- 将 STRONG_ANOMALY 直接等同正式 FAIL；
- 建立数据库或持久化状态服务；
- 引入 LangGraph；
- 引入 Multi-agent；
- 自研 Browser Crawler；
- 自研 Playwright Browser Engine；
- 新增 JSON Schema；
- 默认生成 regression `.spec.ts`；
- 自动执行明显危险或不可逆业务操作。

## 6. 与现有 Skill 的边界

### `exploratory-testing`

回答：

> 在没有正式需求的情况下，这个运行中的应用有哪些功能、状态关系、未知行为和异常信号？还应该探索什么？

主要输出：`exploration-report.md`。

### `playwright-cli`

继续作为浏览器执行“手”：

- 打开页面；
- Accessibility / Snapshot；
- 元素识别；
- click / fill / select / press / hover / scroll；
- DOM 属性读取；
- Screenshot；
- Network / Trace 等按需证据；
- Browser Session 管理。

`exploratory-testing` 只决定为什么探索、探索什么、下一步是什么、何时切换区域、何时需要确认异常。

### `test-design`

继续只处理已经存在的正式 Requirement / PRD / AC，生成正式 Test Suite。

URL-only 探索不再为了进入 `test-design` 而强制先生成 `requirements.md`。

### `test-orchestrator`

继续服务正式 Test Suite 的 Preflight、Provision、Reflight、Execution、Evidence 和 Report。

第一版 URL-only Exploration 不强行接入 `test-orchestrator`，避免把开放式 Mission 塞进正式 Case Schema。

## 7. URL-only 探索总流程

```text
URL
 │
 ▼
Open with playwright-cli
 │
 ▼
Initial DOM / Accessibility Snapshot
 │
 ├── Vision supplement when useful
 │
 ▼
Feature Inventory
 │
 ▼
Initial Application Map
 │
 ▼
Exploration Planner
 │
 ▼
Mission Queue
 │
 ▼
Execute One Mission
 │
 ▼
Before → Action → After → Delta
 │
 ├── Confirmed relation → Update Map
 ├── Unknown relation   → Add Mission
 └── Suspicious         → Add Confirmation Probe
 │
 ▼
Update Exploration Ledger
 │
 ▼
Coverage Gate
 │
 ├── Gap exists → choose next highest-value Mission
 ├── Area saturated → reset stable state and switch Area
 └── Gate satisfied → Finish
 │
 ▼
exploration-report.md
 │
 └── optional requirements.md
```

## 8. Initial Observation

### 8.1 DOM-first + Vision supplement

继续沿用现有正确方向：

```text
Accessibility / Snapshot > Rendered DOM > Raw HTML
```

DOM / Accessibility 主要识别：

- heading；
- button；
- link；
- textbox；
- checkbox；
- radio；
- combobox；
- tab；
- table；
- list；
- dialog；
- navigation；
- selected / disabled / required；
- 页面可见文字。

Rendered DOM 只在需要确认 `maxlength`、`minlength`、`pattern`、`required`、`disabled` 等直接影响用户行为的属性时按需读取。

Vision 只补充：

- 页面区域和视觉层级；
- 列表 / 详情关系；
- 图表、Canvas、图片；
- Modal / Drawer；
- 颜色和视觉选中态；
- DOM 无法解释的明显视觉差异；
- 明显布局异常。

不要求每个 Action 都调用 Vision。

### 8.2 Feature Inventory

Initial Observation 后先建立功能清单，不立即自由操作。

至少识别：

- Area；
- Control；
- Interaction Type；
- 是否 Stateful；
- 是否 Input / Filter；
- 是否安全；
- 大致优先级。

推荐只使用三档：

```text
High
Medium
Unsafe
```

High-value 的典型特征：

- 用户主要任务；
- 会改变业务数据视图；
- 会改变页面状态；
- 接收用户输入；
- 会触发导航或重要异步行为。

不要为了完整度给 Logo、Footer、Copyright 等静态装饰分配同等探索预算。

## 9. Application Map

Application Map 是 URL-only 模式的核心内部模型，而不是正式 Requirement。

第一版不新增 `application-map.json` 或 Schema。Agent 在当前上下文维护轻量 Map，并在最终报告中输出人类可读摘要。

Map 至少表达：

```text
Areas
Controls
Known transitions
Unknown transitions
Suspicious transitions
```

例如：

```text
Source Filter
  ├── changes → News List
  └── changes → Total Pages

Page Size
  ├── changes → Visible Item Count
  ├── changes → Total Pages
  └── resets  → Current Page

Pagination
  ├── changes → Current Page
  └── changes → News List

Search
  └── ? → Result State
```

`?` 本身就是高价值 Exploration Target。

## 10. Exploration Planner

Planner 不生成完整正式 Test Suite，只维护当前最值得执行的 Mission Queue。

每个 Mission 只需回答：

```text
目标是什么？
为什么值得探索？
准备做什么 Probe？
重点观察哪些状态变化？
```

例如：

```text
Mission: Search-Normal
Goal: 确认查询是否改变资讯结果状态
Probe: 搜索当前页面中真实存在的企业名
Observe: 列表、分页、结果数量、empty state、loading、必要时 network
```

第一批 Mission 来自 Feature Inventory；执行过程中可动态增加 Mission。

Planner 每完成一个 Mission 后重新考虑：

1. Application Map 有什么新关系？
2. 哪些关系仍是 UNKNOWN？
3. 有没有 Suspicious Observation？
4. Coverage Gate 还缺什么？
5. 下一 Mission 哪个信息增益最大？

## 11. 三种 Exploration Lens

不引入多个 Persona Agent，只把 Persona 思想压缩成三个探索视角。

### 11.1 Normal

验证正常用户最自然的主要路径。

例：

```text
Search → 搜索当前列表中确实存在的企业
Filter → All → 某个具体来源
Pagination → Page 1 → Page 2 → Page 1
```

### 11.2 Edge

针对 Input / Filter 选择少量高信息量边界输入，不做无限 Fuzz。

典型：

- 空值；
- 明确不存在的随机值；
- 一个边界长度值；
- 必要时一个特殊字符值。

例如 Search：

```text
__NO_RESULT_9F2A__
```

目的不是穷举，而是判断不同语义输入是否产生合理不同的状态关系。

### 11.3 Combination

把会影响同一业务状态的 Stateful Controls 做代表性组合。

例如：

```text
Source Filter + Search
Page Size + Pagination
Search + Pagination
```

避免笛卡尔积。

组合选择原则：如果 A 和 B 都会改变同一个核心状态（例如列表），则 A + B 值得至少组合一次。

## 12. Mission Execution Loop

每个 Mission 都执行：

```text
Before
  ↓
Action
  ↓
After
  ↓
Delta
  ↓
Interpret
```

Before / After 至少关注与当前 Mission 有关的状态，例如：

- selected value；
- visible item set；
- item count；
- current page；
- total pages；
- URL；
- dialog state；
- empty state；
- loading state；
- error / alert；
- 必要时 network request / response。

### 12.1 Significant Action 后重新 Snapshot

以下操作后默认重新获取页面状态：

- Filter changed；
- Search submitted；
- Pagination changed；
- Tab changed；
- Page Size changed；
- Modal opened；
- Navigation happened；
- Form submitted；
- Refresh happened。

不要一次执行多个关键动作后才统一观察，否则无法建立清晰的 Action → Delta 关系。

## 13. Exploration Ledger

第一版不实现 JSONL Action Tape。

Agent 在上下文中维护轻量 Ledger：

| Area | Mission | Before | Action | Delta | Assessment |
|---|---|---|---|---|---|
| Search | Normal | All / 20 pages | 搜海芯微 | list/pages unchanged | suspicious |
| Search | Edge | All / 20 pages | 搜随机不存在值 | list/pages unchanged | suspicious |
| Source | Normal | All / 20 pages | 选 IT桔子 | → 5 pages | confirmed |

Ledger 的用途：

- 防止重复探索；
- 给 Planner 选择下一 Mission；
- 给 Coverage Gate 判断覆盖；
- 给最终 Report 提供 Reproduction Path 和证据摘要。

不要求单独落盘为中间文件。

## 14. URL-only 的 Implicit Oracles

没有正式 Requirement 时不能凭感觉制造精确 Expected，但可以使用若干隐式 Oracle 判断一致性和异常程度。

### 14.1 UI Semantic Oracle

控件自身表达的语义提供弱到中等强度的预期关系。

例如：

```text
textbox: 标题/企业名
button: 查询
```

至少说明“输入不同查询并提交后，页面应产生与查询语义有关的某种可观察反馈”。

它不能直接证明应该返回精确几条数据。

### 14.2 Metamorphic Relation

这是 URL-only 场景最重要的 Oracle。

不要求知道精确正确值，只比较不同输入之间应该存在的合理关系。

例如：

```text
Query A = 页面真实存在企业名
Query B = 明确不存在的随机字符串
```

若 A 与 B 在列表、分页、结果反馈和相关 Network 行为上长期完全相同，则形成强异常信号。

### 14.3 State Invariant

同一功能内部状态应一致。

例如：

- page indicator = 2 时数据应与 page 1 有合理区别；
- disabled / selected 状态应与当前交互状态一致。

### 14.4 Cross-feature Consistency

组合功能之间应保持一致。

例如来源筛选选择“IT桔子”后，当前列表的来源标签不应大面积与 IT桔子矛盾。

### 14.5 Reversibility

可逆操作恢复后，核心状态应合理恢复。

例如：

```text
All → IT桔子 → All
```

应大体恢复初始列表范围和分页状态。

### 14.6 Health Signals

重大交互后按需检查：

- visible error banner；
- `role=alert`；
- stuck loading / spinner / aria-busy；
- 明显 console error；
- 必要时 Network 4xx / 5xx。

### 14.7 UX Contract

例如无匹配搜索通常应该有空列表或明确反馈，而不是静默保持旧结果。

UX Contract 只能作为弱 Oracle，默认用于 `SUSPECTED_ANOMALY`，除非有更多证据支持。

## 15. Anomaly Detection 与 Confirmation Probe

一次可疑观察不能立刻升级成强异常。

```text
Suspicious Observation
  ↓
Confirmation Probe
  ↓
Re-observe
  ↓
Classify Finding
```

Confirmation Probe 应优先：

- 换一个输入；
- 换一个路径；
- 换一个组合状态；
- 重置到稳定初始状态后重试。

例如搜索第一次没有变化：

```text
Probe 1: 搜真实存在企业名
Probe 2: 搜明确不存在随机字符串
Probe 3: Source Filter + Search
```

若不同语义输入重复产生相同无反馈状态，异常置信度显著提高。

## 16. Finding 分类

URL-only 模式不直接复用正式 Test Suite 的 PASS / FAIL。

### `CONFIRMED_BEHAVIOR`

多次直接 Evidence 支持一个稳定的用户可观察行为或状态关系。

### `STRONG_ANOMALY`

至少满足：

1. 一个 UI Semantic / Metamorphic / State Invariant / Cross-feature 等关系出现明显不一致；
2. 至少执行一次不同输入、路径或组合的 Confirmation Probe；
3. 异常仍可稳定观察。

`STRONG_ANOMALY` 表示高度值得人工确认，不等价于已知 Requirement 下的严格 FAIL。

### `SUSPECTED_ANOMALY`

存在可疑信号，但仍有多个合理业务解释。

### `UNKNOWN`

当前环境、权限、安全限制或页面证据不足以判断。

## 17. Evidence Escalation

普通行为不要一开始就抓全量 Trace / Network / Vision。

按需升级证据：

```text
普通行为
  ↓
DOM / Accessibility

可疑
  ↓
重复 Probe + DOM Delta

仍可疑
  ↓
Screenshot / Network / Console / Trace（按需）
```

目标是提高异常判断质量，同时避免探索成本爆炸。

## 18. Coverage Gate

Coverage Gate 是防止 Agent “随便点几下就结束”的核心。

### 18.1 High-value Area Normal Coverage

每个安全的 High-value Interactive Area 至少完成 1 个 Normal Mission。

### 18.2 Input / Filter Edge Coverage

每个安全的 Input / Filter 至少完成 1 个高信息量 Edge Mission。

### 18.3 Stateful Combination Coverage

如果页面存在至少两个安全 Stateful Controls，则至少完成 2 个有意义的 Combination Missions。

如果整个页面不存在两个可组合的 Stateful Controls，该 Gate 自动视为不适用。

### 18.4 Suspicious Confirmation Coverage

任何 Suspicious Observation 在正常结束前，至少必须执行 1 个不同输入、路径或组合的 Confirmation Probe；若因安全或环境限制不能确认，则明确记录为 UNKNOWN / Coverage Gap。

## 19. 探索预算与区域饱和

第一版不增加额外配置系统，Skill 内给出默认预算：

```text
max_depth = 2
max_interactions = 30
```

这两个值是 Hard Limit，不是完成条件。

### 19.1 当前区域饱和

连续约 3 次安全 Probe 没有得到新的状态关系、未知信息或异常证据时：

```text
Current Area Saturated
  ↓
记录已探索内容
  ↓
恢复稳定状态
  ↓
选择下一个 Coverage Gap 最大的 Area
```

不得把“当前 Area 饱和”解释成整个 Exploration 完成。

### 19.2 真正完成条件

正常完成必须：

```text
Coverage Gate satisfied
AND
没有仍需要安全 Confirmation Probe 的 unresolved suspicious behavior
```

### 19.3 预算耗尽

Hard Limit 先到达但 Coverage Gate 未满足时，运行状态是：

```text
PARTIAL
```

不能伪装成探索完成。

## 20. 运行状态

URL-only Exploration 最终运行状态只有：

### `COMPLETED`

Coverage Gate 满足，且没有仍待安全 Confirmation Probe 的关键异常。

### `PARTIAL`

因探索预算达到上限而结束，但仍存在 Coverage Gap。

### `BLOCKED`

因为页面不可访问、登录、权限、必要环境条件或安全限制导致无法继续关键探索。

## 21. 安全边界

允许自动探索的典型操作：

- Search；
- Filter；
- Tab；
- Pagination；
- Page Size；
- Dropdown；
- Accordion；
- Tooltip / Hover；
- Modal 打开 / 关闭；
- Read-only navigation；
- 同一 Origin 内的普通非破坏性导航。

灰区操作默认只记录入口，不执行：

- Save；
- Create；
- Sync；
- Submit；
- Confirm；
- Send。

默认禁止：

- Delete；
- Payment；
- Publish；
- Password change；
- Account deletion；
- Real transaction；
- Unknown file upload；
- Production task；
- 其他明显不可逆或会影响真实业务数据的行为。

Unsafe Area 不计入必须完成的 Coverage Gate，但必须在 Report 中标注未探索原因。

## 22. SPA、外部链接与深度

### 22.1 SPA

不能只用 URL change 识别状态。

应比较：

- Accessibility / DOM Delta；
- visible text；
- selected / disabled；
- dialog state；
- list / count / pagination；
- 必要时 Network。

### 22.2 External Origin

默认只验证存在外部导航能力和可观察目标，不继续深入第三方站点。

### 22.3 Depth

默认：

```text
Depth 0：输入页面
Depth 1：直接核心状态 / 子页面
Depth 2：核心功能的下一层状态
```

Depth Limit 是预算边界；达到边界的 Area 记录 Coverage Boundary，不继续无限扩散。

## 23. `exploration-report.md` 输出

URL-only 模式的主要正式产物改为：

```text
exploration-report.md
```

推荐结构：

```markdown
# Exploratory Testing Report

## 1. Application Overview

## 2. Application Map

## 3. Confirmed Behaviors

## 4. Strong Anomalies

## 5. Suspected Anomalies

## 6. Unknown / Unsafe Areas

## 7. Exploration Coverage

## 8. Reproduction Paths
```

### 23.1 Application Overview

描述页面目的、主要 Area、关键 Stateful Controls 和核心用户路径。

### 23.2 Application Map

输出最终发现的核心状态关系和未知关系，不要求 JSON。

### 23.3 Confirmed Behaviors

使用 `BEH-*`：

```text
BEH-001
来源筛选会改变资讯范围和总页数。
```

### 23.4 Anomalies

使用 `ANOM-*`，每条至少包含：

- 现象；
- 关键 Probe；
- Before / After 差异；
- 使用的 Oracle；
- Evidence；
- 分类：STRONG_ANOMALY / SUSPECTED_ANOMALY。

### 23.5 Unknown / Unsafe Areas

说明当前无法判断或因安全边界跳过的区域。

### 23.6 Coverage Summary

至少输出：

| Area | Normal | Edge | Combination | Result |
|---|---|---|---|---|
| Search | ✓ | ✓ | ✓ | Strong anomaly |
| Source Filter | ✓ | ✓ | ✓ | Confirmed |
| Pagination | ✓ | N/A | ✓ | Confirmed |

并给出总体运行状态：COMPLETED / PARTIAL / BLOCKED。

### 23.7 Reproduction Paths

对 STRONG_ANOMALY 输出简短可重复路径即可，第一版不强制自动生成 Playwright `.spec.ts`。

## 24. `requirements.md` 的新定位

`requirements.md` 不再是 URL-only Exploration 的强制中间产物，而是探索结束后的可选导出视图。

来源优先使用：

```text
Confirmed Behaviors
+
UI Semantics
+
稳定 State Relations
```

不得直接把 `STRONG_ANOMALY` 当前错误行为写成正式 Requirement。

候选需求仍可分：

- `REQ-*`：稳定、直接 Evidence 支持的候选产品行为；
- `INF-*`：存在较强语义但仍无法确认正式业务规则；
- `Q-*`：仍需产品或业务确认的问题。

如果用户后续人工确认这些候选需求，可以再把正式文档交给 `test-design`。

## 25. Anomaly 到 Regression Test 的生命周期

第一版 `exploratory-testing` 不默认生成正式 Regression Test。

推荐生命周期：

```text
Unknown Web App
  ↓
Exploration
  ↓
ANOM-xxx
  ↓
Human / Requirement confirmation
  ↓
Confirmed Bug / Contract
  ↓
test-design 或 Playwright Test generation
  ↓
Permanent Regression Test
```

这样可以避免在没有正式 Expected 时过早冻结错误假设。

## 26. 对现有仓库的影响

实施时计划：

```text
Remove
skills/requirement-discovery/SKILL.md

Create
skills/exploratory-testing/SKILL.md

Modify
README.md
USAGE.md
docs/architecture.md
docs/implementation-plan.md
```

旧 `requirement-discovery` 设计与实施文档保留作为历史记录，但新文档和 README 应明确新架构已经取代旧 URL-only 流程。

### 不修改

- `skills/test-design/schema.json`；
- `skills/test-design/scripts/*`；
- `skills/test-orchestrator/*` 公共 Schema；
- `playwright-cli`；
- Secret / Preflight / Provision / Reflight 逻辑。

## 27. 第一版明确不做的事情

为避免过度工程化，第一版明确不加入：

```text
Multi-agent
LangGraph
Supervisor
SQLite / DB
Persistent Memory
Application Map JSON Schema
Exploration Ledger JSON
Custom Browser Engine
Custom Crawler
Custom Selector Engine
Action Tape JSONL
Automatic Playwright reproduction codegen
Complex scoring formula
全排列组合测试
全站无限 Crawl
```

所有核心控制先通过 `SKILL.md` 的探索协议实现。

如果实测证明单纯 Skill 协议无法稳定维持 Coverage Gate，再考虑加入一个极小的临时 exploration state 文件；在有证据之前不预先实现。

## 28. 第一版成功标准

第一版 implementation 可以用真实隐藏 Bug 页面做盲测，但这些属于后续实施验证，不要求在设计阶段执行。

设计上的成功标准是：

1. URL-only 模式不再强制经过 `requirements.md → test-cases.json` 才开始测试；
2. Agent 先建立 Feature Inventory 和 Application Map；
3. 每个 High-value Area 至少执行 Normal Mission；
4. 每个安全 Input / Filter 至少执行 Edge Mission；
5. 存在多个 Stateful Controls 时执行代表 Combination Mission；
6. 可疑行为至少进行一次 Confirmation Probe，而不是立刻 Q / BLOCKED；
7. 当前 Area 饱和后切换 Area，不直接结束；
8. Coverage Gate 未满足但预算耗尽时明确输出 PARTIAL；
9. `exploration-report.md` 能直观看出探索了哪些 Area、哪些 Lens、哪些组合，以及发现了什么异常；
10. `requirements.md` 只作为探索后可选导出，不再成为 URL-only 测试的强制事实源。

## 29. 最终架构

```text
                         User Input
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        Formal Requirement             URL only
                │                       │
                ▼                       ▼
          test-design            exploratory-testing
                │                       │
                ▼                       ▼
          Test Suite              Application Map
                │                       │
                ▼                       ▼
       test-orchestrator         Exploration Missions
                │                       │
                │                Plan ↔ Explore
                │                       │
                ▼                       ▼
             Evidence                Findings
                │                       │
                ▼                       ├─ exploration-report.md
      PASS / FAIL / BLOCKED            └─ optional requirements.md
```

核心边界：

```text
exploratory-testing
→ unknown app / unknown expected

test-design + test-orchestrator
→ known requirements / known expected
```

## 30. 设计结论

`requirement-discovery` 更名为 `exploratory-testing`，不是单纯的命名调整，而是职责升级：

旧模式：

```text
URL
↓
猜候选需求
↓
requirements.md
↓
静态 Test Case
↓
执行
```

新模式：

```text
URL
↓
建立 Application Map
↓
规划 Mission
↓
主动探索 Normal / Edge / Combination
↓
Before / Action / After / Delta
↓
用 Implicit Oracle 发现异常
↓
Confirmation Probe
↓
Coverage Gate
↓
Exploration Report
↓
按需导出 Candidate Requirements
```

第一版仍然只增加 Skill-level 的流程约束，继续复用现有 `playwright-cli`，不引入新的运行时框架。