# Testing Agent Skills 用户使用教程

这套 Skill 包用于把需求文档转换成可追溯测试用例，检查测试环境是否就绪，调用 Browser、API、Log-Trace 或 Static Inspection 取得真实证据，最后输出统一测试报告。只有运行中的 Web 页面、缺少正式需求文档时，也可以先使用 `requirement-discovery` 生成候选 `requirements.md`。

适用输入包括：PRD、验收标准、业务规则、接口/SSE 契约、自然语言需求，以及需要反向提取候选需求的运行中 Web 页面。

## 1. 先理解四个 Skill

| Skill | 负责什么 | 不负责什么 |
|---|---|---|
| `requirement-discovery` | 从运行中的网页提取候选需求并输出 `requirements.md` | 不生成 Test Case，不决定正式产品需求 |
| `test-design` | 需求拆解、Case、Expected、证据入口、运行条件 | 不生成 Locator，不执行测试 |
| `test-orchestrator` | Preflight、Provision、Reflight、通道路由、证据判定、报告、Cleanup | 不修改 Expected，不分析根因 |
| `playwright-cli` | Browser 探索、交互、Locator、Trace、Screenshot、Playwright Test | 不决定业务需求是否正确 |

已有正式需求时，完整测试链路不变：

```text
需求文档
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

只有网页、没有正式需求时，可以先走：

```text
运行中的网页
  → requirement-discovery
  → requirements.md
  → test-design
  → 后续测试链路
```

> [!IMPORTANT]
> 原始需求和 Test Suite 中的 Expected 是验收基准。产品实际行为只能形成 Actual。不能因为页面当前就是这样，就自动修改 Expected 让测试通过。`requirement-discovery` 输出的是页面反向提取的候选需求，不自动等同于正式产品需求。

## 2. 安装运行依赖

安装 Python 校验依赖：

```bash
pip install "jsonschema>=4.20,<5"
```

安装 Playwright CLI：

```bash
npm install -g @playwright/cli@0.1.18
```

检查安装：

```bash
python -c "import jsonschema; print(jsonschema.__version__)"
playwright-cli --version
```

如果目标项目需要生成和运行正式 Playwright Test，还要确认目标项目已经安装 Playwright：

```bash
npx --no-install playwright --version
```

> [!CAUTION]
> 不要让 Agent 未经确认就在目标项目中升级依赖或执行 `npm init playwright@latest`。优先使用目标项目已有的 Playwright 配置、Fixture 和依赖版本。

## 3. 让 Agent 加载 Skill 包

确保 Agent 能读取以下四个目录：

```text
skills/requirement-discovery/
skills/test-design/
skills/test-orchestrator/
skills/playwright-cli/
```

只有网页、没有需求文档时，先读取 `requirement-discovery` + `playwright-cli`。已有正式需求时，可以直接从 `test-design` 开始；`requirement-discovery` 不要求每次测试都执行。

如果 Agent 支持 Skill 安装，将需要的目录分别安装为 Skill；如果不支持自动发现，在任务中明确要求先读取对应 `SKILL.md`。

已有需求时的推荐指令：

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

> [!NOTE]
> 自研 Skill 使用工具中立的输入输出契约，不绑定 Codex、Trae 或某个 Agent 的专有工具名。不同 Agent 的 Skill 安装方式可以不同，但数据契约和执行顺序不能改变。

## 4. 为一次测试准备独立目录

建议在目标项目或单独交付目录下准备本次运行目录：

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

各文件作用：

| 文件 | 作用 |
|---|---|
| `test-cases.json` | 需求级 Test Suite |
| `test-context.json` | 基础环境已经具备什么、缺少时怎样准备 |
| `readiness-before.*` | Provision 前的就绪情况 |
| `runtime-context.json` | 本次运行的 Context 副本、已验证 Provision 结果和 Secret 元数据 |
| `readiness-after.*` | Provision 后重新检查的结果 |
| `report.json` | 机器可校验的最终报告 |
| `test-report.md` | 用户阅读和交付的正式报告 |
| `artifacts/` | Trace、截图、响应、日志摘录等产物 |

> [!IMPORTANT]
> `test-context.json` 是基础环境契约，`runtime-context.json` 是本次运行副本。Provision 时不要直接覆盖基础 Context，否则下次运行可能把临时资源误认为永久可用。

## 可选：从网页发现需求

当只有已经运行的 Web 页面、没有正式需求文档时，先独立运行 `requirement-discovery`。它到 `requirements.md` 即结束，不自动生成 Test Case，也不自动进入测试执行。

推荐指令：

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

最小输出示例：

```markdown
# 快讯资讯页面需求

