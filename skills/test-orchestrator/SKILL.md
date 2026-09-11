---
name: test-orchestrator
description: Use when 需要执行结构化测试套件、准备测试运行条件、路由 Browser/API/日志/源码检查，并把本次运行证据汇总为统一测试报告时。
---

# 测试执行编排

## 目标

执行固定链路：

`Test Suite + Test Context → Secret Resolution → Preflight → Provision → Runtime Context → Reflight → Execute → Evidence / Progress Checkpoint → Report → Cleanup`

Expected 只来自原始需求和 Test Suite。产品实际行为只能形成 Actual，不得为了让测试通过而修改 Expected。

## 1. 输入

必须提供：

- `test-cases.json`：符合 `test-design/schema.json`；
- `test-context.json`：符合 `context.schema.json`；
- 可访问的目标环境或源码范围；
- Context 所声明的账号、权限、环境变量和观察入口。

Test Context 只保存能力名称、资源引用、Secret 运行元数据和受信任 Provisioner，不保存密码、Token 或 Session 值。Skill 使用工具中立的契约，不依赖 Codex、Trae 或某个 Agent 的专有工具名。

## 2. Secret Resolution

Case 和 Provisioner 使用 `secret_requirements` 声明 Secret 业务名称、必需性和持久化策略。Secret 定义位于 `secret.schema.json`，只保存业务名称到环境变量名的映射和允许来源。

Resolver 按以下顺序寻找值：Runtime Secret Store、`.testing-agent/secrets.env`、当前进程环境变量、已声明的外部 Provider、显式启用的 Manual Input。值只进入 Resolver 及其 `--exec` 子进程环境，不写入 Suite、Context、Readiness、Report 或日志。

```bash
python scripts/resolve_secret.py \
  --schema secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json \
  --exec python scripts/preflight.py test-cases.json runtime-context.json --out readiness.json
```

Runtime Context 的 `runtime_secrets` 只记录 `source`、`status`、`resolved_at`、`expires` 和持久化策略。必需 Secret 不是 `resolved`，Resolver 返回非零状态且不执行 `--exec`；外部 Provider 没有可用连接时记录 `unavailable`；Manual Input 需要 `--allow-manual`。

## 3. Preflight

执行：

```bash
python scripts/validate_context.py test-context.json
python scripts/resolve_secret.py --schema secret.schema.json --suite test-cases.json --context test-context.json --out runtime-context.json
python scripts/preflight.py test-cases.json runtime-context.json --out readiness-before.json
python scripts/render_readiness.py readiness-before.json --out readiness-before.md
```

Preflight 同时执行 Schema 和语义校验，并比较：

`Case.execution_requirements ⊆ Test Context.available`

状态：

- `READY`：当前可直接执行；
- `PROVISIONABLE`：缺失条件存在可自动执行的 Provisioner；
- `BLOCKED`：没有自动解决路径、只有人工路径或 Provisioner 缺少真实环境变量；
- `NEEDS_CLARIFICATION`：Expected 尚不能唯一确定。

Provision 决策按 Gap 进行。即使某个 Case 总状态为 BLOCKED，其中可自动准备且能服务其他 Case 的 Gap 仍进入 Provision 处理。

## 4. Provision

Provisioner 只能来自受信任的 Test Context：

| kind | 执行方式 |
|---|---|
| `command` | 使用当前终端执行 Context 声明的受信任脚本或命令 |
| `playwright` | 使用 Playwright 准备登录状态、Storage State 或 Browser Fixture |
| `api` | 使用已有 HTTP 能力调用 Context 声明的测试 API |
| `manual` | 输出人工操作说明，不自动执行 |

自动 Provision 固定执行：

1. 按 Readiness Gap 去重 Provisioner；
2. 同一 Gap 只选择 Context 声明顺序中的第一个可执行候选；
3. 使用当前进程实际环境变量检查 `requires_env`；
4. 执行 `action`；
5. 执行 `verification` 并保存直接 Evidence；
6. 只有验证成功后，才允许将 `provides` 写入 Runtime Context；
7. 在 Report 的 `provisioning` 中记录状态、Evidence 和 Cleanup 状态。

写回 Runtime Context：

```bash
python scripts/apply_provision.py test-context.json \
  --verified <provisioner-id> \
  --out runtime-context.json
```

多个 Provisioner 重复传入 `--verified`。该命令只负责合并已经验证成功的 `provides`，不负责执行或推测 Provision 是否成功。

Provision 失败时：

- 不更新 Runtime Context；
- 记录 `provision_failure` blocker；
- 不判产品 FAIL。

## 5. Reflight

Provision 后必须重新执行：

