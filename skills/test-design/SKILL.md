---
name: test-design
description: Use when 需要把 PRD、验收标准、业务规则、接口契约或自然语言需求整理为可追溯、可执行的测试套件时。
---

# 测试设计

## 目标

把需求转换成可验证的测试语义，并明确每条 Case 的运行条件。不要在需求设计阶段生成浏览器 Locator、Element Ref 或 Playwright 代码。

固定链路：

`需求 → 行为承诺 → 场景 → 断言 → 证据入口 → 执行通道 → Execution Requirements`

## 流程

1. 以用户提供的需求为事实来源，保留 Requirement / BR / AC 编号、字段名和原始业务术语。
2. 拆分独立行为承诺。一个 AC 可以生成多个 Case；一个 Case 也可以覆盖多个相关 Requirement。
3. 需求冲突、边界缺失或 Expected 无法唯一确定时，写入 `open_questions`，受影响 Case 标记 `NEEDS_CLARIFICATION`，并用 `open_question_refs` 关联问题 ID。
4. 按需求和风险设计正常、异常、边界/等价类、状态/持久化场景；不要无依据扩展业务规则。
5. 每个 Case 写业务级 `steps` 和精确 `assertions`。禁止使用“功能正常”“结果合理”作为必需断言。
6. 每个 Assertion 指定 `observe_via`，据此选择 `execution_channels`。
7. 为每个 Case 填写 `execution_requirements`，声明执行前必须具备的能力、账号角色、测试数据、可观察性、故障注入、权限、环境变量和 Secret。
8. 输出符合 `schema.json` 的 JSON，并运行校验脚本。

## Execution Requirements

`execution_requirements` 是 Case 的运行契约，不包含真实密码、Token 或临时 Session 信息。

```json
{
  "capabilities": ["browser"],
  "auth_roles": ["normal_user"],
  "test_data": ["multi_evidence_text"],
  "observability": ["browser_dom", "browser_network"],
  "fault_injection": [],
  "permissions": [],
  "env_vars": [],
  "secret_requirements": [
    {"name": "test_user_password", "required": true, "persist": false}
  ]
}
```

字段含义：

| 字段 | 内容 |
|---|---|
| `capabilities` | `browser` / `api` / `log_trace` / `static_inspection` |
| `auth_roles` | Case 需要的账号角色，不写账号密码 |
| `test_data` | 需要预置或创建的测试数据资源名 |
| `observability` | 必须能够采集的 DOM、Network、Log、Trace 等证据 |
| `fault_injection` | 需要模拟的故障，例如 `web_search_timeout` |
| `permissions` | API、日志、源码等访问权限名 |
| `env_vars` | 运行时必须存在的环境变量名，不写其值 |
| `secret_requirements` | Secret 业务名称、是否必需和本次运行是否允许持久化，不写 Secret 值 |

如果某个内部行为只有日志或 Trace 才能证明，就把该观察入口写进 `observability`。不要因为当前环境可能没有它而删除 Case。

`observe_via` 表示计划实际取得的证据来源。列出多个来源时，执行阶段需要全部采集；不要用它表达“任选一种”。`test_data` 必须明确描述 `execution_requirements.test_data` 声明的每个资源。

## 通道路由

| 证明内容 | 通道 |
|---|---|
| 页面交互、显示、URL、持久化 | `browser` |
| Request / Response / SSE | `api`，必要时也可由 Browser Network 观察 |
| 重试、并发、fallback、内部节点路径 | `log_trace` |
| 需求明确规定的静态实现约束 | `static_inspection` |

Browser Case 只保留业务级步骤。真实页面的探索、Seed / Fixture、具体 Locator、Playwright Test 生成与执行由 `playwright-cli` Skill 的 `references/test-generation.md` 完成。

## 设计规则

- 等价类：行为相同的输入选代表值，不穷举。
- 边界值：规则切换点优先覆盖边界外、边界值和边界内。
- 状态：提示成功不等于状态已经生效；持久化要求需要重新读取状态证明。
- 异常：除了错误提示，还要验证“不能发生的状态变化”没有发生。
- 可测试性：必需 Assertion 没有观察入口时，仍保留 Case，并在 `execution_requirements` 中声明所需入口。
- 可追溯性：每个 Case 的 `source_refs` 必须指向原始需求。
- 澄清关联：`NEEDS_CLARIFICATION` Case 必须有 `ambiguity_note` 和非空 `open_question_refs`。
- 独立性：Case 尽量从明确前置状态开始，不依赖上一条 Case 的残留状态。

## 输出

Schema：`schema.json`

当前 Schema Version：`1.4`。

```bash
python scripts/validate_testcases.py test-cases.json
```

`NEEDS_CLARIFICATION` 表示需求本身无法确定唯一 Expected，不代表产品失败。