> 本文档根据当前运行中的产品页面反向提取，不等同于正式产品需求。

## 功能需求

### REQ-001 用户可以切换快讯分类

用户可以切换不同快讯分类，切换后展示对应内容。

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

`requirement-discovery` 到 `requirements.md` 即结束。如果后续要测试，再把经人工确认或直接接受的 `requirements.md` 交给 `test-design`。进入测试阶段后，正式需求和 Test Suite Expected 仍然是验收基准；页面实际行为不能反向修改 Expected。

## 5. 第一步：生成 Test Suite

让 Agent 使用 `test-design` 读取需求并输出 `test-cases.json`。

推荐指令：

```text
请使用 test-design 把需求转换成 test-cases.json。

要求：
1. 保留原始 Requirement、BR、AC 和字段名；
2. 不从需求之外发明业务规则；
3. 每条必需 Assertion 必须有精确 Expected；
4. 为每条 Assertion 指定实际计划取得的 observe_via；
5. 区分 browser、api、log_trace、static_inspection；
6. 无法唯一确定 Expected 时标记 NEEDS_CLARIFICATION；
7. 输出符合 Test Suite Schema 1.4；
8. 输出后运行 validate_testcases.py。
```

### 5.1 Test Suite 最小示例

```json
{
  "schema_version": "1.4",
  "suite_id": "feature-smoke",
  "feature": "示例功能",
  "source_documents": [
    {
      "id": "REQ",
      "path": "requirements.md"
    }
  ],
  "open_questions": [],
  "cases": [
    {
      "id": "AC001-001",
      "title": "提交内容后展示核实结果",
      "source_refs": ["AC-001"],
      "open_question_refs": [],
      "objective": "验证用户提交内容后能够看到结构化核实结果",
      "design_status": "READY",
      "priority": "P0",
      "execution_channels": ["browser"],
      "preconditions": ["测试环境可访问"],
      "execution_requirements": {
        "capabilities": ["browser"],
        "auth_roles": ["normal_user"],
        "test_data": ["short_text_fixture"],
        "observability": ["browser_dom"],
        "fault_injection": [],
        "permissions": [],
        "env_vars": [],
        "secret_requirements": [
          {"name": "test_user_password", "required": true, "persist": false}
        ]
      },
      "test_data": {
        "fixture": "short_text_fixture",
        "description": "包含一个可核实事实的短文本"
      },
      "steps": [
        "使用 normal_user 登录",
        "提交 short_text_fixture",
        "等待核实报告生成"
      ],
      "assertions": [
        {
          "id": "A1",
          "expected": "页面展示核实结论、理由和证据",
          "observe_via": ["browser_dom"],
          "required": true
        }
      ],
      "cleanup": [],
      "ambiguity_note": null
    }
  ]
}
```

### 5.2 Test Suite 关键字段

| 字段 | 通俗解释 |
|---|---|
| `source_refs` | 这条 Case 来自哪条 AC/BR |
| `design_status` | Expected 是否已经明确 |
| `execution_channels` | 用 Browser、API、日志还是源码验证 |
| `execution_requirements` | 执行前必须具备什么 |
| `observe_via` | 这条 Assertion 实际计划取得哪些证据 |
| `required` | 是否参与 Case 最终状态聚合 |

> [!IMPORTANT]
> `observe_via` 不是“任选一种”。如果填写 `browser_dom` 和 `browser_network`，正式 PASS/FAIL 报告中两类 Evidence 都必须存在。

