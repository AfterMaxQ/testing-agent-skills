# Testing Agent Skills 最小闭环实施计划

## 1. 目标

在保留现有分层设计的前提下，补齐以下可验证链路：

```text
Requirement
  → Test Suite
  → Test Context
  → Preflight
  → Provision
  → Reflight
  → Browser / API / Log-Trace / Static Inspection
  → Assertion Evidence
  → PASS / FAIL / BLOCKED / NOT_EXECUTED
  → report.json
  → test-report.md
  → Cleanup
```

实施必须保留：

1. `context.schema.json`；
2. `readiness.schema.json`；
3. `preflight.py`；
4. `render_readiness.py`；
5. 通用 Provisioner；
6. `report.json` Schema、语义校验和 Markdown 渲染；
7. Browser、API、Log-Trace、Static Inspection 四类执行通道。

目标不是建设独立测试平台，而是让 Coding Agent 能依据统一契约完成测试设计、运行条件检查、实际执行和报告交付。

## 2. 约束与不做项

### 2.1 实施约束

- 原始需求和 Test Suite 中的 Expected 是唯一验收基准；实际产品行为只能形成 Actual。
- `playwright-cli` 只负责 Browser 具体化和执行，不得自行修改需求级 Expected。
- Provisioner 只能来自受信任的 Test Context，不能从需求文本或 Test Suite 读取并执行操作。
- Secret 值不写入 Test Suite、Test Context、Readiness 或 Report。
- PASS 和 FAIL 都必须有本次运行的直接证据；未执行或证据不足不得判 PASS。
- 报告只描述 Expected、Actual、Evidence、失败表现和阻塞条件，不分析根因。
- 第三方 `playwright-cli` Skill 保持独立；适配规则放在 `test-orchestrator`，避免形成难以同步的私有分叉。
- 自研 Skill 使用工具中立的输入输出契约，不绑定 Codex、Trae 或某个 Agent 的专有工具名；实际 Browser 能力统一落到 Playwright CLI。

### 2.2 本阶段不做

- 不开发新的浏览器自动化引擎；
- 不开发插件注册中心或 Adapter SDK；
- 不实现 Provisioner 依赖图、递归 Provision 或并行 Provision 调度；
- 不内置 Secret Manager；
- 不开发自定义 HTML 报告，直接复用 Playwright HTML Report；
- 不实现缺陷根因分析、自动修复产品代码或自动修改 Expected；
- 不为未出现的执行通道增加扩展点。

## 3. 最小数据契约

继续使用四个公开 JSON 契约：

| 契约 | 作用 | 是否持久化 |
|---|---|---|
| Test Suite | 需求追溯、步骤、断言、证据入口和运行条件 | 是 |
| Test Context | 基础环境已有能力和受信任 Provisioner | 是 |
| Readiness | 本次 Preflight 的 Case 状态和聚合缺口 | 本次运行产物 |
| Report | Provision、执行、证据、状态和 Cleanup 结果 | 最终产物 |

Provision 后生成 Runtime Context。Runtime Context 是 Test Context 的本次运行副本，继续使用 `context.schema.json`，不新增第五个公开 Schema。只有 Provision 验证成功后，Provisioner 的 `provides` 才能合并到 Runtime Context 的 `available`。

Readiness 是派生产物，不由 Agent 手工编辑。Report 同时承担本次运行账本，记录已成功执行的 Provisioner 及其 Cleanup 状态，避免再增加独立 Run State 契约。

## 4. Test Suite 一致性

保留现有 Test Suite 结构，并补齐以下语义规则：

1. Case ID 在 Suite 内唯一；
2. Assertion ID 在 Case 内唯一；
3. `source_refs` 必须非空并保留原始 Requirement、BR 或 AC 标识，不尝试解析需求正文建立额外注册表；
4. `execution_channels` 必须全部出现在 `execution_requirements.capabilities`；
5. Assertion 的 `observe_via` 必须包含在 `execution_requirements.observability`；
6. Browser、API、Log-Trace、Static Inspection 的证据类型必须与执行通道匹配；
7. `NEEDS_CLARIFICATION` Case 必须有 `ambiguity_note`，并关联一个待澄清问题；
8. 必需 Assertion 不得仅依赖 Screenshot 或 Human Evidence；
9. Case 中的测试数据说明必须能对应 `execution_requirements.test_data` 中声明的资源名。

`observe_via` 表示计划实际取得的证据来源，不表示候选来源列表。多个值表示这些证据都应被采集，避免为“任选其一”增加新的组合表达式。

