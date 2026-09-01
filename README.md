# Testing Agent Skills

面向 Coding Agent 的通用测试 Skill 包，明确支持两种不同场景：

```text
有正式 Requirement / PRD / AC
→ test-design
→ test-orchestrator
→ PASS / FAIL / BLOCKED

只有运行中的 Web URL、没有明确 Expected
→ exploratory-testing
→ Application Map + Exploration Missions
→ exploration-report.md
→ optional requirements.md
```

详细操作说明见 [USAGE.md](USAGE.md)。

Browser 能力直接复用 Microsoft Playwright CLI Skill。仓库自研部分负责探索策略、需求级测试设计、测试环境就绪检查、跨通道执行规则、Evidence 判定和报告汇总。

## 1. 总体架构

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

四个核心 Skill：

| Skill | 负责 |
|---|---|
| `exploratory-testing` | URL-only、未知 Expected 的应用理解与探索式测试：Feature Inventory、Application Map、Mission、Coverage Gate、异常发现与探索报告 |
| `test-design` | 已有需求下的需求拆解、Case、Expected、证据入口、执行通道、运行条件和追溯 |
| `test-orchestrator` | Preflight、Provision、Reflight、执行路由、Evidence 汇总、PASS/FAIL/BLOCKED、Report 与 Cleanup |
| `playwright-cli` | Browser Snapshot、元素识别、交互、Locator、Network、Trace、Screenshot、Playwright Test |

`exploratory-testing` 与正式 Test Suite 流程是两条入口，不属于 `test-orchestrator` 的公共 JSON 状态机，也不会修改现有 Test Suite / Context / Readiness / Report Schema。

## 2. URL-only：Exploratory Testing

当只有 URL、没有正式需求时，不再强制：

```text
URL
→ requirements.md
→ test-cases.json
→ 再开始测试
```

而是直接：

```text
URL
→ Initial Observation
→ Feature Inventory
→ Application Map
→ Exploration Planner
→ Exploration Missions
→ Execute / Observe / Update Map
→ Coverage Gate
→ Findings
→ exploration-report.md
→ optional requirements.md
```

### 2.1 Application Map

不是只枚举按钮，而是建立状态关系，例如：

```text
Source Filter --changes--> News List
Source Filter --changes--> Total Pages
Page Size --changes--> Visible Item Count
Search --?--> Result State
```

未知关系 `--?-->` 会优先变成新的 Exploration Mission。

### 2.2 Exploration Missions

同一个 Agent 使用三个探索视角：

```text
Normal       正常用户行为
Edge         高信息量边界 / 空值 / 不存在值 / 可逆反例
Combination  代表性的 Stateful 控件组合
```

每个重大交互都执行：

```text
Before → Action → After → Delta
```

可疑行为不能立刻写成 `Q` 或结束，必须至少做一次不同输入、路径或组合的 Confirmation Probe。

### 2.3 Coverage Gate

默认预算：

```text
max_depth = 2
max_interactions = 30
```

它们只是 Hard Limit，不是完成条件。

正常完成至少要求：

- 每个安全 High-value Area 至少 1 个 Normal Mission；
- 每个安全 Input / Filter 至少 1 个 Edge Mission；
- 存在多个安全 Stateful Controls 时至少 2 个有意义的 Combination Mission；
- 每个 Suspicious Observation 至少 1 个安全 Confirmation Probe。

当前 Area 连续探索没有新信息时，应切换到未覆盖 Area，而不是结束整个运行。

URL-only Findings 使用：

```text
CONFIRMED_BEHAVIOR
STRONG_ANOMALY
SUSPECTED_ANOMALY
UNKNOWN
```

运行状态使用：

```text
COMPLETED
PARTIAL
BLOCKED
```

没有正式 Expected 时，`STRONG_ANOMALY` 不等同正式 `FAIL`。

### 2.4 输出

主要输出：

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

`requirements.md` 只在探索后按需导出，候选需求主要来自 Confirmed Behaviors、UI Semantics 和稳定 State Relations。当前异常行为不能因为“页面现在就是这样”而被写成正式 Requirement。

## 3. 有正式需求：Requirements-driven Testing

已有 Requirement / PRD / AC 时，继续使用原有正式链路：

```text
Requirement / PRD
  ↓
test-design
  ↓
test-cases.json
  ↓
test-context.json
  ↓
Secret Resolution
  ↓
Preflight
  ↓
Provision / Reflight
  ↓
Browser / API / Log-Trace / Static Inspection
  ↓
Evidence
  ↓
report.json
  ↓
test-report.md
```

Test Suite 的 Expected 只能来自正式需求和 Test Suite，不能根据产品当前表现倒改 Expected。

### 3.1 Test Suite 声明运行条件

每条 Case 用 `execution_requirements` 声明所需能力：

```json
{
  "capabilities": ["browser", "log_trace"],
  "auth_roles": ["normal_user"],
  "test_data": ["long_text_fixture"],
  "observability": ["browser_dom", "log"],
  "fault_injection": [],
  "permissions": ["logs:verify-service"],
  "env_vars": [],
  "secret_requirements": [
    {"name": "test_user_password", "required": true, "persist": false}
  ]
}
```

Secret 值、密码、完整 Token、Cookie 和 Session 不进入 Test Suite / Context / Readiness / Report。

### 3.2 Preflight 与 Provision

常用命令：

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
python skills/test-orchestrator/scripts/validate_context.py test-context.json
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
python skills/test-orchestrator/scripts/preflight.py \
  test-cases.json runtime-context.json --out readiness.json
```

Preflight 状态：

- `READY`：可以直接执行；
- `PROVISIONABLE`：缺条件，但有受信任 Provisioner；
- `BLOCKED`：缺条件且没有自动路径；
- `NEEDS_CLARIFICATION`：需求本身不够明确。

Provision 失败属于环境准备问题，不判产品 FAIL。

### 3.3 Browser Case

Browser 执行直接使用 `playwright-cli`：

```text
需求级 Browser Case
→ Seed / Fixture
→ Planning
→ Locator / Playwright Test
→ Run
→ DOM / URL / Network / Trace / Screenshot
```

## 4. 安装

Playwright CLI：

```bash
npm install -g @playwright/cli@0.1.18
```

JSON Schema 校验：

```bash
pip install "jsonschema>=4.20,<5"
```

## 5. 目录

```text
testing-agent-skills/
├── README.md
├── USAGE.md
├── docs/
│   ├── architecture.md
│   ├── implementation-plan.md
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── skills/
│   ├── exploratory-testing/
│   │   └── SKILL.md
│   ├── test-design/
│   │   ├── SKILL.md
│   │   ├── schema.json
│   │   └── scripts/validate_testcases.py
│   ├── test-orchestrator/
│   │   ├── SKILL.md
│   │   ├── schema.json
│   │   ├── context.schema.json
│   │   ├── readiness.schema.json
│   │   ├── secret.schema.json
│   │   ├── secret-resolver/SKILL.md
│   │   └── scripts/
│   └── playwright-cli/
├── licenses/
├── .gitignore
└── .testing-agent/
```
