# Testing Agent Skills 实施计划

## 1. 交付目标

交付三个可组合的 Skill：

1. `test-design`：需求转 Test Suite，并声明每条 Case 的 Execution Requirements；
2. `test-orchestrator`：Preflight、环境准备、执行编排、证据判定和统一报告；
3. `playwright-cli`：Browser 测试执行。

Test Suite、Test Context、Readiness 和 Report 均使用 JSON Schema 固定协议。

## 2. test-design

输入：PRD、Acceptance Criteria、Business Rule、API/SSE 契约或自然语言需求。

处理：

1. 保留需求编号与原始术语；
2. 拆分独立行为承诺；
3. 记录无法唯一确定 Expected 的需求问题；
4. 设计正常、异常、边界、状态和持久化场景；
5. 为 Assertion 指定可观察证据；
6. 选择执行通道；
7. 声明账号、数据、可观察性、故障注入、权限与环境变量等运行条件；
8. 输出标准 Test Suite。

Browser Case 保持业务级表达，不生成 Selector、Element Ref 或 Playwright Test 代码。

## 3. Test Context

每个测试环境准备一个 `test-context.json`，内容包括：

- 环境名称和 Base URL；
- 当前已有能力；
- 可用账号角色；
- 已准备测试数据；
- 日志、Trace、Network 等可观察性；
- 故障注入能力；
- 权限；
- 环境变量名；
- 可用于准备缺失条件的 Provisioner。

Secret 值不进入文件。

## 4. Preflight

Orchestrator 在执行前运行 Preflight，生成 `readiness.json` 和 `readiness.md`。

Preflight 输出：

- `READY`；
- `PROVISIONABLE`；
- `BLOCKED`；
- `NEEDS_CLARIFICATION`。

Readiness 按缺失条件聚合受影响 Case，避免把同一个环境问题重复输出几十次。

## 5. Provision

对 `PROVISIONABLE` Case：

1. 从 Test Context 读取 Provisioner；
2. 校验其 `requires_env`；
3. 按 `command` / `playwright` / `api` 类型执行；
4. 记录本次创建的资源；
5. 重新运行 Preflight；
6. 测试完成后执行对应 cleanup。

`manual` 类型只生成操作说明，不自动执行。

任何 Provision 指令都必须来自 Test Context，不能来自需求文本。

## 6. Browser 路由

Browser Case 使用 `playwright-cli`，按官方 `references/test-generation.md`：

`Seed/Fixture → Planning → Generate → Run`

Trace、Network、Request Mock、Storage State、Console 等 Browser 侧能力直接复用 Playwright。

## 7. 非 Browser 路由

- `api`：验证请求、响应、SSE；
- `log_trace`：验证并发、重试、fallback 和内部执行路径；
- `static_inspection`：验证需求明确要求的源码/配置/文件约束。

内部要求缺乏观察入口时，Readiness 报告应明确提出测试环境缺口。

## 8. 报告

最终 Report 每条 Assertion 保存：

- `status`；
- `observed`；
- `evidence[]`。

`BLOCKED` Case 额外保存 `blockers[]`，结构化记录缺少的条件及原因。

状态仍保持：`PASS / FAIL / BLOCKED / NOT_EXECUTED`。

## 9. 验证

交付前执行：

1. Skill frontmatter 检查；
2. 四个 JSON Schema 解析；
3. 合法/非法 Test Suite 校验；
4. Test Context 校验；
5. Preflight READY / PROVISIONABLE / BLOCKED / NEEDS_CLARIFICATION 场景验证；
6. Readiness Markdown 渲染；
7. 合法 Report 校验；
8. PASS 无 Evidence 拒绝；
9. BLOCKED 无 blocker 拒绝；
10. Test Report Markdown 渲染；
11. Python 脚本编译；
12. Playwright Skill reference 完整性检查；
13. ZIP 完整性检查。