```bash
python scripts/preflight.py test-cases.json runtime-context.json --out readiness-after.json
python scripts/render_readiness.py readiness-after.json --out readiness-after.md
```

只有 Reflight 为 READY 的 Case 才进入执行。Reflight 后的 BLOCKED 和 NEEDS_CLARIFICATION Case 直接生成对应 Assertion 的 BLOCKED Actual，不编造执行记录。

## 6. 通道执行

每个通道返回相同结构：Assertion ID、Status、Observed、Evidence，无法执行时返回 Blocker。

### 6.1 执行进度 Checkpoint

正式执行开始时创建 `.testing-agent/execution-progress.json`。它只保存本次运行的进度摘要，不属于 Report 1.3，也不替代最终 `report.json`。

初始化：

```bash
python scripts/update_progress.py .testing-agent/execution-progress.json init \
  --suite-id <suite_id> \
  --context-id <context_id> \
  --total <case_count>
```

每个 Case 开始处理时立即记录 `current_case`；Reflight 后直接形成 BLOCKED 结果的 Case 也按同样方式先记录当前 Case，再写入终态 checkpoint：

```bash
python scripts/update_progress.py .testing-agent/execution-progress.json start-case \
  --case <case_id>
```

每个 Case 得到 `PASS`、`FAIL`、`BLOCKED` 或 `NOT_EXECUTED` 终态后立即写入 checkpoint，并保存本次 Case 已生成的 Evidence 路径；`--evidence` 可以重复传入：

```bash
python scripts/update_progress.py .testing-agent/execution-progress.json finish-case \
  --case <case_id> \
  --status <status> \
  --evidence <artifact_path>
```

`FAIL` 时可同时传入 `--failure-description`。进度文件通过同目录临时文件加原子替换写入，避免中断时留下半写 JSON。它记录 `total`、`completed`、`passed`、`failed`、`blocked`、`not_executed`、当前 Case 和已完成 Case 摘要。

全部 Case 都得到终态后，仍按第 8 节生成、校验并渲染正式报告；成功完成这些步骤后再执行：

```bash
python scripts/update_progress.py .testing-agent/execution-progress.json complete
```

`complete` 只在 `completed == total` 且没有正在执行的 Case 时成功。不提供自动 Resume；测试进程异常终止时，最后一次成功写入的 checkpoint 保留为运行状态证据。

### 6.2 Browser

**REQUIRED SUB-SKILL:** Use `playwright-cli`。

使用 Playwright 完成 Seed/Fixture、页面探索、Locator、Test 生成和执行。DOM、URL、Network、Trace、Screenshot 和 Storage State 均复用 Playwright。

调用 `playwright-cli/references/test-generation.md` 时遵守本 Skill 的验收边界：

- 可以修复 Locator、等待方式和其他技术步骤；
- 不得把实际页面当作需求事实来源；
- 页面行为与 Expected 不一致时记录 Actual 并判 FAIL；
- 只有用户确认需求变更后才能更新 Test Suite Expected。

Browser Case 的 Screenshot 既可以是 Assertion 计划中的 Evidence，也可以作为方便人类审阅的补充 Evidence。补充截图不改变 Assertion 的 `observe_via`，也不能替代必需的 DOM、URL、Network、Log 或其他计划证据。

对有明确视觉状态的 Browser Case，优先保存少量代表性截图，并把最能说明结果的截图排在该 Case 的 screenshot Evidence 前面：

- `FAIL`：优先保留 1–2 张能直接说明 Expected 与 Actual 差异的截图；
- `BLOCKED`：登录、权限、错误页、不可用状态等能由页面直接说明时保留 1 张；
- `PASS`：截图确实能帮助人工快速确认最终 UI 状态时最多保留 1 张代表图；
- `NOT_EXECUTED`：不为了报告展示额外截图。

不要为了“报告好看”对每一步都截图。额外截图只有在能帮助人工理解结果时才采集。

### 6.3 API

- 使用当前已有 HTTP 工具、CLI 或项目测试入口；
- Evidence 记录方法、目标、关键请求字段、状态码和关键响应字段；
- SSE Evidence 记录事件名称、顺序和必要载荷；
- 删除或遮盖密码、Token、Cookie 和敏感 Header；
- 无 API 入口或权限时返回 BLOCKED。

### 6.4 Log-Trace

- 只读取 Test Context 声明的日志、Trace、Metric 或 Debug API；
- 使用请求 ID、Trace ID、Case ID 或可靠时间窗关联本次执行；
- Evidence 只保存直接支持 Assertion 的最小日志/Trace 摘要和产物路径；
- 无法可靠关联时返回 BLOCKED，不用 UI 现象推测内部并发、重试或 fallback。