> [!CAUTION]
> 必需 Assertion 不能只依赖 Screenshot 或 Human Evidence。截图可以作为辅助，但不能单独证明内部并发、重试、接口字段或持久化状态。

### 5.3 需求不清楚时

顶层增加问题：

```json
"open_questions": [
  {
    "id": "Q1",
    "source_refs": ["AC-003"],
    "question": "合法的进度步骤顺序是什么？",
    "impact": "无法确定进度测试的 Expected"
  }
]
```

受影响 Case 使用：

```json
"design_status": "NEEDS_CLARIFICATION",
"open_question_refs": ["Q1"],
"ambiguity_note": "需求未定义合法进度顺序"
```

> [!WARNING]
> `NEEDS_CLARIFICATION` 是需求问题，不是产品 FAIL。不要替业务负责人自行补规则，也不要执行这条 Case 后猜测 Expected。

### 5.4 校验 Test Suite

```bash
python skills/test-design/scripts/validate_testcases.py test-run/test-cases.json
```

成功示例：

```text
OK: test-run/test-cases.json (1 cases)
```

错误分为：

- `SCHEMA`：字段、类型、枚举或版本错误；
- `SEMANTIC`：JSON 结构合法，但通道、证据、测试数据或澄清关联不一致。

> [!IMPORTANT]
> Test Suite 校验失败时停止执行。不要跳过错误直接 Preflight，否则后面的状态和报告都不可信。

## 6. 第二步：编写 Test Context

Test Suite 表示“Case 需要什么”，Test Context 表示“当前环境有什么，以及缺少时怎样准备”。

### 6.1 Test Context 示例

```json
{
  "schema_version": "1.2",
  "context_id": "staging",
  "environment": {
    "name": "staging",
    "base_url": "https://staging.example.com",
    "notes": []
  },
  "available": {
    "capabilities": ["browser", "api"],
    "auth_roles": [],
    "test_data": ["short_text_fixture"],
    "observability": [
      "browser_dom",
      "browser_url",
      "browser_network",
      "api_response"
    ],
    "fault_injection": [],
    "permissions": [],
    "env_vars": []
  },
  "runtime_secrets": [],
  "provisioners": [
    {
      "id": "prepare-normal-user",
      "kind": "playwright",
      "provides": [
        {
          "category": "auth_roles",
          "name": "normal_user"
        }
      ],
      "action": "使用测试账号登录并保存 Playwright Storage State",
      "verification": "重新打开受保护页面并确认 normal_user 已登录",
      "cleanup_action": null,
      "requires_env": [],
      "secret_requirements": [
        {"name": "test_user_password", "required": true, "persist": false}
      ],
      "notes": []
    }
  ]
}
```

### 6.2 `available` 的填写原则

只能填写当前环境确实具备的能力：

- 有浏览器运行能力才能写 `browser`；
- 能读取服务日志才能写 `log`；
- 有对应权限才能写入 `permissions`；
- 测试数据真实存在才能写入 `test_data`；
- 能执行故障模拟才能写入 `fault_injection`。

> [!WARNING]
> 不要为了让 Preflight 显示 READY 而虚构环境能力。虚假的 Context 会把“不能测”伪装成 PASS 风险。

### 6.3 Secret 和环境变量

密码、Token、Cookie 和 Session 值不能写进 Suite、Context、Readiness、Report 或截图。Secret 定义写在 `skills/test-orchestrator/secret.schema.json`，本地值默认写在 `.testing-agent/secrets.env`。

第一次使用时复制模板：

PowerShell：

```powershell
Copy-Item .testing-agent/secrets.env.example .testing-agent/secrets.env
notepad .testing-agent/secrets.env
```

Bash：

```bash
cp .testing-agent/secrets.env.example .testing-agent/secrets.env
$EDITOR .testing-agent/secrets.env
```

`.testing-agent/secrets.env` 和 `.testing-agent/runtime/` 已被 `.gitignore` 排除。不要把真实值填入 `*.example` 文件之外的 JSON、Markdown 或命令行参数。

