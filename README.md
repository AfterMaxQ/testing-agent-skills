# Testing Agent Skills

面向 Coding Agent 的通用测试 Skill 包，支持两种场景：

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

详细操作说明见 [USAGE.md](USAGE.md)。Browser 能力复用 Microsoft Playwright CLI Skill。

## 1. 核心 Skill

| Skill | 负责 |
|---|---|
| `exploratory-testing` | URL-only、未知 Expected 的应用理解与探索式测试 |
| `test-design` | 已有需求下的 Case、Expected、证据入口、运行条件和追溯 |
| `test-orchestrator` | Secret Resolution、Preflight、Provision、Reflight、执行路由、Evidence、运行进度、Report、Cleanup |
| `playwright-cli` | Browser Snapshot、交互、Locator、Network、Trace、Screenshot、Playwright Test |

## 2. URL-only：Exploratory Testing

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
```

`requirements.md` 是可选导出。没有正式 Expected 时，Finding 使用 `CONFIRMED_BEHAVIOR`、`STRONG_ANOMALY`、`SUSPECTED_ANOMALY`、`UNKNOWN`，其中 `STRONG_ANOMALY` 不等同于正式需求测试中的 `FAIL`。

## 3. Requirements-driven Testing

```text
Requirement / PRD
→ test-design
→ test-cases.json
→ test-context.json
→ Secret Resolution
→ Preflight
→ Provision / Reflight
→ Browser / API / Log-Trace / Static Inspection
→ execution-progress.json
→ Evidence
→ report.json
→ test-report.md
```

Test Suite 的 Expected 只来自正式需求和 Test Suite，产品实际行为只形成 Actual。

`test-orchestrator` 在正式执行开始时创建 `execution-progress.json`，进入 Case 时更新当前 Case，每个 Case 得到 `PASS`、`FAIL`、`BLOCKED` 或 `NOT_EXECUTED` 终态后立即写入一次 checkpoint。该文件只表示本次执行的运行态进度；正式 `report.json` 仍在全部 Case 结束后生成，并继续遵守 Report 1.3 的完整 Suite 契约。

## 4. Secret 本地配置

配置模板位于：

```text
skills/test-orchestrator/examples/
├── config.example.json
└── secrets.env.example
```

运行项目可以使用以下本地目录：

```text
.testing-agent/
├── config.json
├── secrets.env
├── execution-progress.json
└── runtime/
    └── secrets.env
```

`.testing-agent/` 是本地运行目录，已被 `.gitignore` 忽略。Resolver 默认识别：

```text
.testing-agent/config.json
.testing-agent/secrets.env
.testing-agent/runtime/secrets.env
```

也可以直接通过当前进程环境变量或 Secret Schema 声明的外部 Provider 提供 Secret。

Linux / macOS：

```bash
mkdir -p .testing-agent
cp skills/test-orchestrator/examples/config.example.json .testing-agent/config.json
cp skills/test-orchestrator/examples/secrets.env.example .testing-agent/secrets.env
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force .testing-agent | Out-Null
Copy-Item skills/test-orchestrator/examples/config.example.json .testing-agent/config.json
Copy-Item skills/test-orchestrator/examples/secrets.env.example .testing-agent/secrets.env
```

真实密码、Token、Cookie 和 Session 不写入 Test Suite、Context、Readiness、Report 或 Git 仓库。

## 5. 契约版本

```text
Test Suite   1.4
Test Context 1.2
Readiness    1.0
Report       1.3
```

`execution-progress.json` 是运行态 checkpoint，不属于正式 Report 契约。

## 6. 安装

```bash
npm install -g @playwright/cli@0.1.18
pip install "jsonschema>=4.20,<5"
```

## 7. 目录

```text
testing-agent-skills/
├── README.md
├── USAGE.md
├── .gitignore
└── skills/
    ├── exploratory-testing/
    │   └── SKILL.md
    ├── test-design/
    │   ├── SKILL.md
    │   ├── schema.json
    │   └── scripts/
    ├── test-orchestrator/
    │   ├── SKILL.md
    │   ├── schema.json
    │   ├── context.schema.json
    │   ├── readiness.schema.json
    │   ├── secret.schema.json
    │   ├── examples/
    │   │   ├── config.example.json
    │   │   └── secrets.env.example
    │   ├── secret-resolver/
    │   │   └── SKILL.md
    │   ├── scripts/
    │   │   └── update_progress.py
    │   └── tests/
    │       └── test_update_progress.py
    └── playwright-cli/
```
