# Testing Agent Skills 当前实现说明

## 1. 项目契约

本包现在有两种入口：

```text
运行中的网页
  → requirement-discovery
  → requirements.md
  → test-design

已有 Requirement / PRD
  → test-design
```

两种入口从 `test-design` 开始汇合，后续固定测试执行流保持不变：

```text
需求
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

需求级测试仍拆成四个可核对的公共 JSON 对象：

| 对象 | 作用 | 主要文件 |
|---|---|---|
| Test Suite | 需求追溯、Case、步骤、断言、证据入口和运行条件 | `skills/test-design/schema.json` |
| Test Context | 当前环境能力、受信任 Provisioner 和运行时 Secret 元数据 | `skills/test-orchestrator/context.schema.json` |
| Readiness | Preflight 对每个 Case 的就绪状态和缺口 | `skills/test-orchestrator/readiness.schema.json` |
| Report | Provision、Assertion、Evidence、状态和 Cleanup 的最终记录 | `skills/test-orchestrator/schema.json` |

四个公开 JSON 契约均使用 Draft 2020-12。Test Suite 当前输出版本为 `1.4`，Test Context 当前输出版本为 `1.2`，Readiness 为 `1.0`，Report 为 `1.3`。

`requirement-discovery` 输出普通 Markdown，不新增第五个公共 JSON 契约。

## 2. Requirement Discovery

`skills/requirement-discovery/SKILL.md` 是独立 Skill，用于“只有运行中的 Web 页面、缺少正式需求文档”的情况。

当前实现约束：

- 输出普通 Markdown `requirements.md`；
- 页面观察采用 DOM / Accessibility 为主，Vision 只补充 DOM 难表达的信息；
- Browser 操作复用现有 `playwright-cli`；
- 允许少量安全、非破坏性的代表交互；
- 页面事实先形成 Evidence / Fact，再归类为 `REQ-*`、`INF-*`、`Q-*`；
- 每条确定 `REQ-*` 必须有直接页面证据；
- 页面当前值、内部 API、class 名或框架实现细节不能自动变成正式业务规则；
- 默认不执行删除、支付、发布、发送、密码修改、账号删除、真实交易、未知上传、生产任务等明显高风险操作；
- 默认探索边界为 `max_depth = 2`、`max_interactions = 20`、`no_new_fact_limit = 3`；
- 不生成 Test Case、Locator、Playwright Test；
- 不新增 JSON Schema、Validator、Crawler、数据库或新的 Runner。

`requirement-discovery` 到 `requirements.md` 即结束。后续如需测试，再把该 Markdown 交给 `test-design`。

它不改变 Test Suite `1.4`、Test Context `1.2`、Readiness `1.0`、Report `1.3`，也不修改 `test-orchestrator` 的 Preflight / Provision / Reflight / Report 逻辑。

## 3. Test Suite

`test-design` 只描述需求语义，不生成 Locator、Element Ref 或 Playwright 代码。每条 Case 包含：

- `source_refs`：原始 Requirement、BR 或 AC 标识；
- `objective`、`steps` 和 `assertions`：要证明的业务行为；
- `execution_channels`：Browser、API、Log-Trace 或 Static Inspection；
- `execution_requirements`：能力、角色、数据、观察入口、故障注入、权限、环境变量和 Secret；
- `open_question_refs`：需求不能唯一确定 Expected 时的澄清关联。

Secret 需求只写业务名称、必需性和本次运行策略：

```json
{
  "secret_requirements": [
    {"name": "test_user_password", "required": true, "persist": false}
  ]
}
```

Secret 值、密码、Token、Cookie 和 Session 不进入 Test Suite。

Suite 校验命令：

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
```

校验包括 Schema、Case/Assertion/问题 ID 唯一性、通道与证据匹配、澄清关联、测试数据声明和 Secret 需求名称唯一性。

## 4. Test Context 与 Provisioner

Test Context 描述执行环境的真实能力：