需要自定义 Secret 文件路径或默认启用 Manual Input 时，复制 `.testing-agent/config.example.json` 为 `.testing-agent/config.json` 再调整对应字段；默认路径无需配置文件。

Secret Resolver 的来源顺序：Runtime Secret Store → Local Secret Store → 当前进程环境变量 → 已声明的外部 Provider → 显式启用的 Manual Input。

生成 Runtime Context：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-run/test-cases.json \
  --context test-run/test-context.json \
  --out test-run/runtime-context.json
```

把解析后的值只注入后续命令：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-run/test-cases.json \
  --context test-run/test-context.json \
  --out test-run/runtime-context.json \
  --exec python skills/test-orchestrator/scripts/preflight.py \
    test-run/test-cases.json test-run/runtime-context.json \
    --out test-run/readiness-before.json
```

Runtime Context 只保存 `source`、`status`、`env_key`、`persist_policy`、`resolved_at` 和 `expires` 等元数据。`persist` 只记录策略，Resolver 不自动把值写回 Secret Store。必需 Secret 不是 `resolved` 时，Resolver 返回非零退出码且不执行 `--exec`；外部 Provider 没有连接时记录 `unavailable`；人工输入只有显式添加 `--allow-manual` 才会启用。

直接使用进程环境变量也是可行的：

```powershell
$env:TEST_USER_PASSWORD = "通过安全方式取得的密码"
```

Bash：

```bash
export TEST_USER_PASSWORD="通过安全方式取得的密码"
```

> [!IMPORTANT]
> `available.env_vars` 只声明 Case 的环境依赖，不能证明 Secret 已注入。Preflight 对 Secret 还会检查 Runtime Context 的 `resolved` 状态和当前子进程中的非空 `env_key`。

### 6.4 校验 Test Context

```bash
python skills/test-orchestrator/scripts/validate_context.py test-run/test-context.json
```

## 7. 第三步：运行 Preflight

生成机器可读 Readiness：

```bash
python skills/test-orchestrator/scripts/preflight.py test-run/test-cases.json test-run/runtime-context.json --out test-run/readiness-before.json
```

生成用户可读 Markdown：

```bash
python skills/test-orchestrator/scripts/render_readiness.py test-run/readiness-before.json --out test-run/readiness-before.md
```

### 7.1 四种状态

| 状态 | 含义 | 下一步 |
|---|---|---|
| `READY` | 当前环境可以直接执行 | 进入通道执行 |
| `PROVISIONABLE` | 缺少条件，但可以自动准备 | 执行并验证 Provisioner |
| `BLOCKED` | 当前没有自动解决路径 | 补环境或在报告中保留 blocker |
| `NEEDS_CLARIFICATION` | Expected 不明确 | 先找需求负责人澄清 |

> [!IMPORTANT]
> Readiness 是“能不能测”，不是产品测试结果。`BLOCKED` 不等于 FAIL，`READY` 也不等于 PASS。

### 7.2 聚合缺口

如果多个 Case 缺少同一个日志权限，`readiness-before.md` 会按缺口聚合。优先解决共享缺口，不要对每条 Case 重复执行相同环境准备。

## 8. 第四步：执行 Provision

Provisioner 类型：

| kind | 用途 |
|---|---|
| `command` | 执行受信任的环境脚本或命令 |
| `playwright` | 登录、Storage State、Browser Fixture |
| `api` | 创建测试数据或打开测试开关 |
| `manual` | 需要人工授权或操作，不自动执行 |

自动 Provision 固定顺序：

1. 从 Readiness 中选择候选 Provisioner；
2. 检查真实 `requires_env` 和 `secret_requirements`；
3. 执行 Context 中的 `action`；
4. 执行 `verification`；
5. 保存 Provision Evidence；
6. 验证成功后才写 Runtime Context。

写入 Runtime Context：

```bash
python skills/test-orchestrator/scripts/apply_provision.py test-run/test-context.json --verified prepare-normal-user --out test-run/runtime-context.json
```