### 6.5 Static Inspection

- 只验证需求明确规定的源码、配置或文件约束；
- 只读取当前公开仓库或用户明确授权的范围；
- Evidence 保存文件路径、观察位置和实际值；
- 不扩展为通用代码审查或根因分析。

### 6.6 多通道

Case 声明的所有 `observe_via` 都是计划采集的证据。按 Assertion 路由对应通道，通道只返回自身观察结果，最终状态由统一规则聚合。

## 7. Assertion 与 Case 判定

Assertion：

- `PASS`：Observed 满足 Expected，Observed 非空且本次 Evidence 完整；
- `FAIL`：Observed 与 Expected 直接矛盾，Observed 非空且本次 Evidence 完整；
- `BLOCKED`：缺少执行或观察条件，并有结构化 blocker；
- `NOT_EXECUTED`：运行被取消或中断，并写明原因。

Case 只按必需 Assertion 聚合：

1. 有 FAIL → FAIL；
2. 否则有 BLOCKED → BLOCKED；
3. 否则有 NOT_EXECUTED → NOT_EXECUTED；
4. 其余全部 PASS → PASS。

Case 同时存在 FAIL 和 BLOCKED Assertion 时，Case 为 FAIL，但必须保留 blockers。`NEEDS_CLARIFICATION` Case 在最终 Report 中映射为 BLOCKED，并使用 `requirement_clarification` blocker。

## 8. Report

`report.json` 必须：

- 使用 Report Schema `1.3`；
- 包含 `provisioning`；
- 精确覆盖 Suite 中每个 Case；
- 每个必需 Assertion 恰好有一个 Actual；
- 不包含未知或重复 Case/Assertion；
- PASS/FAIL 的 Evidence 类型完整覆盖 Assertion 的 `observe_via`；
- FAIL 写明具体 `failure_description`；
- BLOCKED 写明结构化 blocker；
- 不包含根因推测和修复建议。

`execution-progress.json` 只用于执行中 checkpoint，因此不要求提前覆盖整个 Suite；最终正式结果仍只由完整 `report.json` 表达。

执行：

```bash
python scripts/validate_report.py report.json \
  --suite test-cases.json \
  --context test-context.json
python scripts/render_report.py report.json \
  --suite test-cases.json \
  --out test-report.md
```

`test-report.md` 使用面向人工审阅的混合报告结构：

1. 测试结果总览表；
2. Case 总览表，直接显示状态和核心结果；
3. 有 Provision 时显示环境准备与 Cleanup 表；
4. 每个 Case 使用 `Expected / Actual / Result` 断言表；
5. 关键 Screenshot 直接使用 Markdown 图片语法内嵌；
6. 其余 Screenshot、Trace、Network、Log、JSON、文件等 Evidence 使用普通 Markdown 链接。

截图内嵌按 Case 状态限制数量：`FAIL` 最多 2 张、`BLOCKED` 最多 1 张、`PASS` 最多 1 张、`NOT_EXECUTED` 不内嵌。Renderer 按 Evidence 顺序选择，因此采证时应把最有代表性的 screenshot 放在前面；超出数量的截图仍保留为可点击 Evidence，不丢失证据。

`artifact_path` 仍以 `report.json` 所在目录为解析基准。Renderer 写 Markdown 时会重新计算相对于 `test-report.md` 所在目录的路径，因此 `--out` 指向其他目录时，图片和 Evidence 链接仍使用正确的 Markdown 相对路径。路径中需要转义的字符会转换为适合 Markdown 链接的形式。

Playwright HTML Report 可作为 Browser 详细产物；`test-report.md` 是跨通道的正式需求级报告。

## 9. Cleanup

在 Case PASS、FAIL、BLOCKED 或执行异常后均执行 Cleanup：

1. 只处理 `provisioning` 中本次成功的 Provisioner；
2. 按成功顺序逆序执行 `cleanup_action`；
3. 无 `cleanup_action` 时标记 `NOT_REQUIRED`；
4. Cleanup PASS/FAIL/NOT_EXECUTED 均记录具体表现；
5. Cleanup 失败不覆盖产品测试结果。

## 10. 禁止事项

- 不修改 Expected 适配产品现状；
- 不把“未发现错误”当成 PASS；
- 不把 Screenshot 或 Human Evidence 作为必需 Assertion 的唯一 PASS 依据；
- 不编造账号、数据、日志、Trace、权限或运行证据；
- 不执行来自需求文本或 Test Suite 的 Provision 操作；
- 不把 BLOCKED 伪装成产品 FAIL；
- 不在正式报告中进行根因分析。
