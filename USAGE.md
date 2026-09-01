# Testing Agent Skills 用户使用教程

这套 Skill 包有两种不同入口，不要混用：

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
| `test-orchestrator` | Preflight、Provision、Reflight、执行路由、Evidence、PASS/FAIL/BLOCKED、Report、Cleanup | 不修改 Expected，不替业务补需求 |
| `playwright-cli` | Browser Snapshot、交互、Locator、Network、Trace、Screenshot、Playwright Test | 不决定业务语义和测试 Oracle |

最重要的边界：

```text
exploratory-testing = unknown app / unknown expected

test-design + test-orchestrator = known requirement / known expected
```

## 2. 安装运行依赖

安装 Python 校验依赖：

```bash
pip install "jsonschema>=4.20,<5"
```

安装 Playwright CLI：

```bash
npm install -g @playwright/cli@0.1.18
```

检查：

```bash
python -c "import jsonschema; print(jsonschema.__version__)"
playwright-cli --version
```

如果目标项目需要生成和运行正式 Playwright Test，再确认目标项目已经安装 Playwright：

```bash
npx --no-install playwright --version
```

> [!CAUTION]
> 不要让 Agent 未经确认升级目标项目依赖，也不要随意执行 `npm init playwright@latest`。优先复用目标项目已有配置。

## 3. 让 Agent 加载 Skill

四个目录：

```text
skills/exploratory-testing/
skills/test-design/
skills/test-orchestrator/
skills/playwright-cli/
```

只有 URL、没有正式需求时，读取：

```text
skills/exploratory-testing/SKILL.md
skills/playwright-cli/SKILL.md
```

已有正式 Requirement / PRD / AC 时，可以直接读取：

```text
skills/test-design/SKILL.md
skills/test-orchestrator/SKILL.md
skills/playwright-cli/SKILL.md
```

## 4. URL-only：直接做探索式测试

### 4.1 推荐提示词

```text
请先读取并严格遵守：
- skills/exploratory-testing/SKILL.md
- skills/playwright-cli/SKILL.md

目标页面：<运行中的页面 URL>
主要输出：exploration-report.md

要求：
1. 先建立 Feature Inventory 和 Application Map，不要打开页面后随便点击；
2. DOM / Accessibility 为主要事实源，Vision 只在必要时补充；
3. 对高价值功能规划 Normal / Edge / Combination Exploration Missions；
4. 每次重大交互执行 Before → Action → After → Delta；
5. 可疑行为必须做不同输入、路径或组合的 Confirmation Probe；
6. 使用 Coverage Gate 判断是否允许正常结束；
7. 没有正式 Requirement 时，不要把 STRONG_ANOMALY 叫做正式 FAIL；
8. 最终输出 exploration-report.md；
9. 只有我明确需要时，再额外导出 requirements.md。
```

### 4.2 Agent 应该怎样探索

正确流程：

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
Mission
↓
Before / Action / After / Delta
↓
Update Map / Finding
↓
选择下一 Mission
↓
Coverage Gate
```

不要使用旧流程：

```text
URL
→ 先猜 requirements.md
→ 再生成 test-cases.json
→ 最后才开始测试
```

### 4.3 Exploration Mission 不是正式 Test Case

Mission 是一个动态探索目标，例如：

```text
目标：确认 Search 是否会改变结果状态
Normal：搜索页面中真实存在的企业名
Edge：搜索明确不存在的随机字符串
Combination：先选择 Source Filter，再搜索
观察：列表、分页、空状态、loading，必要时 Network
```

Agent 可以根据前一个 Mission 的结果动态插入下一 Mission。

正式 Test Case 则需要已经明确的 Expected，由 `test-design` 负责。

### 4.4 Coverage Gate

默认预算：

```text
max_depth = 2
max_interactions = 30
```

这两个值只是上限，不代表探索完成。

正常结束至少要求：

- 每个安全 High-value Area 至少有 1 个 Normal Mission；
- 每个安全 Input / Filter 至少有 1 个 Edge Mission；
- 有多个安全 Stateful Controls 时至少有 2 个有意义的 Combination Mission；
- 每个 Suspicious Observation 至少有 1 个安全 Confirmation Probe。

如果当前 Area 连续约 3 次 Probe 没有新信息，应切换到其他未覆盖 Area，而不是结束整个 Exploration。

预算耗尽但 Coverage 未满足时必须报告：

```text
PARTIAL
```

不能写成 `COMPLETED`。

### 4.5 URL-only Finding

没有正式 Expected 时使用：

| 分类 | 含义 |
|---|---|
| `CONFIRMED_BEHAVIOR` | 直接 Evidence 支持的稳定行为 |
| `STRONG_ANOMALY` | 经过 Confirmation Probe 仍稳定存在的强异常信号 |
| `SUSPECTED_ANOMALY` | 可疑，但仍存在多个合理业务解释 |
| `UNKNOWN` | 当前证据、权限或安全边界不足 |

`STRONG_ANOMALY` 不等同正式 Requirement 下的 `FAIL`。

### 4.6 Implicit Oracle

URL-only 场景主要依赖：

```text
UI Semantic Oracle
Metamorphic Relation
State Invariant
Cross-feature Consistency
Reversibility
Health Signals
UX Contract（弱 Oracle）
```

尤其是 Metamorphic Relation：不知道精确正确结果时，比较两个语义明显不同的安全输入是否产生合理不同的状态。

例如：

```text
Query A = 页面中真实存在的企业名
Query B = __NO_RESULT_9F2A__
```

如果 A、B 的列表、分页、空状态和相关 Network 行为始终完全相同，就应该进入异常确认，而不是简单写成“规则待确认”。

### 4.7 `exploration-report.md` 最小示例

```markdown
# Exploratory Testing Report