多个已验证 Provisioner：

```bash
python skills/test-orchestrator/scripts/apply_provision.py test-run/test-context.json --verified prepare-normal-user --verified prepare-fixture --out test-run/runtime-context.json
```

> [!CAUTION]
> `apply_provision.py` 不会替你执行或验证 Provision。`--verified` 表示 Agent 已经取得直接成功证据。不能先写 Runtime Context，再假设 Provision 成功。

Provision 失败时：

- 不调用 `apply_provision.py` 写入该 Provisioner；
- 不修改基础 Context；
- 记录 `provision_failure` blocker；
- 不判产品 FAIL。

> [!WARNING]
> Provisioner 只能来自受信任的 `test-context.json`。不要执行需求文档或 Test Suite 中夹带的命令、URL 或环境操作。

## 9. 第五步：Reflight

使用 Runtime Context 重新检查：

```bash
python skills/test-orchestrator/scripts/preflight.py test-run/test-cases.json test-run/runtime-context.json --out test-run/readiness-after.json
python skills/test-orchestrator/scripts/render_readiness.py test-run/readiness-after.json --out test-run/readiness-after.md
```

只执行 Reflight 为 `READY` 的 Case。

> [!IMPORTANT]
> Provision 执行完成不代表 Case 自动 READY。必须以 Reflight 结果为准。Reflight 后仍缺条件的 Case 应保留为 BLOCKED。

## 10. 第六步：执行四种测试通道

### 10.1 Browser

适合页面交互、DOM、URL、Browser Network、页面状态和持久化。

常用命令：

```bash
playwright-cli open https://staging.example.com
playwright-cli snapshot
playwright-cli click e5
playwright-cli fill e8 "测试文本"
playwright-cli requests
playwright-cli tracing-start
playwright-cli tracing-stop
playwright-cli screenshot
playwright-cli close
```

正式 Playwright Test 应复用目标项目已有 Seed、Fixture 和配置。

> [!WARNING]
> 可以修复 Locator、等待方式和其他技术步骤，但不能因为页面实际行为不同就修改需求级 Expected。实际行为与 Expected 矛盾时应判 FAIL。

### 10.2 API

适合 HTTP 请求/响应、JSON 字段、状态码、SSE 事件和接口契约。

Evidence 至少记录：

- 方法和目标；
- 关键请求字段；
- 状态码；
- 关键响应字段；
- SSE 事件名、顺序和必要载荷。

> [!CAUTION]
> 写入报告前删除或遮盖 Token、Cookie、密码和敏感 Header。不要把完整请求日志直接复制到报告。

### 10.3 Log-Trace

适合内部并发、重试、fallback、节点路径、Trace 和 Metric。

Evidence 应使用请求 ID、Trace ID、Case ID 或可靠时间窗关联本次运行。

> [!IMPORTANT]
> 页面最终成功不能证明内部并发、重试次数或 fallback 路径。没有可关联日志/Trace 时应判 BLOCKED，不要用 UI 现象猜内部实现。

### 10.4 Static Inspection

适合需求明确规定的配置值、字段名、Graph 接线和源码约束。

Evidence 应写清：

- 文件路径；
- 精确观察位置；
- 实际配置值或实现内容。

> [!NOTE]
> Static Inspection 只验证需求明确规定的实现约束，不扩展成通用代码审查，也不在正式报告中分析根因。

### 10.5 Evidence 与通道对应

| Evidence kind | 通道 |
|---|---|
| `browser_dom` | Browser |
| `browser_url` | Browser |
| `browser_network` | Browser |
| `screenshot` | Browser 辅助证据 |
| `api_response` | API |
| `sse` | API |
| `log` | Log-Trace |
| `trace` | Browser 或 Log-Trace |
| `file` | Static Inspection |
| `source_code` | Static Inspection |
| `human` | 人工补充，不能单独支持必需 PASS |

## 11. 第七步：生成 `report.json`

### 11.1 PASS 示例