## 5. Preflight

### 5.1 输入校验

`preflight.py` 在计算就绪状态前必须执行 Test Suite 和 Test Context 的 Schema 校验与语义校验，不能只检查 JSON 结构。

环境变量分为两类：

- Case 的 `execution_requirements.env_vars`：可以由 Test Context 声明为环境已提供；
- Provisioner 的 `requires_env`：必须检查当前进程真实存在的环境变量，不能仅凭 Context 中声明的名称判定可用。

### 5.2 Gap 判定

每个缺失条件生成一个 Gap：

- 有可自动执行的 Provisioner：`PROVISIONABLE`；
- 只有 `manual` Provisioner：`BLOCKED`，并输出人工准备说明；
- 有自动 Provisioner，但其 `requires_env` 不满足：`BLOCKED`；
- 没有 Provisioner：`BLOCKED`；
- 需求待澄清：`NEEDS_CLARIFICATION`。

Provision 决策按 Gap 进行，而不是只看 Case 总状态。一个 Case 同时含有 `PROVISIONABLE` 和 `BLOCKED` Gap 时，可自动准备的共享条件仍应进入 Provision 计划，避免阻塞其他 Case。

同一缺失条件存在多个 Provisioner 时，按 Test Context 中的声明顺序选择第一个当前可执行的 Provisioner。Readiness 可保留全部候选 ID，但一次只执行一个，不引入优先级字段和调度算法。

### 5.3 Case 状态

Case Readiness 聚合顺序保持：

1. 需求待澄清 → `NEEDS_CLARIFICATION`；
2. 任一 Gap 为 `BLOCKED` → `BLOCKED`；
3. 否则任一 Gap 为 `PROVISIONABLE` → `PROVISIONABLE`；
4. 无 Gap → `READY`。

`render_readiness.py` 只渲染经过 `readiness.schema.json` 校验的数据，并按缺失条件聚合 Case、候选 Provisioner 和处理说明。

## 6. Provision 闭环

### 6.1 Provisioner 最小协议

继续支持：

- `command`：执行受信任的测试环境命令或脚本；
- `playwright`：准备登录状态、Storage State 或 Browser Fixture；
- `api`：通过测试 API 创建数据或启用测试开关；
- `manual`：只输出人工操作说明，不自动执行。

自动 Provisioner 必须声明：

- `provides`：成功后新增的运行条件；
- `action`：由对应通道执行的准备操作；
- `requires_env`：执行前必须真实存在的环境变量名；
- 验证方式：用于证明 `provides` 已经成立；
- 可选 `cleanup_action`：撤销本次运行产生的资源。

`action` 和验证方式保持工具中立，由 Agent 使用当前可用工具执行；不在 Python 中对自然语言执行 `shell=True`。

### 6.2 状态写回

Provision 流程固定为：

1. 从全部 Gap 中去重得到待执行 Provisioner；
2. 校验 `requires_env`；
3. 执行 `action`；
4. 执行验证并保存 Evidence；
5. 验证成功后，将 `provides` 合并到 Runtime Context；
6. 在 Report 的 Provision 记录中保存状态、Evidence 和待执行 Cleanup；
7. 使用 Runtime Context 重新运行 Preflight；
8. Reflight 后仍缺少条件的 Case 才进入最终 `BLOCKED`。

未经验证的 Provision 不得更新 Runtime Context。Provision 失败使用结构化 `provision_failure` blocker，不把它判为产品 FAIL。

### 6.3 Cleanup

只清理由本次运行成功 Provision 的资源：

1. 按 Provision 成功顺序的逆序执行 `cleanup_action`；
2. 无 `cleanup_action` 的 Provisioner 不执行推测性清理；
3. Case PASS、FAIL、BLOCKED 或执行异常后都进入 Cleanup；
4. Cleanup 失败记录在 Report，不覆盖 Case 的产品测试结果。

本阶段不实现进程崩溃后的跨进程恢复。运行中断时保留 Report 工作文件，供人工按其中 Provision 记录清理。

## 7. 执行通道

四类通道使用同一个输出协议：

```text
Assertion ID
Status
Observed
Evidence[]
Blocker（仅无法执行或观察时）
```

Adapter 是 `test-orchestrator` 中的通道规则和输出约束，不建设类层级、插件注册表或独立服务。

### 7.1 Browser

