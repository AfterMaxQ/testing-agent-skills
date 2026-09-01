# Testing Agent Skills 架构

## 1. 总体架构

Testing Agent Skills 明确分成两种模式。

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

正式需求模式和 URL-only 模式不在 `test-design` 强制汇合。

- 已有 Requirement / PRD / AC：进入正式 Test Suite 流程；
- 只有 URL、没有明确 Expected：进入 `exploratory-testing`；
- URL-only 探索结束后，如果人工确认并沉淀出正式需求，才可以再进入 `test-design`。

## 2. Exploratory Testing

`skills/exploratory-testing/SKILL.md` 用于 URL-only、unknown-expected 场景。

它回答：

> 在没有正式需求的情况下，这个运行中的应用有哪些功能、状态关系、未知行为和异常信号？下一步应该探索什么？

核心流程：

```text
URL
↓
Initial Observation
↓
Feature Inventory
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

`requirements.md` 只是探索后的可选导出，不是 URL-only 测试的强制中间合同。

### 2.1 Browser 分工

`exploratory-testing` 负责探索策略，`playwright-cli` 负责浏览器执行。

```text
exploratory-testing
→ 为什么探索
→ 探索什么
→ 哪个 Area 还没覆盖
→ 是否需要 Confirmation Probe
→ 什么时候允许结束

