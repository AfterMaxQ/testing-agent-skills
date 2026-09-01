# Testing Agent Skills 当前实现说明

## 1. 项目契约

本包现在有两种独立入口。

### 1.1 URL-only / unknown expected

```text
运行中的网页 / URL
  → exploratory-testing
  → Feature Inventory
  → Application Map
  → Exploration Missions
  → Plan ↔ Explore
  → Coverage Gate
  → exploration-report.md
  → optional requirements.md
```

URL-only 不再强制经过 `requirements.md → test-design → test-cases.json` 才开始测试。

### 1.2 Formal Requirement / known expected

```text
Requirement / PRD / AC
  → test-design
  → Test Suite
  → Test Context
  → Secret Resolution
  → Preflight
  → Provision
  → Runtime Context
  → Reflight
  → Browser / API / Log-Trace / Static Inspection
  → Evidence
  → Report
  → Cleanup
```

需求级正式测试仍使用四个可核对公共 JSON 对象：

| 对象 | 作用 | 主要文件 |
|---|---|---|
| Test Suite | 需求追溯、Case、步骤、断言、证据入口和运行条件 | `skills/test-design/schema.json` |
| Test Context | 当前环境能力、受信任 Provisioner 和 Runtime Secret 元数据 | `skills/test-orchestrator/context.schema.json` |
| Readiness | Preflight 对每个 Case 的就绪状态和缺口 | `skills/test-orchestrator/readiness.schema.json` |
| Report | Assertion、Evidence、状态、Provision 和 Cleanup 的最终记录 | `skills/test-orchestrator/schema.json` |

版本保持：

```text
Test Suite   1.4
Test Context 1.2
Readiness    1.0
Report       1.3
```

`exploratory-testing` 输出 Markdown，不新增第五个公共 JSON 契约。

## 2. Exploratory Testing

`skills/exploratory-testing/SKILL.md` 用于只有运行中的 Web 页面、缺少正式 Requirement / PRD / AC 的情况。

### 2.1 当前职责

- DOM / Accessibility 为主要观察源，Vision 按需补充；
- Initial Observation 后先建立 Feature Inventory；
- 持续维护 Application Map；
- 根据未知关系和 Coverage Gap 动态规划 Exploration Missions；
- 使用 Normal / Edge / Combination 三种探索视角；
- 每个重大交互执行 `Before → Action → After → Delta`；
- 在当前上下文维护轻量 Exploration Ledger；
- 使用 Implicit Oracles 发现一致行为、异常信号和未知区域；
- 可疑行为执行 Confirmation Probe，而不是立刻写成 Q / BLOCKED；
- 使用 Coverage Gate 控制是否允许正常结束；
- 输出 `exploration-report.md`；
- 按需在探索后额外导出 `requirements.md`。

### 2.2 Browser 复用

`exploratory-testing` 不实现自己的 Browser Engine。

浏览器能力全部复用 `playwright-cli`：

```text
Open / Snapshot
DOM / Accessibility
click / fill / select / press / hover / scroll
Screenshot
Network
Trace
Browser Session
```

### 2.3 Application Map

Application Map 记录状态关系，而不只是元素：

```text
Filter --changes--> List
Page Size --changes--> Visible Count
Pagination --changes--> Current Page / List
Search --?--> Result State
```

关系未知时优先生成新的 Mission。

不新增 Application Map JSON Schema，也不要求落盘。

### 2.4 Mission 与 Lens

Exploration Mission 是动态探索目标，不是正式 Test Case。

同一个 Agent 使用：

```text
Normal
Edge
Combination
```

Normal 覆盖主要自然用户路径；Edge 使用高信息量安全边界；Combination 只组合影响相同或相关业务状态的 Stateful Controls。

不做控件全排列。

### 2.5 Implicit Oracles

URL-only 场景没有正式 Expected，当前实现使用：

- UI Semantic Oracle；
- Metamorphic Relation；
- State Invariant；
- Cross-feature Consistency；
- Reversibility；
- Health Signals；
- UX Contract（弱 Oracle）。

其中 Metamorphic Relation 用于比较不同语义输入之间是否存在合理状态差异，而不是猜精确正确值。

### 2.6 Finding

URL-only Finding：

```text
CONFIRMED_BEHAVIOR
STRONG_ANOMALY
SUSPECTED_ANOMALY
UNKNOWN
```

`STRONG_ANOMALY` 需要明显的语义 / 状态 / metamorphic 不一致，并至少通过一次不同输入、路径或组合的安全 Confirmation Probe 复现。

它不是正式 Requirement 下的 `FAIL`。

### 2.7 Evidence Escalation

```text
普通行为
→ DOM / Accessibility

可疑
→ Repeat Probe + DOM Delta

仍可疑
→ Screenshot / Network / Console / Trace（按需）
```

默认不对所有 Mission 全量抓取昂贵证据。

### 2.8 Coverage Gate

Hard Limit：

