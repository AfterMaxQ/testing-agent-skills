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

## 1. 四个 Skill

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

URL-only 不先生成 Test Suite，也不调用 `test-orchestrator`。没有正式 Expected 时使用：

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

Test Suite 当前版本为 `1.4`，Test Context 为 `1.2`，Readiness 为 `1.0`，Report 为 `1.3`。

## 5. Secret 模板与本地运行目录

Secret 模板已经迁移到：

```text
skills/test-orchestrator/examples/
├── config.example.json
└── secrets.env.example
```

仓库中**不再保留 `.testing-agent/` 模板目录**。

`.testing-agent/` 现在只表示用户本地的运行时目录。需要文件型 Secret Store 时，在目标项目根目录自行创建：

```text
.testing-agent/
├── config.json
├── secrets.env
└── runtime/
    └── secrets.env
```

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

填写真实值时，只改本地 `.testing-agent/secrets.env`：

```dotenv
TEST_USER_USERNAME=...
TEST_USER_PASSWORD=...
API_TOKEN=...
```

`.testing-agent/` 整个目录都属于本地运行数据，不应提交到 Git。

如果不想创建文件型 Secret Store，也可以直接通过当前进程环境变量提供值。Resolver 的查找顺序仍为：

```text
Runtime Secret Store
→ Local Secret Store
→ 当前进程环境变量
→ 已声明的外部 Provider
→ 显式 Manual Input
```

## 6. Secret Resolver

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
```

Secret 值不得写入 Suite、Context、Readiness、Report、Markdown、截图或日志。

## 7. Preflight 与报告

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
python skills/test-orchestrator/scripts/validate_context.py test-context.json
python skills/test-orchestrator/scripts/preflight.py \
  test-cases.json runtime-context.json --out readiness.json
```

正式 Case 状态：

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

正式 Assertion 状态：

```text
PASS
FAIL
BLOCKED
NOT_EXECUTED
```

不要把环境缺失、需求不清楚或无法观察的问题伪装成产品 FAIL。