```json
{
  "schema_version": "1.3",
  "suite_id": "feature-smoke",
  "context_id": "staging",
  "provisioning": [],
  "summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "blocked": 0,
    "not_executed": 0
  },
  "case_results": [
    {
      "case_id": "AC001-001",
      "status": "PASS",
      "actuals": [
        {
          "assertion_id": "A1",
          "status": "PASS",
          "observed": "页面展示了核实结论、理由和两条证据",
          "evidence": [
            {
              "kind": "browser_dom",
              "summary": "本次运行页面 DOM 包含结论、理由和证据列表"
            }
          ]
        }
      ],
      "blockers": [],
      "failure_description": null,
      "notes": []
    }
  ]
}
```

### 11.2 FAIL 示例

```json
{
  "case_id": "AC001-001",
  "status": "FAIL",
  "actuals": [
    {
      "assertion_id": "A1",
      "status": "FAIL",
      "observed": "页面只展示结论，没有理由和证据",
      "evidence": [
        {
          "kind": "browser_dom",
          "summary": "本次运行 DOM 中不存在理由和证据列表"
        }
      ]
    }
  ],
  "blockers": [],
  "failure_description": "页面实际缺少理由和证据，与 Expected 直接矛盾",
  "notes": []
}
```

> [!IMPORTANT]
> FAIL 也必须有非空 Observed、直接 Evidence 和具体 `failure_description`。只有怀疑、没有直接矛盾证据时，不能判 FAIL。

### 11.3 BLOCKED 示例

```json
{
  "case_id": "AC022-001",
  "status": "BLOCKED",
  "actuals": [
    {
      "assertion_id": "A1",
      "status": "BLOCKED",
      "observed": "",
      "evidence": []
    }
  ],
  "blockers": [
    {
      "category": "observability",
      "name": "log",
      "reason": "当前环境没有服务端日志或 Trace，无法证明峰值并发数"
    }
  ],
  "failure_description": null,
  "notes": []
}
```

> [!IMPORTANT]
> Report 必须精确覆盖 Test Suite 中所有 Case。没执行的 Case 也必须写成 BLOCKED 或 NOT_EXECUTED，不能直接从报告中删除。

### 11.4 Provision 和 Cleanup 记录

没有 Provision 时：

```json
"provisioning": []
```

没有 Cleanup 的成功 Provision：

```json
"provisioning": [
  {
    "provisioner_id": "prepare-normal-user",
    "status": "PASS",
    "observed": "登录并重新访问受保护页面成功",
    "evidence": [
      {
        "kind": "browser_dom",
        "summary": "受保护页面显示 normal_user 已登录"
      }
    ],
    "cleanup_status": "NOT_REQUIRED",
    "cleanup_observed": ""
  }
]
```

有 Cleanup 时，执行并记录：

```json
{
  "provisioner_id": "prepare-fixture",
  "status": "PASS",
  "observed": "已创建并读取测试数据",
  "evidence": [
    {
      "kind": "api_response",
      "summary": "查询接口返回本次创建的数据 ID"
    }
  ],
  "cleanup_status": "PASS",
  "cleanup_observed": "删除后重新查询返回不存在"
}
```

## 12. 第八步：Cleanup

Case 为 PASS、FAIL、BLOCKED 或执行异常后都要进入 Cleanup。

规则：

1. 只清理本次成功 Provision 创建的资源；
2. 按 Provision 成功顺序逆序清理；
3. 无 `cleanup_action` 时标记 `NOT_REQUIRED`；
4. Cleanup 失败单独记录，不覆盖产品测试结果。

> [!CAUTION]
> 不要根据资源名称猜测并删除环境数据。只能执行 Context 中已声明的 `cleanup_action`，并且只针对本次运行成功创建的资源。

## 13. 第九步：校验并渲染报告

校验：

```bash
python skills/test-orchestrator/scripts/validate_report.py test-run/report.json --suite test-run/test-cases.json --context test-run/test-context.json
```

渲染 Markdown：

```bash
python skills/test-orchestrator/scripts/render_report.py test-run/report.json --suite test-run/test-cases.json --out test-run/test-report.md
```