playwright-cli
→ Open / Snapshot
→ click / fill / select / press / hover / scroll
→ DOM / Accessibility
→ Screenshot / Network / Trace
→ Browser Session
```

页面观察优先级：

```text
Accessibility / Snapshot > Rendered DOM > Raw HTML
```

Vision 只补充布局、视觉层级、图表 / Canvas / 图片、Modal / Drawer、视觉选中态和 DOM 难解释的变化。

### 2.2 Feature Inventory 与 Application Map

Initial Observation 后先建立 Feature Inventory，不立即自由点击。

每个主要 Area 至少识别：

```text
Control / Interaction Surface
Interaction Type
Stateful?
Input / Filter?
Safety
Priority
Known Effect
Unknown Relation
```

Application Map 关注状态关系，例如：

```text
Source Filter --changes--> News List
Source Filter --changes--> Total Pages
Page Size --changes--> Visible Item Count
Search --?--> Result State
```

未知关系会成为后续高优先级 Exploration Mission。

### 2.3 Exploration Mission

未知系统使用动态 Mission，而不是一开始生成正式 Test Case。

Mission 关注：

```text
Goal
Why informative
Target Area / Control
Probe / Action
Observed state relation
```

探索视角只有三个，不创建多 Agent：

```text
Normal
Edge
Combination
```

Combination 只选择有业务状态依赖的代表组合，禁止笛卡尔积穷举。

### 2.4 执行闭环

每个重大交互固定：

```text
Before → Action → After → Delta → Interpret
```

每次重大交互后重新读取相关 DOM / Accessibility 状态，再决定下一 Mission。

内部维护轻量 Exploration Ledger：

```text
Area | Mission | Action | Delta | Result
```

Ledger 只用于去重、规划、Coverage 和最终 Reproduction Path，不要求落盘 JSON / JSONL。

### 2.5 Implicit Oracles

URL-only 没有正式 Expected，因此不能凭感觉制造精确断言。

主要 Oracle：

- UI Semantic Oracle；
- Metamorphic Relation；
- State Invariant；
- Cross-feature Consistency；
- Reversibility；
- Health Signals；
- UX Contract（弱 Oracle）。

其中 Metamorphic Relation 是 unknown-expected 场景的核心：通过比较语义明显不同的安全输入之间是否产生合理不同的状态，而不是要求预先知道精确正确结果。

### 2.6 Anomaly 与 Confirmation Probe

一次可疑观察不能直接升级成强异常：

```text
Suspicious Observation
→ Confirmation Probe
→ Re-observe
→ Finding
```

Confirmation Probe 优先换输入、路径、组合或恢复稳定状态后重试。

Finding 分类：

- `CONFIRMED_BEHAVIOR`；
- `STRONG_ANOMALY`；
- `SUSPECTED_ANOMALY`；
- `UNKNOWN`。

`STRONG_ANOMALY` 不是正式 Requirement 下的 `FAIL`。

### 2.7 Coverage Gate

默认 Hard Limit：

```text
max_depth = 2
max_interactions = 30
```

Hard Limit 只是预算上限。

正常完成要求：

1. 每个安全 High-value Area 至少 1 个 Normal Mission；
2. 每个安全 Input / Filter 至少 1 个 Edge Mission；
3. 存在至少 2 个安全 Stateful Controls 时至少 2 个有意义的 Combination Mission；
4. 每个 Suspicious Observation 至少 1 个安全 Confirmation Probe，或明确记录无法确认原因。

当前 Area 连续约 3 次安全 Probe 没有新关系、未知信息或异常证据时，只标记 Area Saturated，然后恢复稳定状态并切换未覆盖 Area。

URL-only 运行状态：

- `COMPLETED`：Coverage Gate 满足；
- `PARTIAL`：预算先耗尽，仍有 Coverage Gap；
- `BLOCKED`：环境、登录、权限或安全限制阻止关键探索。

### 2.8 输出

主要输出为普通 Markdown：

```text
exploration-report.md
```

至少包含：

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

可选 `requirements.md` 只从 Confirmed Behaviors、UI Semantics 和稳定 State Relations 导出。当前异常行为不能直接写成正式 Requirement。

## 3. Test Suite

`test-design` 只处理已经存在的正式 Requirement / PRD / AC。

每条 Case 包含：

- `source_refs`；
- `objective`、`steps`、`assertions`；
- `execution_channels`；
- `execution_requirements`；
- `open_question_refs`。

`execution_requirements` 包括：

- `capabilities`；
- `auth_roles`；
- `test_data`；
- `observability`；
- `fault_injection`；
- `permissions`；
- `env_vars`；
- `secret_requirements`。

Secret 值、Cookie、Session 和完整 Token 不进入 Test Suite。

## 4. Test Context

Test Context 描述当前运行环境真实具备的能力。

```text
Case requires                         Context provides
-------------                         ----------------
auth_roles: normal_user      ◄────►   available.auth_roles
observability: log           ◄────►   available.observability
permissions: logs:service    ◄────►   available.permissions
secret: test_user_password   ◄────►   runtime_secrets
```

`available` 只列真实具备能力。`provisioners` 是受信任环境准备操作。Runtime Context 是本次运行副本，`runtime_secrets` 只保存来源、状态和生命周期元数据，不保存 Secret 值。

## 5. Secret Resolver

`skills/test-orchestrator/secret.schema.json` 描述业务 Secret 名称到 `env_key` 的映射、类型、敏感等级、允许来源和生命周期策略。

来源优先级：

```text
Runtime Secret Store
→ .testing-agent/secrets.env
→ 当前进程环境变量
→ 外部 Provider 状态
→ 显式 Manual Input
```

Secret 值只存在于 Resolver 进程和它启动的子进程环境。

## 6. Preflight

Preflight 检查：

```text
execution_requirements ⊆ available
```

状态：

```text
全部满足 ───────────────► READY
缺失 + 自动 Provisioner ─► PROVISIONABLE
缺失 + 无自动路径 ───────► BLOCKED
需求未确定 ──────────────► NEEDS_CLARIFICATION
```

需求未澄清不是产品 FAIL。

## 7. Provision

Provisioner 类型：

- `command`；
- `playwright`；
- `api`；
- `manual`。

自动 Provision 固定执行 action、verification，验证成功后才写入 Runtime Context。Provision 失败写为 `provision_failure` blocker，不改变产品 FAIL 语义。

## 8. 执行通道

正式 Test Suite 支持四类通道：

| 通道 | 主要 Evidence |
|---|---|
| Browser | DOM、URL、Network、Trace、Screenshot、Storage State |
| API | Request / Response、状态码、关键字段、SSE 事件 |
| Log-Trace | 本次 Case 可关联的 Log / Trace / Metric |
| Static Inspection | 需求明确指定的文件、配置和实际值 |

Browser 继续使用 Microsoft Playwright CLI Skill。

## 9. Report 与正式状态

正式 Test Suite Assertion 状态：

- `PASS`：Observed 满足 Expected，Evidence 完整；
- `FAIL`：Observed 与 Expected 直接矛盾；
- `BLOCKED`：缺少执行或观察条件；
- `NOT_EXECUTED`：运行取消或中断。

Case 聚合和 Report Schema 保持原逻辑不变。

## 10. 公开契约

`exploratory-testing` 的 `exploration-report.md` 和可选 `requirements.md` 都是 Markdown 产物，**不是新的公共 JSON 契约**。

现有公开 JSON 契约保持不变：

- `skills/test-design/schema.json`：Test Suite；
- `skills/test-orchestrator/context.schema.json`：Test Context / Runtime Context；
- `skills/test-orchestrator/secret.schema.json`：Secret 定义；
- `skills/test-orchestrator/readiness.schema.json`：Readiness；
- `skills/test-orchestrator/schema.json`：正式 Test Report。

当前版本保持：

```text
Test Suite  1.4
Test Context 1.2
Readiness   1.0
Report      1.3
```

`exploratory-testing` 第一版不引入 Multi-agent、LangGraph、Supervisor、SQLite、Persistent Memory、Application Map JSON Schema、Action Tape、自研 Browser Engine 或 Crawler。
