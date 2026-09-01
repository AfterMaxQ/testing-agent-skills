# Testing Agent Skills 用户使用教程

这套 Skill 包有两种入口：

```text
有正式 Requirement / PRD / AC
→ test-design
→ test-orchestrator
→ PASS / FAIL / BLOCKED

只有运行中的 Web URL、没有明确 Expected
→ exploratory-testing
→ exploration-report.md
→ optional requirements.md
```

## 1. Skill 分工

| Skill | 负责什么 | 不负责什么 |
|---|---|---|
| `exploratory-testing` | URL-only 下建立 Application Map、规划 Mission、主动探索、发现异常、检查 Coverage | 不把当前页面行为当正式 Expected，不直接输出正式 FAIL |
| `test-design` | 已有需求下生成 Case、Expected、证据入口和运行条件 | 不生成 Locator，不负责开放式探索 |
| `test-orchestrator` | Secret Resolution、Preflight、Provision、Reflight、执行路由、Evidence、Report、Cleanup | 不修改 Expected，不替业务补需求 |
| `playwright-cli` | Browser Snapshot、交互、Locator、Network、Trace、Screenshot、Playwright Test | 不决定业务语义和测试 Oracle |

## 2. 安装依赖

```bash
pip install "jsonschema>=4.20,<5"
npm install -g @playwright/cli@0.1.18
```

## 3. URL-only 探索式测试

读取：

```text
skills/exploratory-testing/SKILL.md
skills/playwright-cli/SKILL.md
```

推荐最小提示词：

```text
请先读取并严格遵守：
- skills/exploratory-testing/SKILL.md
- skills/playwright-cli/SKILL.md

目标页面：<URL>
最终输出：exploration-report.md

请直接按照 exploratory-testing Skill 自主完成探索式测试。
```

主要流程：

```text
Initial Observation
→ Feature Inventory
→ Application Map
→ Exploration Planner
→ Exploration Missions
→ Before / Action / After / Delta
→ Confirmation Probe
→ Coverage Gate
→ exploration-report.md
```

Finding：

```text
CONFIRMED_BEHAVIOR
STRONG_ANOMALY
SUSPECTED_ANOMALY
UNKNOWN
```

运行状态：

```text
COMPLETED
PARTIAL
BLOCKED
```

## 4. 正式需求测试

读取：

```text
skills/test-design/SKILL.md
skills/test-orchestrator/SKILL.md
skills/playwright-cli/SKILL.md
```

正式链路：

```text
Requirement / PRD
→ test-cases.json
→ test-context.json
→ Secret Resolution
→ Preflight
→ Provision
→ runtime-context.json
→ Reflight
→ Execute
→ Evidence
→ report.json
→ Cleanup
→ test-report.md
```

契约版本：

```text
Test Suite   1.4
Test Context 1.2
Readiness    1.0
Report       1.3
```

## 5. Secret 模板与本地目录

模板位置：

```text
skills/test-orchestrator/examples/
├── config.example.json
└── secrets.env.example
```

本地运行目录：

```text
.testing-agent/
├── config.json
├── secrets.env
└── runtime/
    └── secrets.env
```

`.testing-agent/` 已被 `.gitignore` 忽略。

### Linux / macOS

```bash
mkdir -p .testing-agent
cp skills/test-orchestrator/examples/config.example.json .testing-agent/config.json
cp skills/test-orchestrator/examples/secrets.env.example .testing-agent/secrets.env
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force .testing-agent | Out-Null
Copy-Item skills/test-orchestrator/examples/config.example.json .testing-agent/config.json
Copy-Item skills/test-orchestrator/examples/secrets.env.example .testing-agent/secrets.env
```

填写 `.testing-agent/secrets.env`：

```dotenv
TEST_USER_USERNAME=...
TEST_USER_PASSWORD=...
API_TOKEN=...
```

Resolver 默认查找顺序：

```text
Runtime Secret Store
→ Local Secret Store
→ 当前进程环境变量
→ Secret Schema 声明的外部 Provider
→ 显式 Manual Input
```

Secret 值不得写入 Suite、Context、Readiness、Report、Markdown、截图或日志。

## 6. Secret Resolver

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
```

让后续命令继承解析后的 Secret：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json \
  --exec python skills/test-orchestrator/scripts/preflight.py \
    test-cases.json runtime-context.json --out readiness.json
```

## 7. Preflight 与 Report

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
python skills/test-orchestrator/scripts/validate_context.py test-context.json
python skills/test-orchestrator/scripts/preflight.py \
  test-cases.json runtime-context.json --out readiness.json
```

Readiness：

```text
READY
PROVISIONABLE
BLOCKED
NEEDS_CLARIFICATION
```

最终报告：

```bash
python skills/test-orchestrator/scripts/validate_report.py report.json \
  --suite test-cases.json --context runtime-context.json
python skills/test-orchestrator/scripts/render_report.py report.json \
  --suite test-cases.json --out test-report.md
```

Assertion 状态：

```text
PASS
FAIL
BLOCKED
NOT_EXECUTED
```
