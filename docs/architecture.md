# Testing Agent Skills 架构设计

## 1. 目标

测试流程分为测试语义、运行环境、执行能力三部分：

```text
Requirement
   ↓
test-design
   ↓
Test Suite + execution_requirements
   ↓
Test Context
   ↓
Preflight → Provision → Runtime Context → Reflight
   ↓
test-orchestrator
   ↓
Browser / API / Log-Trace / Static
   ↓
Evidence
   ↓
Report
```

需求层定义“要证明什么”和“需要什么条件”；运行层确认“当前环境是否具备这些条件”；执行层取得“实际发生了什么”的证据。

## 2. test-design

`test-design` 输出结构化 Test Suite。每条 Case 包含需求追溯、业务步骤、断言、执行通道以及 `execution_requirements`。

`execution_requirements` 分为：

- `capabilities`：Browser、API、Log-Trace、Static Inspection；
- `auth_roles`：账号角色；
- `test_data`：固定测试数据或待创建数据；
- `observability`：DOM、Network、Log、Trace 等证据入口；
- `fault_injection`：需要模拟的故障；
- `permissions`：日志、接口、源码等访问权限；
- `env_vars`：运行依赖的环境变量名。

需求存在冲突或无法唯一确定预期时，记录 `open_questions`，Case 标记为 `NEEDS_CLARIFICATION`，并通过 `open_question_refs` 关联问题。

## 3. Test Context

Test Context 是运行环境契约。它描述当前环境已经具备的条件以及受信任的 Provisioner。

```text
Case requires                         Context provides
-------------                         ----------------
auth_roles: normal_user      ◄────►   available.auth_roles
observability: log           ◄────►   available.observability
permissions: logs:service    ◄────►   available.permissions
```

敏感值不进入 Test Context。密码和 Token 通过环境变量、Secret Manager 或 Playwright storage state 管理。

## 4. Preflight

Preflight 在测试执行前完成集合匹配：

`execution_requirements ⊆ available`

缺失项再检查 Context 中是否存在 Provisioner。

```text
全部满足 ───────────────► READY
缺失 + 自动 Provisioner ─► PROVISIONABLE
缺失 + 无自动路径 ───────► BLOCKED
需求未确定 ──────────────► NEEDS_CLARIFICATION
```

Preflight 生成聚合 Readiness Report。同一个日志权限影响 10 条 Case 时，只需要在环境准备阶段处理一次。

## 5. Provision

Provisioner 由 Test Context 定义，不能由需求文本动态生成并执行。

支持四种类型：

- `command`：测试环境脚本；
- `playwright`：登录、storage state 等 Browser 准备；
- `api`：创建测试数据、切换测试开关；
- `manual`：人工授权或环境变更。

自动 Provisioner 必须声明 `action`、`verification`、`provides`、`requires_env` 和可选 `cleanup_action`。只有 `verification` 产生直接证据后，`provides` 才能写入本次 Runtime Context。Runtime Context 继续使用 Test Context Schema，不增加新的公开契约。

写回后使用 Runtime Context 重新运行 Preflight。Provision 失败记录为 `provision_failure`，不判产品 FAIL；Reflight 后仍不满足的 Case 才进入最终 `BLOCKED`。

## 6. test-orchestrator

Orchestrator 负责：

1. 校验 Test Suite 和 Test Context；
2. Preflight；
3. 执行并验证可用 Provisioner；
4. 写入 Runtime Context 并再次 Preflight；
5. 路由 READY Case；
6. 收集 Actual Evidence；
7. 统一判定并生成完整覆盖 Suite 的 Report；
8. 逆序清理由本次成功 Provision 创建的资源，并记录 Cleanup 状态。

Orchestrator 不修改 Expected，也不重新设计 Case。

## 7. Browser 执行

Browser 侧使用 Microsoft 官方 Playwright CLI Skill。

以下能力由 Playwright 负责：

- Snapshot、页面探索和 Locator；
- Seed / Fixture / Session；
- Playwright Test 生成与执行；
- Request Mock 和网络故障模拟；
- Network、Console、Storage；
- Trace、Screenshot、Video。

因此 Browser 自带的 Trace、Network、Request Mock 等不应重复作为外部测试基础设施实现。

## 8. 非 Browser 可测试性

对于内部并发、重试、fallback 等要求，如果没有 Log、Trace、Metric 或 Debug API，就无法稳定验收。这类缺失会在 Preflight 中明确暴露为测试环境缺口。

需要时应向测试环境补充可观察性，例如：

- staging 日志访问；
- trace 字段；
- 测试指标；
- test-only debug endpoint；
- 可控 fault injection。

测试系统不通过 UI 现象猜测不可观察的内部实现。

API、Log-Trace 和 Static Inspection 使用与 Browser 相同的 Assertion 输出协议：Status、Observed、Evidence 和可选 Blocker。Adapter 是 Orchestrator 的工具中立执行规则，不建设插件注册表或独立服务。

## 9. 数据契约

- `test-design/schema.json`：Test Suite；
- `test-orchestrator/context.schema.json`：Test Context；
- `test-orchestrator/readiness.schema.json`：Preflight 输出；
- `test-orchestrator/schema.json`：最终 Test Report。

Runtime Context 是 Test Context 的本次运行副本，继续由 `context.schema.json` 校验。Test Report 同时记录 Provision 和 Cleanup，避免增加独立 Run State Schema。

这些协议不包含临时 Browser Element Ref、Session ID 或 Secret 值。
