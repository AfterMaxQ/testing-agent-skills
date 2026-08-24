# Testing Agent Skills

面向 Coding Agent 的通用测试 Skill 包。输入可以是 PRD、验收标准、业务规则、接口契约或自然语言需求；输出为可追溯 Test Suite、测试就绪检查和统一测试报告。

详细的用户操作说明和关键注意事项见 [USAGE.md](USAGE.md)。

Browser 测试直接使用 Microsoft Playwright CLI Skill。自研部分负责需求级测试设计、运行条件声明、测试环境 Preflight、跨通道路由、证据判定和报告汇总。

## 1. 架构

```text
                         Requirement / PRD
                                │
                                ▼
                       ┌─────────────────┐
                       │   test-design   │
                       │   需求级测试设计  │
                       └────────┬────────┘
                                │ Test Suite
                                ▼
                     execution_requirements
                                │
                                ▼
                         ┌──────────────┐
                         │ Test Context │
                         │ 当前环境能力  │
                         └──────┬───────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   test-orchestrator    │
                    │ Secret / Preflight /   │
                    │ Provision / Reflight   │
                    └───────────┬────────────┘
                                │
                      Ready / Provisioned
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                  │
              ▼                 ▼                  ▼
          browser             api          log_trace / static
              │                 │                  │
              ▼                 │                  │
      ┌─────────────────┐       │                  │
      │ playwright-cli  │       │                  │
      │ 官方 Browser Skill│      │                  │
      └────────┬────────┘       │                  │
               └────────────────┼──────────────────┘
                                │
                                ▼
                         Actual Evidence
                                │
                                ▼
                       PASS / FAIL / BLOCKED
                                │
                                ▼
                         Unified Report
```

模块职责：

| 模块 | 负责 |
|---|---|
| `test-design` | 需求拆解、场景、断言、证据入口、执行通道、运行条件、需求追溯 |
| `test-orchestrator` | Preflight、Provision 写回、Reflight、执行路由、Evidence 汇总、状态判定、报告与 Cleanup |
| `playwright-cli` | Browser 探索、Seed/Fixture、Locator、Playwright Test、Network Mock、Trace、Screenshot |

## 2. 数据流

```text
需求文档
  │
  │ test-design
  ▼
test-cases.json
  │
  │ 声明每个 Case 的 execution_requirements
  ▼
test-context.json ───────────────┐
  │                              │
  └──────────────┬───────────────┘
                 ▼
         Secret Resolution
                 │
                 ▼
              Preflight
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
     READY  PROVISIONABLE BLOCKED
       │         │
       │      Provision
       │         │
       │         ▼
       │   runtime-context.json
       │         │
       │      Reflight
       │         │
       └────┬────┘
            ▼
          Execute
            │
    ┌───────┼──────────────┐
    ▼       ▼              ▼
 Browser   API       Log/Trace / Static
    │
    ▼
playwright-cli
    │
    └──────────────► Evidence
                       │
                       ▼
                   report.json
                       │
                       ▼
                 test-report.md
```

### 2.1 Test Suite 声明运行条件

`test-design` 不假设测试环境一定具备账号、数据、日志或权限。每条 Case 用 `execution_requirements` 明确声明：

```json
{
  "capabilities": ["browser", "log_trace"],
  "auth_roles": ["normal_user"],
  "test_data": ["long_text_fixture"],
  "observability": ["browser_dom", "log"],
  "fault_injection": ["web_search_timeout"],
  "permissions": ["logs:verify-service"],
  "env_vars": [],
  "secret_requirements": [
    {"name": "test_user_password", "required": true, "persist": false}
  ]
}
```

这描述“Case 需要什么”，不保存密码、Token 或临时 Session。

### 2.2 Test Context 描述当前环境