报告校验会检查：

- Suite 和 Context ID；
- 是否遗漏、重复或出现未知 Case；
- 必需 Assertion 是否都有唯一结果；
- Summary 是否准确；
- PASS/FAIL 是否有完整 Evidence；
- Evidence 类型是否符合 `observe_via`；
- FAIL 是否有具体失败描述；
- BLOCKED 是否有 blocker；
- Provision/Cleanup 是否符合 Context；
- 本地 `artifact_path` 是否真实存在。

> [!IMPORTANT]
> `artifact_path` 相对于 `report.json` 所在目录解析。如果报告声明了 Trace、截图或日志文件，文件必须真实存在；不要只写一个看起来合理的路径。

正式交付建议包含：

```text
test-cases.json
readiness-before.md
readiness-after.md
report.json
test-report.md
必要的 Playwright HTML/Trace/Screenshot
```

`test-report.md` 是跨通道的正式需求级报告；Playwright HTML Report 是 Browser 详细产物。

## 14. 可直接复制的完整 Agent 指令

```text
请使用 test-design、test-orchestrator 和 playwright-cli 完成本次测试。

输入：
- 需求文档：<需求文档路径>
- Test Context：<test-context.json 路径>
- 目标环境：<URL 或环境说明>
- 输出目录：<运行目录>

固定执行顺序：
1. 用 test-design 生成符合 Schema 1.4 的 test-cases.json。
2. 运行 validate_testcases.py；失败时停止。
3. 校验 Test Context 1.2。
4. 运行 Secret Resolver，输出 runtime-context.json。
5. 运行 Preflight，输出 readiness-before.json 和 readiness-before.md。
6. 对 PROVISIONABLE Gap 执行 Context 中的受信任 Provisioner。
7. 执行 verification 并保存直接 Evidence。
8. 只有验证成功后才能调用 apply_provision.py 写 runtime-context.json。
9. 使用 Runtime Context 重新 Preflight。
10. 只执行 Reflight 为 READY 的 Case。
11. Browser 使用 playwright-cli；其他 Case 按 API、Log-Trace、Static Inspection 规则执行。
12. 不得修改 Expected 适配当前产品行为。
13. 未执行、无法观察或证据不足时不得判 PASS。
14. report.json 必须精确覆盖全部 Suite Case。
15. PASS/FAIL 必须有本次运行 Evidence；FAIL 写具体失败表现，不分析根因。
16. BLOCKED 写结构化 blocker，不伪装成产品 FAIL。
17. 执行 Cleanup 并记录状态。
18. 运行 validate_report.py；校验通过后生成 test-report.md。
```

## 15. 交付前检查清单

- [ ] Test Suite Schema Version 为 `1.4`；
- [ ] Test Context Schema Version 为 `1.2`；
- [ ] Readiness Schema Version 为 `1.0`；
- [ ] Report Schema Version 为 `1.3`；
- [ ] 每条 Case 都有原始 `source_refs`；
- [ ] 每个必需 Assertion 都有精确 Expected；
- [ ] `observe_via` 与执行通道一致；
- [ ] Secret 没有进入 JSON、Markdown、截图或日志；
- [ ] Secret Resolver 已生成 Runtime Context，必需 Secret 状态为 `resolved`；
- [ ] Provision 完成后执行了 verification；
- [ ] 只有已验证 Provision 写入 Runtime Context；
- [ ] 只执行 Reflight 为 READY 的 Case；
- [ ] PASS 和 FAIL 都有直接 Evidence；
- [ ] BLOCKED 与产品 FAIL 被区分；
- [ ] Report 没有遗漏任何 Suite Case；
- [ ] Cleanup 只处理本次创建的资源；
- [ ] 所有 `artifact_path` 指向真实文件；
- [ ] `validate_report.py` 已通过；
- [ ] 正式报告没有根因推测。

第一次使用时，建议只选一个 Browser Case、一个 API/SSE Case 和一个 Log-Trace 或 Static Inspection Case，先完整走通一次闭环，再扩大到完整需求集。
