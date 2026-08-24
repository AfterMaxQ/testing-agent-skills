# Testing Agent Skills

面向 Coding Agent 的通用测试 Skill 包。输入可以是 PRD、验收标准、业务规则、接口契约或自然语言需求；输出为可追溯 Test Suite、测试就绪检查和统一测试报告。

Browser 测试直接使用 Microsoft Playwright CLI Skill。自研部分负责需求级测试设计、运行条件声明、测试环境 Preflight、跨通道路由、证据判定和报告汇总。

## 1. 架构

```text
Requirement / PRD
        |
        v
 test-design
        |
        v
   Test Suite
        |
        v
execution_requirements
        |
        v
 test-orchestrator
        |
  +-----+-----+--------+
  |           |        |
Browser      API   Log/Trace
  |
  v
Playwright CLI
        |
        v
 Evidence
        |
        v
 PASS / FAIL / BLOCKED
        |
        v
 Unified Report
```

模块职责：

| 模块 | 负责 |
|---|---|
| `test-design` | 需求拆解、测试场景、断言、证据入口、执行通道、运行条件、需求追溯 |
| `test-orchestrator` | Preflight、环境准备、执行路由、Evidence 汇总、结果判断、报告生成 |
| `playwright-cli` | Browser 探索、Seed/Fixture、Playwright Test、Network Mock、Trace、Screenshot |

## 2. 数据流

```text
需求文档
   |
   v
test-design
   |
   v
Test Cases
   |
   v
Preflight
   |
 +---------+-------------+
 |         |             |
READY  PROVISIONABLE  BLOCKED
 |         |
 |     Provision
 |         |
 +----+----+
      |
      v
 Execute Tests
      |
      v
 Evidence Collection
      |
      v
 Test Report
```

### Test Suite 与运行环境

每条 Case 通过 `execution_requirements` 声明执行需要的条件：

```json
{
  "capabilities": ["browser", "log_trace"],
  "auth_roles": ["normal_user"],
  "test_data": ["long_text_fixture"],
  "observability": ["browser_dom", "log"],
  "permissions": ["logs:verify-service"]
}
```

Test Context 描述当前环境能力，包括：

- 可用账号和权限
- 测试数据
- 日志和 Trace 能力
- 故障注入能力
- 自动准备 Provisioner

Preflight 会判断：

- `READY`：当前环境可以执行；
- `PROVISIONABLE`：存在自动准备方式；
- `BLOCKED`：当前无法满足且没有准备路径；
- `NEEDS_CLARIFICATION`：需求仍需确认。

## 3. Browser 测试

Browser Case 不负责重复实现 Playwright 能力。

执行流程：

```text
Browser Case
      |
      v
Seed / Fixture
      |
      v
Planning
      |
      v
Playwright Test
      |
      v
Run
      |
      v
DOM / URL / Network / Trace Evidence
```

Trace、Network、Request Mock、Storage State 等能力优先使用 Playwright 官方能力。

## 4. 使用示例

需求：

```text
AC-022：长文本核实时，段落并发数固定为 3。
```

生成测试 Case：

```text
目标：验证长文本处理过程中并发数固定为 3

执行通道：
- browser
- log_trace

需要：
- normal_user 账号
- long_text_fixture 数据
- 服务日志读取权限

断言：
日志中存在并发数为 3 的证据
```

执行流程：

```text
Test Suite
    |
    v
Preflight 检查环境
    |
    +-- 缺少日志权限
    |       |
    |       v
    |   查找 Provisioner
    |
    v
Playwright 执行业务流程
    |
    v
收集日志和页面证据
    |
    v
生成 PASS / FAIL / BLOCKED 报告
```

## 5. 安装

运行环境需要安装 Playwright CLI：

```bash
npm install -g @playwright/cli
```

Python 校验脚本依赖：

```bash
pip install jsonschema
```

## 6. 目录

```text
testing-agent-skills/
├── README.md
├── docs/
│   ├── architecture.md
│   └── implementation-plan.md
├── skills/
│   ├── test-design/
│   ├── test-orchestrator/
│   └── playwright-cli/
└── licenses/
```