`test-context.json` 描述“现在有什么”和“缺少时怎样准备”：

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
    "capabilities": ["browser", "api", "log_trace"],
    "auth_roles": [],
    "test_data": [],
    "observability": ["browser_dom", "browser_network", "trace", "log"],
    "fault_injection": [],
    "permissions": ["logs:verify-service"],
    "env_vars": []
  },
  "runtime_secrets": [],
  "provisioners": [
    {
      "id": "prepare-normal-user",
      "kind": "playwright",
      "provides": [{"category": "auth_roles", "name": "normal_user"}],
      "action": "登录测试账号并保存 Playwright storage state",
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

敏感值通过 Secret Resolver 注入，不写入 Test Suite、Test Context、Readiness 或 Report。Runtime Context 的 `runtime_secrets` 只保存来源、状态和生命周期元数据。

### 2.3 Preflight 与 Provision

先执行：

```bash
python skills/test-design/scripts/validate_testcases.py test-cases.json
python skills/test-orchestrator/scripts/validate_context.py test-context.json
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
python skills/test-orchestrator/scripts/preflight.py test-cases.json runtime-context.json --out readiness.json
python skills/test-orchestrator/scripts/render_readiness.py readiness.json --out readiness.md
```

Preflight 将每条 Case 分为：

- `READY`：当前可直接执行；
- `PROVISIONABLE`：有缺失条件，但存在可自动执行的 Provisioner；
- `BLOCKED`：当前缺失且没有自动解决路径；
- `NEEDS_CLARIFICATION`：需求本身仍待澄清。

`readiness.md` 会按缺失条件聚合受影响 Case，便于一次补齐账号、权限、日志入口或测试数据。

对可自动准备的 Gap，`test-orchestrator` 执行 Test Context 中受信任的 Provisioner 并验证结果。验证成功后执行：

```bash
python skills/test-orchestrator/scripts/apply_provision.py test-context.json \
  --verified prepare-normal-user \
  --out runtime-context.json
python skills/test-orchestrator/scripts/preflight.py test-cases.json runtime-context.json --out readiness-after.json
```

只有验证成功的 `provides` 才写入 Runtime Context。Secret Resolver 解析出的值只注入它启动的子进程；必需 Secret 未 `resolved` 时不会启动后续命令。Reflight 后仍不满足运行条件，Case 才进入 `BLOCKED`；Provision 失败记录为 `provision_failure`，不判产品 FAIL。

Secret Resolver 的默认来源顺序为 Runtime Secret Store、`.testing-agent/secrets.env`、当前进程环境变量、已声明的外部 Provider、显式启用的 Manual Input。普通开发者只需复制 `.testing-agent/secrets.env.example` 为 `.testing-agent/secrets.env` 并填写值；该文件已被 `.gitignore` 排除。

### 2.4 Browser Case

Browser Case 由 `playwright-cli` 负责页面层具体化：

```text
需求级 Browser Case
        │
        ▼
Seed / Fixture
        │
        ▼
Planning
        │
        ▼
Locator / Playwright Test
        │
        ▼
Run
        │
        ▼
DOM / URL / Network / Trace / Screenshot
```

Browser 自带的 Trace、Network、Request Mock、Storage State 等能力优先直接使用 Playwright，不作为外部环境缺失项处理。

## 3. 使用示例

需求：

```text
AC-022：长文本核实时，段落并发数固定为 3。
```

### 3.1 生成 Case

`test-design` 生成的 Case 重点是“如何证明并发为 3”，而不是页面按钮怎么点：

```json
{
  "id": "F005-AC022-001",
  "title": "长文本核实固定三段并发",
  "source_refs": ["AC-022"],
  "open_question_refs": [],
  "objective": "验证长文本段落处理并发数固定为 3",
  "design_status": "READY",
  "priority": "P0",
  "execution_channels": ["browser", "log_trace"],
  "preconditions": ["测试环境可访问"],
  "execution_requirements": {
    "capabilities": ["browser", "log_trace"],
    "auth_roles": ["normal_user"],
    "test_data": ["long_text_fixture"],
    "observability": ["browser_dom", "log"],
    "fault_injection": [],
    "permissions": ["logs:verify-service"],
    "env_vars": [],
    "secret_requirements": [
      {"name": "test_user_password", "required": true, "persist": false}
    ]
  },
  "test_data": {"fixture": "long_text_fixture"},
  "steps": ["提交长文本核实", "等待处理完成"],
  "assertions": [
    {
      "id": "A1",
      "expected": "段落处理并发数固定为 3",
      "observe_via": ["log"],
      "required": true
    }
  ],
  "cleanup": []
}
```

### 3.2 Preflight

如果当前环境有 Browser，但没有服务日志权限，Preflight 不直接执行 Case，而是在 `readiness.md` 中集中列出：

```text
logs:verify-service — BLOCKED
影响 Case：F005-AC022-001、F005-AC025-001、F005-AC035-001
原因：当前环境未提供该权限，且没有可用 Provisioner
```

如果 Test Context 中存在日志权限 Provisioner，则状态为 `PROVISIONABLE`，先完成环境准备再执行。

### 3.3 执行与报告

环境就绪后：

1. Playwright 执行页面主流程；
2. `log_trace` 通道读取对应运行日志；
3. A1 的 Actual 与 Expected 比较；
4. 有证据证明并发数为 3 → `PASS`；
5. 证据显示并发数不是 3 → `FAIL`；
6. Provision 后仍无法读取日志 → `BLOCKED`，并在报告中记录结构化 blocker；
7. PASS/FAIL 都保存本次运行 Evidence，Report 必须精确覆盖全部 Suite Case；
8. 测试结束后只清理本次成功 Provision 创建的资源，并记录 Cleanup 状态。

最终：

```bash
python skills/test-orchestrator/scripts/validate_report.py report.json --suite test-cases.json --context test-context.json
python skills/test-orchestrator/scripts/render_report.py report.json --suite test-cases.json --out test-report.md
```

## 4. 安装

包内包含 Microsoft 官方 `playwright-cli` Skill；运行环境仍需安装 CLI：

```bash
npm install -g @playwright/cli@0.1.18
```

Python 校验脚本需要：

```bash
pip install "jsonschema>=4.20,<5"
```

## 5. 目录

```text
testing-agent-skills/
├── README.md
├── USAGE.md
├── docs/
│   ├── architecture.md
│   └── implementation-plan.md
├── skills/
│   ├── test-design/
│   │   ├── SKILL.md
│   │   ├── schema.json
│   │   └── scripts/validate_testcases.py
│   ├── test-orchestrator/
│   │   ├── SKILL.md
│   │   ├── schema.json
│   │   ├── context.schema.json
│   │   ├── readiness.schema.json
│   │   ├── secret.schema.json
│   │   ├── secret-resolver/SKILL.md
│   │   └── scripts/
│   │       ├── resolve_secret.py
│   │       ├── preflight.py
│   │       ├── render_readiness.py
│   │       ├── apply_provision.py
│   │       ├── validate_context.py
│   │       ├── validate_report.py
│   │       └── render_report.py
│   └── playwright-cli/
├── licenses/
├── .gitignore
└── .testing-agent/
    ├── config.example.json
    └── secrets.env.example
```