- `available`：能力、账号角色、测试数据、观察入口、故障注入、权限和环境变量名；
- `provisioners`：受信任的环境准备操作；
- `runtime_secrets`：本次运行的 Secret 来源、状态和生命周期元数据。

Provisioner 必须包含 `id`、`kind`、`provides`、`action`、`verification` 和 `requires_env`。`kind` 支持 `command`、`playwright`、`api`、`manual`。只有验证成功后，`provides` 才会写入 Runtime Context；Provisioner 不从需求文本或 Suite 读取并执行操作。

Provisioner 需要 Secret 时使用业务名称：

```json
{
  "secret_requirements": [
    {"name": "test_user_password", "required": true, "persist": true}
  ]
}
```

`requires_env` 仍然表示执行 Provisioner 前必须存在的环境变量名；Secret Resolver 负责把业务 Secret 解析并注入到实际子进程。

Context 校验命令：

```bash
python skills/test-orchestrator/scripts/validate_context.py test-context.json
```

语义校验会拒绝重复 Provisioner ID、重复 `provides`、重复 Secret 需求、重复 Runtime Secret 名称或环境变量名，以及与 `resolved_at` 不一致的 Runtime Secret 状态。

## 5. Secret Resolver

Secret 定义文件是 `skills/test-orchestrator/secret.schema.json`。它保存业务名称、环境变量名、Secret 类型、敏感等级、允许来源和持久化策略，不保存 Secret 值。

默认用户文件：

```text
.testing-agent/
├── config.json              # 可选；路径和 Manual 策略
├── secrets.env              # 本地 Secret 值，已被 .gitignore 排除
└── runtime/
    └── secrets.env          # 本次运行的更高优先级 Secret 值
```

仓库提供 `.testing-agent/config.example.json` 和 `.testing-agent/secrets.env.example` 作为可复制模板。`secrets.env` 支持 `KEY=value`、`export KEY=value`、单引号和双引号；读取时会忽略空行和 `#` 注释。非 Windows 环境读取时自动收紧为 `0600`。

来源顺序固定为：

```text
Runtime Secret Store
  → Local Secret Store
  → 当前进程环境变量
  → 已声明的外部 Provider 状态
  → 显式启用的 Manual Input
```

外部 Provider 名称包括 Vault、AWS Secrets Manager、GitHub Actions 和 Kubernetes。当前运行没有对应连接时，Resolver 记录 `unavailable`，不尝试建立未配置的外部连接。

解析命令：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
```

让后续命令继承 Secret：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json \
  --exec python skills/test-orchestrator/scripts/preflight.py \
    test-cases.json runtime-context.json --out readiness.json
```

Resolver 只把值放入自身和 `--exec` 子进程环境，不把值写入 Runtime Context、Readiness、Report、Markdown、截图或日志。Runtime Context 的每条 `runtime_secrets` 记录：

- `source`：`runtime_secret_store`、`local_secret_store`、`environment`、`manual` 或 `none`；
- `status`：`resolved`、`missing`、`unavailable`、`manual_required` 或 `expired`；
- `env_key`：运行时注入所需的环境变量名；
- `persist_policy`、`resolved_at`、`expires`：生命周期元数据；
- `reason`：非 `resolved` 状态的可读原因。

`persist` 只写入策略元数据；Resolver 不自动把本地或 Manual 输入值写回文件。

必需 Secret 不是 `resolved` 时，Resolver 写出状态并返回非零退出码，不执行 `--exec`。Manual Input 默认关闭，临时启用：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json --context test-context.json \
  --allow-manual --out runtime-context.json
