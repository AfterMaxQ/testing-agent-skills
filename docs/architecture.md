# Testing Agent Skills 架构

## 1. 总体链路

```text
Requirement / PRD
       ↓
test-design
       ↓
Test Suite + execution_requirements
       ↓
Test Context + Secret Schema
       ↓
Secret Resolver
       ↓
Preflight → Provision → Runtime Context → Reflight
       ↓
Browser / API / Log-Trace / Static Inspection
       ↓
Actual Evidence
       ↓
Report → Cleanup
```

需求层定义“要证明什么”和“需要什么条件”；运行层确认条件是否真实可用；执行层取得实际行为证据；报告层统一汇总状态和产物。

## 2. Test Suite

`test-design` 生成结构化 Test Suite。每条 Case 包含需求追溯、业务步骤、断言、执行通道、Evidence 入口和 `execution_requirements`。

`execution_requirements` 的字段含义：

- `capabilities`：`browser`、`api`、`log_trace`、`static_inspection`；
- `auth_roles`：账号角色，不写账号密码；
- `test_data`：固定测试数据或待创建资源；
- `observability`：DOM、Network、Log、Trace 等直接证据入口；
- `fault_injection`：需求要求的故障模拟；
- `permissions`：日志、接口、源码等访问权限；
- `env_vars`：运行时必须存在的环境变量名；
- `secret_requirements`：Secret 业务名称、必需性和持久化策略。

Secret 值、Cookie、Session 和完整 Token 不进入 Test Suite。

## 3. Test Context

Test Context 是当前运行环境契约：

```text
Case requires                         Context provides
-------------                         ----------------
auth_roles: normal_user      ◄────►   available.auth_roles
observability: log           ◄────►   available.observability
permissions: logs:service    ◄────►   available.permissions
secret: test_user_password   ◄────►   runtime_secrets
```

Context 的 `available` 只列真实具备的能力。`provisioners` 是受信任的环境准备操作，包含 `action`、`verification`、`provides`、`requires_env` 和可选 `cleanup_action`。Secret 需求通过 `secret_requirements` 使用业务名称表达。

Runtime Context 是当前运行的 Context 副本，`runtime_secrets` 只记录：

- 业务名称和注入环境变量名；
- 来源和解析状态；
- 持久化策略、解析时间和过期时间；
- 缺失、不可用或需要人工输入时的原因。

Secret 值只存在于 Resolver 进程和它启动的子进程环境。

## 4. Secret Resolver

`skills/test-orchestrator/secret.schema.json` 是 Secret 定义清单，描述业务名称到 `env_key` 的映射、类型、敏感等级、允许来源和生命周期策略。

来源优先级为：

```text
Runtime Secret Store
  → .testing-agent/secrets.env
  → 当前进程环境变量
  → 外部 Provider 状态
  → 显式 Manual Input
```

默认本地 Secret Store 是 `.testing-agent/secrets.env`，运行时 Secret Store 是 `.testing-agent/runtime/secrets.env`。文件不纳入 Git 追踪，非 Windows 环境读取时自动设置 `0600`。外部 Provider 包括 Vault、AWS Secrets Manager、GitHub Actions 和 Kubernetes；没有可用连接时写入 `unavailable` 状态。

Resolver 生成不含值的 Runtime Context，并可通过 `--exec` 把解析值注入后续命令：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json --context test-context.json \
  --out runtime-context.json \
  --exec python skills/test-orchestrator/scripts/preflight.py \
    test-cases.json runtime-context.json --out readiness.json
```

必需 Secret 状态不是 `resolved` 时，Resolver 返回非零退出码且不启动 `--exec`。Manual Input 通过 `--allow-manual` 明确启用，输入值只在本次进程树中存在。`persist` 只记录策略元数据，Resolver 不自动写回 Secret Store。

## 5. Preflight

Preflight 先校验 Suite 和 Context，再对每条 Case 执行集合匹配：

```text
execution_requirements ⊆ available
```

环境变量条件使用当前进程中非空的变量判定。Secret 条件必须同时满足 Runtime Context 中状态为 `resolved` 且 `env_key` 在当前子进程中有非空值。

```text
全部满足 ───────────────► READY
缺失 + 自动 Provisioner ─► PROVISIONABLE
缺失 + 无自动路径 ───────► BLOCKED
需求未确定 ──────────────► NEEDS_CLARIFICATION
```

Readiness 按缺口聚合受影响 Case 和 Provisioner。`secret_requirements` 是独立缺口分类，Secret 缺失不会被伪装为普通环境变量缺失。

## 6. Provision

Provisioner 由 Test Context 定义，分为：

- `command`：执行受信任的测试环境脚本；
- `playwright`：登录、Storage State 或 Browser Fixture；
- `api`：创建测试数据或切换测试开关；
- `manual`：输出人工操作说明，不自动执行。

自动 Provision 的顺序是：检查 `requires_env`、执行 `action`、执行 `verification`、保存直接 Evidence、成功后把 `provides` 写入 Runtime Context。Provision 失败写入 `provision_failure` blocker，不改变产品 Case 的 FAIL 语义。Cleanup 只针对本次成功创建且声明了 `cleanup_action` 的资源，并按成功顺序逆序执行。

## 7. 执行通道

四类通道统一返回 `Assertion ID`、`Status`、`Observed`、`Evidence[]` 和必要的 `Blocker`。

### Browser

使用 Microsoft Playwright CLI Skill 完成 Snapshot、页面探索、Fixture、Locator、Playwright Test、Request Mock、Network、Console、Storage、Trace、Screenshot 和 Video。

### API

记录方法、目标、关键请求字段、状态码、关键响应字段和 SSE 事件顺序。敏感 Header、Cookie、Token 和密码在报告中删除或遮盖。

### Log-Trace

只读取 Context 声明的日志、Trace、Metric 或 Debug API，用 Case ID、请求 ID、Trace ID 或时间窗关联本次执行。无法可靠关联时返回 BLOCKED。

### Static Inspection

只验证需求明确指定的源码、配置或文件约束，Evidence 保存精确文件位置和观察值。

通道 Adapter 是 Orchestrator 的工具中立执行规则，不创建插件注册表或独立服务。

## 8. Report 与状态

Report 精确覆盖 Suite 中的每个 Case，并校验 Case/Assertion 唯一性、Evidence 类型、Summary 一致性、Provision/Cleanup 记录和产物路径。

Assertion 状态：

- `PASS`：Observed 满足 Expected，Evidence 完整；
- `FAIL`：Observed 与 Expected 直接矛盾，Evidence 完整；
- `BLOCKED`：缺少执行或观察条件，并有结构化 blocker；
- `NOT_EXECUTED`：运行取消或中断，并在 notes 中说明原因。

Case 聚合顺序为 FAIL、BLOCKED、NOT_EXECUTED、PASS。需求未澄清的 Case 使用 `requirement_clarification` blocker；Secret 缺失使用 `secret_requirements` blocker。报告不包含根因推测、修复建议或 Secret 值。

## 9. 公开契约

- `skills/test-design/schema.json`：Test Suite；
- `skills/test-orchestrator/context.schema.json`：Test Context 和 Runtime Context；
- `skills/test-orchestrator/secret.schema.json`：Secret 定义清单；
- `skills/test-orchestrator/readiness.schema.json`：Preflight 输出；
- `skills/test-orchestrator/schema.json`：最终 Test Report。