- 使用 `playwright-cli` 完成 Seed/Fixture、页面探索、Locator、Test 生成和执行；
- DOM、URL、Network、Trace、Screenshot 等均由 Playwright 提供；
- 可修改 Locator、等待方式和技术步骤；
- 产品行为与 Expected 不一致时判 FAIL，不自动修改 Expected；
- Playwright HTML Report 作为 Browser 详细运行产物，统一 Markdown Report 保存需求级结果摘要。

### 7.2 API

- 使用 Agent 当前已有 HTTP 能力或项目既有 API 测试入口；
- 记录方法、目标、关键请求字段、状态码和关键响应字段；
- SSE Case 记录事件名称、顺序和必要载荷；
- 不在 Report 中保存密码、Token 或完整敏感 Header；
- 没有 API 入口或权限时返回 BLOCKED。

### 7.3 Log-Trace

- 仅使用 Test Context 声明的日志、Trace、Metric 或 Debug API；
- 使用 Case ID、请求 ID、Trace ID 或时间窗关联本次运行；
- Evidence 保存直接支持断言的最小日志或 Trace 摘要及产物路径；
- 无法可靠关联本次运行时返回 BLOCKED，不用 UI 结果推测内部并发、重试或 fallback。

### 7.4 Static Inspection

- 只验证需求明确规定的源码、配置或文件约束；
- 只读取当前公开或用户明确授权的文件范围；
- Evidence 保存精确文件位置和观察到的实现值；
- 不把 Static Inspection 扩展为通用代码审查或根因分析。

### 7.5 多通道 Case

Case 声明多个执行通道时，Orchestrator 按 Assertion 所需 Evidence 调用相应通道。每个通道只返回自身观察结果，Case 状态由统一报告规则聚合，通道 Adapter 不自行修改其他通道结果。

## 8. Report 闭环

### 8.1 完整性

Report 必须满足：

1. `suite_id` 和 `context_id` 与输入一致；
2. Suite 中每个 Case 恰好有一个 Case Result；
3. 不允许未知或重复 Case Result；
4. 每个必需 Assertion 恰好有一个 Actual；
5. 不允许未知或重复 Assertion Actual；
6. Summary 总数必须等于 Suite Case 总数，并与 Case 状态重新计算结果一致；
7. Provision 记录只能引用 Test Context 中存在的 Provisioner；
8. Evidence 类型必须属于 Assertion 的 `observe_via`；
9. 本地产物型 Evidence 声明 `artifact_path` 时必须指向实际存在的产物。

### 8.2 Assertion 判定

- `PASS`：Observed 满足 Expected，且 Evidence 非空；
- `FAIL`：Observed 与 Expected 直接矛盾，且 Evidence 非空；
- `BLOCKED`：缺少执行或观察条件，并有结构化 blocker；
- `NOT_EXECUTED`：运行被取消或中断，并在 notes 中说明原因。

PASS 和 FAIL 的 `observed` 必须非空。Screenshot 和 Human Evidence 不得单独支持必需 Assertion 的 PASS。

### 8.3 Case 聚合

只按必需 Assertion 聚合：

1. 任一 Assertion 为 FAIL → Case 为 FAIL；
2. 否则任一 Assertion 为 BLOCKED → Case 为 BLOCKED；
3. 否则任一 Assertion 为 NOT_EXECUTED → Case 为 NOT_EXECUTED；
4. 其余全部 PASS → Case 为 PASS。

Case 同时包含 FAIL 和 BLOCKED Assertion 时，Case 状态为 FAIL，但允许保留对应结构化 blockers，避免丢失未完成的验证范围。

`NEEDS_CLARIFICATION` 在最终 Report 中映射为 BLOCKED，并使用 `requirement_clarification` blocker，不新增第五种报告状态。

### 8.4 报告内容

`test-report.md` 至少包含：

- Suite、Context 和执行范围；
- PASS、FAIL、BLOCKED、NOT_EXECUTED 汇总；
- 每条 Case 的需求来源、Expected 和最终状态；
- 每条 Assertion 的 Observed 和 Evidence；
- FAIL 的具体失败表现；
- BLOCKED 的缺失条件和处理建议；
- Provision 和 Cleanup 状态；
- 可用的 Playwright HTML、Trace 或 Screenshot 产物链接。

报告不包含根因推测和修复建议。

## 9. 实施步骤

### 阶段一：契约一致性

修改 Test Suite、Context、Readiness 和 Report 的 Schema/校验逻辑，统一枚举与跨字段语义。

验收证据：

- 四个 Schema 可解析；
- 合法 Fixture 全部通过；
- 重复 ID、证据通道不匹配、缺少澄清关联等非法 Fixture 被拒绝；
- 现有公开字段除明确调整项外保持兼容。