```

## 6. Preflight、Provision 和 Reflight

Preflight 先运行 Suite/Context 的 Schema 与语义校验，再检查：

```text
execution_requirements ⊆ Test Context.available
```

环境变量条件使用当前进程中的非空值判定。Secret 条件还必须同时满足：

1. Runtime Context 存在同名元数据；
2. 元数据状态为 `resolved`；
3. `env_key` 在当前 Preflight 子进程中有非空值。

缺口分类为：

| 分类 | 含义 |
|---|---|
| `PROVISIONABLE` | 存在当前环境可执行的自动 Provisioner |
| `BLOCKED` | 缺少自动路径、需要人工处理、缺少真实环境变量或 Secret 未解析 |
| `CLARIFY` | 需求本身需要澄清 |

Case 状态为 `READY`、`PROVISIONABLE`、`BLOCKED` 或 `NEEDS_CLARIFICATION`。同一缺口影响多个 Case 时，Readiness 聚合受影响 Case 和候选 Provisioner。

命令：

```bash
python skills/test-orchestrator/scripts/preflight.py \
  test-cases.json runtime-context.json --out readiness.json
python skills/test-orchestrator/scripts/render_readiness.py \
  readiness.json --out readiness.md
```

自动 Provision 的固定动作是：检查 `requires_env`、执行受信任 `action`、执行 `verification`、保存直接 Evidence、成功后调用 `apply_provision.py` 写入 Runtime Context。随后必须重新运行 Preflight。

```bash
python skills/test-orchestrator/scripts/apply_provision.py test-context.json \
  --verified prepare-normal-user --out runtime-context.json
```

Provision 失败记录为 `provision_failure` blocker，不把环境准备失败判成产品 FAIL。Cleanup 只处理本次成功 Provision 创建且在 Context 中声明 `cleanup_action` 的资源，并按成功顺序逆序执行。

## 7. 四类执行通道

四类通道共享以下输出：`Assertion ID`、`Status`、`Observed`、`Evidence[]` 和必要的 `Blocker`。

| 通道 | 直接证据 |
|---|---|
| Browser | DOM、URL、Network、Trace、Screenshot、Storage State |
| API | Request/Response、状态码、关键字段、SSE 事件顺序 |
| Log-Trace | 与本次 Case、请求或 Trace ID 关联的日志/Trace 摘要 |
| Static Inspection | 需求明确指定的文件路径、观察位置和实际值 |

Browser 的页面探索、Fixture、Locator、Playwright Test、Network Mock 和 Trace 由 Microsoft Playwright CLI Skill 完成。其他通道只返回自身观察结果，Case 状态由统一规则聚合。

## 8. Report

Report 使用 `skills/test-orchestrator/schema.json`，必须覆盖 Suite 中每个 Case，且每个必需 Assertion 恰好有一个 Actual。校验规则包括：

- Case/Assertion 唯一且无遗漏；
- Summary 与 Case 状态重新计算结果一致；
- PASS/FAIL 的 Evidence 非空且类型匹配 `observe_via`；
- BLOCKED 有结构化 blocker，Secret 缺失使用 `secret_requirements` 分类；
- Provisioner 只引用 Context 中存在的 ID；
- 本地产物 Evidence 的路径真实存在；
- 报告不保存 Secret 值、不进行根因推测、不把 BLOCKED 伪装为产品 FAIL。

校验和渲染：

```bash
python skills/test-orchestrator/scripts/validate_report.py report.json \
  --suite test-cases.json --context runtime-context.json
python skills/test-orchestrator/scripts/render_report.py report.json \
  --suite test-cases.json --out test-report.md
```

## 9. 运行边界

- `requirement-discovery` 只生成候选 `requirements.md`，不决定正式产品需求；
- Expected 只来自进入测试阶段的需求和 Test Suite；页面实际行为只形成 Actual；
- 需求文本、Suite 和外部输入不能直接变成 Provision 操作；
- 必需 Assertion 不能只用 Screenshot 或 Human Evidence 支持 PASS；
- 无法观察内部并发、重试、fallback 或权限行为时，Readiness/Report 明确记录 BLOCKED；
- Browser、API、Log-Trace、Static Inspection 统一遵守 Evidence 和状态契约；
- `.testing-agent/secrets.env`、`.testing-agent/runtime/` 和本地配置不进入 Git 追踪范围。