**运行状态：COMPLETED**

## 1. Application Overview

页面包含来源筛选、搜索、资讯列表、分页和每页数量控制。

## 2. Application Map

- Source Filter --changes--> News List
- Source Filter --changes--> Total Pages
- Search --no observable effect--> Result State

## 3. Confirmed Behaviors

### BEH-001 来源筛选会改变列表范围

Evidence：选择单一来源后，当前列表和总页数发生变化。

## 4. Strong Anomalies

### ANOM-001 搜索操作未产生可观察结果变化

- Probe 1：搜索页面真实存在企业名
- Probe 2：搜索明确不存在字符串
- Probe 3：Source Filter + Search
- Before / After：输入值变化，但列表、分页和结果反馈均无明确变化
- Oracle：UI Semantic + Metamorphic Relation
- Classification：STRONG_ANOMALY

## 5. Suspected Anomalies

无。

## 6. Unknown / Unsafe Areas

- 外部第三方链接未深入探索。

## 7. Exploration Coverage

| Area | Normal | Edge | Combination | Result |
|---|---|---|---|---|
| Search | ✓ | ✓ | ✓ | Strong anomaly |
| Source Filter | ✓ | ✓ | ✓ | Confirmed |
| Pagination | ✓ | N/A | ✓ | Confirmed |

## 8. Reproduction Paths

ANOM-001：打开页面 → 输入存在企业名 → 查询 → 记录结果 → 输入不存在字符串 → 查询 → 对比结果。
```

### 4.8 可选导出 `requirements.md`

探索完成后，只有确实需要沉淀候选需求时才导出。

候选需求主要来自：

```text
Confirmed Behaviors
+
UI Semantics
+
稳定 State Relations
```

可以继续使用 `REQ-* / INF-* / Q-*`，但异常行为不能因为“当前页面就是这样”而自动成为 Requirement。

人工或正式需求确认后，才建议把这些候选需求交给 `test-design` 冻结成正式 Test Suite。

## 5. 有正式需求：生成 Test Suite

已有正式 Requirement / PRD / AC 时，使用 `test-design`。

推荐提示词：

```text
请先读取并遵守：
- skills/test-design/SKILL.md
- skills/test-orchestrator/SKILL.md
- skills/playwright-cli/SKILL.md

需求文档：<需求文档路径>
测试环境：<URL 或环境说明>
输出目录：<运行目录>

必须先生成并校验 Test Suite，再执行 Preflight。
未执行、无法观察或证据不足时不得判 PASS。
```

正式测试链：

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

> [!IMPORTANT]
> 正式 Requirement 和 Test Suite 中的 Expected 是验收基准。产品实际行为只能形成 Actual，不能反向修改 Expected 让测试通过。

## 6. 为正式测试准备独立目录

建议：

```text
test-run/
├── test-cases.json
├── test-context.json
├── readiness-before.json
├── readiness-before.md
├── runtime-context.json
├── readiness-after.json
├── readiness-after.md
├── report.json
├── test-report.md
└── artifacts/
```

| 文件 | 作用 |
|---|---|
| `test-cases.json` | Test Suite |
| `test-context.json` | 基础环境能力和 Provisioner |
| `readiness-before.*` | Provision 前状态 |
| `runtime-context.json` | 当前运行 Context 副本和 Secret 元数据 |
| `readiness-after.*` | Provision 后重新检查结果 |
| `report.json` | 机器可校验报告 |
| `test-report.md` | 人类可读测试报告 |
| `artifacts/` | Trace、截图、响应、日志等证据 |

## 7. Test Suite

生成后必须校验：

```bash
python skills/test-design/scripts/validate_testcases.py test-run/test-cases.json
```

重要规则：

- 保留原始 Requirement / BR / AC 追溯；
- 必需 Assertion 必须有明确 Expected；
- `observe_via` 表示实际计划取得的证据；
- 无法唯一确定 Expected 时使用 `NEEDS_CLARIFICATION`；
- 不自行替业务补规则。

Test Suite 当前版本：`1.4`。

## 8. Test Context、Secret 与 Preflight

Test Context 当前版本：`1.2`。

校验：

```bash
python skills/test-orchestrator/scripts/validate_context.py test-context.json
```

Secret Resolver：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
```

Preflight：

```bash
python skills/test-orchestrator/scripts/preflight.py \
  test-cases.json runtime-context.json --out readiness.json
```

状态：

```text
READY
PROVISIONABLE
BLOCKED
NEEDS_CLARIFICATION
```

Provision 只执行 Test Context 中明确声明的受信任操作，且验证成功后才写回 Runtime Context。Provision 失败属于环境准备失败，不判产品 FAIL。

Secret 值不得写入 Suite、Context、Readiness、Report、Markdown 或截图。

## 9. 执行与报告

正式执行支持：

```text
Browser
API
Log-Trace
Static Inspection
```

Browser 由 `playwright-cli` 完成具体页面操作和 Evidence 获取。

Report 当前版本：`1.3`，Readiness 当前版本：`1.0`。

最终校验：

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