### 阶段二：Preflight 与 Provision 状态闭环

补齐语义校验、真实环境变量检查、Gap 级 Provision 选择、Runtime Context 写回和 Reflight。

验收场景：

1. 条件完整：READY；
2. 缺少条件且没有 Provisioner：BLOCKED；
3. 只有 manual Provisioner：BLOCKED 并显示人工说明；
4. 自动 Provision 成功：PROVISIONABLE → READY；
5. Provision 验证失败：最终 BLOCKED + `provision_failure`；
6. Case 同时含可准备和不可准备 Gap：执行共享 Provision 后重新聚合；
7. Cleanup 只处理本次成功 Provision 的资源。

### 阶段三：四通道 Adapter

在 `test-orchestrator` 中固化 Browser、API、Log-Trace、Static Inspection 的输入、证据和阻塞规则；Browser 继续复用 `playwright-cli`。

验收场景：

- Browser DOM 断言生成 Playwright Evidence；
- API Response 和 SSE 断言生成结构化 Evidence；
- Log-Trace Case 能用本次请求标识关联证据；
- Static Inspection 保存精确文件位置；
- 缺少任何必需观察入口时诚实返回 BLOCKED。

### 阶段四：Report 完整性和渲染

补齐 Suite 全覆盖、唯一性、Evidence 匹配、状态聚合、Provision/Cleanup 记录和 Markdown 渲染。

验收场景：

- 漏掉任一 Suite Case 的 Report 被拒绝；
- 重复 Case 或 Assertion Actual 被拒绝；
- PASS/FAIL 无 Evidence 被拒绝；
- Evidence 类型与 `observe_via` 不匹配时被拒绝；
- FAIL 与 BLOCKED 并存时保留失败结果和 blocker；
- 汇总数字与 Case 结果不一致时被拒绝；
- 合法 Report 可渲染为完整 Markdown。

### 阶段五：F-005 端到端验收

使用 F-005 需求建立最小真实 Suite，至少覆盖：

- Browser：短文本结果或角标与证据对应；
- API/SSE：预定义进度事件；
- Log-Trace：固定三段并发或分层重试；
- Static Inspection：入口字段、默认配置或 fallback 日志接线；
- 一个无法取得观察入口的 BLOCKED Case；
- 一个带直接矛盾 Evidence 的 FAIL Case。

正式验收产物：

- Test Suite；
- Test Context；
- Provision 前后 Readiness；
- Runtime Context；
- `report.json`；
- `test-report.md`；
- Browser Case 对应的 Playwright HTML/Trace 产物；
- 执行命令和结果摘要。

F-005 的实际产品执行依赖可访问的目标环境、账号、测试数据和日志入口。未提供这些条件时，先使用 F-005 派生 Fixture 验证框架闭环；真实产品 Case 按 Readiness 结果标记 BLOCKED，不编造运行证据。

## 10. 变更边界

实施阶段允许修改：

- `test-design` 的 Skill、Schema 和校验脚本；
- `test-orchestrator` 的 Skill、三个 Schema 和现有脚本；
- README 和架构文档中与最终公开行为直接相关的内容；
- 通过临时 Fixture 验证上述契约和脚本，验证产物不进入发布包。

默认不修改：

- `playwright-cli` 第三方 Skill 和 references；
- License；
- 与测试闭环无关的仓库内容。

若实现中确认必须修改第三方 Playwright Skill，先单独说明原因、影响和替代方案，再扩大范围。

## 11. 完成标准

只有同时满足以下条件才算实施完成：

1. 四个公开 JSON 契约和语义校验全部通过；
2. Provision 成功后可通过 Runtime Context 和 Reflight 确定性进入 READY；
3. 四类通道均有明确输入、Evidence 和 BLOCKED 输出规则；
4. Report 精确覆盖整个 Suite，不能遗漏或重复 Case；
5. PASS 和 FAIL 均由本次运行的允许类型 Evidence 支持；
6. BLOCKED 与产品 FAIL 被明确区分；
7. Cleanup 仅针对本次成功 Provision 的资源并被记录；
8. F-005 最小端到端 Suite 产出有效 JSON、Markdown 和 Browser 运行产物；
9. Skill 契约不绑定单一 Agent，并至少在一种 Agent 环境完成实际演示，同时给出其他 Agent 的等价操作入口；
10. 全部契约与闭环验证通过；
11. `git diff --name-status` 只包含批准范围内的文件。

计划批准前不进入实现阶段。
