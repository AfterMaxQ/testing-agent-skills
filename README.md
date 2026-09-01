# Testing Agent Skills

面向 Coding Agent 的通用测试 Skill 包，支持两种不同场景：

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

详细操作说明见 [USAGE.md](USAGE.md)。Browser 能力直接复用 Microsoft Playwright CLI Skill。

## 1. 核心 Skill

| Skill | 负责 |
|---|---|
| `exploratory-testing` | URL-only、未知 Expected 的应用理解与探索式测试 |
| `test-design` | 已有需求下的 Case、Expected、证据入口、运行条件和追溯 |
| `test-orchestrator` | Secret Resolution、Preflight、Provision、Reflight、执行路由、Evidence、Report、Cleanup |
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

`requirements.md` 仅在探索后按需导出。没有正式 Expected 时，`STRONG_ANOMALY` 不等同正式 `FAIL`。

## 3. 有正式需求：Requirements-driven Testing

```text
Requirement / PRD
→ test-design
→ test-cases.json
→ test-context.json
→ Secret Resolution
→ Preflight
→ Provision / Reflight
→ Browser / API / Log-Trace / Static Inspection
→ Evidence
→ report.json
→ test-report.md
```

Test Suite 的 Expected 只能来自正式需求和 Test Suite，不能根据产品当前表现倒改 Expected。

## 4. Secret 本地配置

仓库不再提交 `.testing-agent/` 模板目录。模板统一放在：

```text
skills/test-orchestrator/examples/
├── config.example.json
└── secrets.env.example
```

需要本地 Secret Store 时，把模板复制到运行项目根目录下的 `.testing-agent/`：

```text
.testing-agent/
├── config.json
├── secrets.env
└── runtime/
    └── secrets.env
```

其中 `.testing-agent/` 是**本地运行时目录**，不应提交到 Git。Resolver 仍兼容这些默认路径；如果不创建本地 Secret Store，也可以直接使用当前进程环境变量或已声明的外部 Provider。

示例：

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

不要把真实密码、Token、Cookie 或 Session 写入 Test Suite、Context、Readiness、Report 或仓库。

## 5. 安装

Playwright CLI：

```bash
npm install -g @playwright/cli@0.1.18
```

JSON Schema 校验：

```bash
pip install "jsonschema>=4.20,<5"
```

## 6. 目录

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
    │   └── scripts/
    └── playwright-cli/
```