```text
max_depth = 2
max_interactions = 30
```

它们只是预算上限。

正常完成至少要求：

1. 每个安全 High-value Area 至少 1 个 Normal Mission；
2. 每个安全 Input / Filter 至少 1 个 Edge Mission；
3. 存在至少 2 个安全 Stateful Controls 时至少 2 个有意义的 Combination Mission；
4. 每个 Suspicious Observation 至少 1 个安全 Confirmation Probe，或明确记录无法确认原因。

当前 Area 连续约 3 次安全 Probe 没有新关系、未知信息或异常证据时，只标记 Area Saturated，恢复稳定状态并切换到未覆盖 Area。

URL-only 运行状态：

```text
COMPLETED
PARTIAL
BLOCKED
```

Coverage Gate 未满足而预算耗尽时必须是 `PARTIAL`。

### 2.9 输出

主要输出：

```text
exploration-report.md
```

内容至少包括：

```text
Application Overview
Application Map
Confirmed Behaviors
Strong Anomalies
Suspected Anomalies
Unknown / Unsafe Areas
Exploration Coverage
Reproduction Paths
```

可选 `requirements.md` 只在探索后生成。当前异常表现不能直接成为正式 Requirement。

### 2.10 第一版明确不实现

```text
Multi-agent
LangGraph
Supervisor
SQLite / DB
Persistent Memory
Application Map JSON Schema
Exploration Ledger JSON / JSONL
Custom Browser Engine
Custom Crawler
Custom Selector Engine
Action Tape
Automatic reproduction codegen
复杂评分公式
全排列组合测试
```

所有核心探索控制先由 `SKILL.md` 协议实现。

## 3. Test Suite

`test-design` 继续只描述已经存在的正式需求语义，不承担 URL-only 开放式探索。

每条 Case 包含：

- `source_refs`；
- `objective`、`steps`、`assertions`；
- `execution_channels`；
- `execution_requirements`；
- `open_question_refs`。

无法唯一确定 Expected 时使用 `NEEDS_CLARIFICATION`，不自行替业务补规则。

Suite 校验：

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
```

Test Suite Schema 保持 `1.4`。

## 4. Test Context 与 Provisioner

Test Context 继续描述当前执行环境真实能力：

- `available`；
- `provisioners`；
- `runtime_secrets`。

Provisioner 支持：

```text
command
playwright
api
manual
```

只有 verification 成功后，`provides` 才写入 Runtime Context。

Context 校验：

```bash
python skills/test-orchestrator/scripts/validate_context.py test-context.json
```

Test Context Schema 保持 `1.2`。

## 5. Secret Resolver

Secret 定义文件：

```text
skills/test-orchestrator/secret.schema.json
```

来源顺序：

```text
Runtime Secret Store
→ Local Secret Store
→ 当前进程环境变量
→ 已声明外部 Provider 状态
→ 显式 Manual Input
```

Secret 值只存在于 Resolver 和它启动的子进程环境，不进入 Runtime Context、Readiness、Report、Markdown 或截图。

## 6. Preflight、Provision 和 Reflight

Preflight 检查：

```text
execution_requirements ⊆ Test Context.available
```

正式 Case 状态：

```text
READY
PROVISIONABLE
BLOCKED
NEEDS_CLARIFICATION
```

Provision 失败记录 `provision_failure` blocker，不判产品 FAIL。

Readiness Schema 保持 `1.0`。

## 7. 四类正式执行通道

| 通道 | 直接 Evidence |
|---|---|
| Browser | DOM、URL、Network、Trace、Screenshot、Storage State |
| API | Request / Response、状态码、关键字段、SSE 事件 |
| Log-Trace | 与本次 Case / Request / Trace ID 可关联的日志和 Trace |
| Static Inspection | 需求明确指定的文件、配置和实际值 |

Browser 具体执行继续由 `playwright-cli` 完成。

## 8. Report

正式 Report 使用：

```text
skills/test-orchestrator/schema.json
```

正式 Assertion 状态：

```text
PASS
FAIL
BLOCKED
NOT_EXECUTED
```

PASS / FAIL 必须有与 `observe_via` 匹配的 Evidence；BLOCKED 必须有结构化 blocker；Report 不进行根因推测，也不保存 Secret 值。

Report Schema 保持 `1.3`。

## 9. 运行边界

- `exploratory-testing` 用于 unknown app / unknown expected；
- `test-design + test-orchestrator` 用于 known requirement / known expected；
- URL-only 不强制生成 `requirements.md` 或 `test-cases.json` 才开始测试；
- `STRONG_ANOMALY` 不等同正式 `FAIL`；
- Candidate Requirements 必须经过人工或正式需求确认后，才适合作为正式 Expected 来源；
- Test Suite、Test Context、Secret、Readiness、Report 公共 Schema 均不因此次改造发生变化；
- `.testing-agent/secrets.env`、`.testing-agent/runtime/` 和本地配置继续不进入 Git 追踪范围。
