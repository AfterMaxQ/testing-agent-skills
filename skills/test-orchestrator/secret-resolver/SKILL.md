---
name: secret-resolver
description: Use when Test Suite 或 Provisioner 声明了 secret_requirements，需要在不把 Secret 值写入测试文件、报告或 Agent 上下文的前提下解析并注入测试子进程时。
---

# Secret Resolver

## 目标

Secret Resolver 将业务 Secret 名称解析为临时运行环境变量，并输出不含 Secret 值的 Runtime Context 元数据。

支持的来源顺序：

```text
Runtime Secret Store
→ Local Secret Store
→ 当前进程环境变量
→ Secret Schema 声明的外部 Provider
→ 可选 Manual Input
```

## 本地文件

Resolver 默认识别：

```text
.testing-agent/config.json
.testing-agent/secrets.env
.testing-agent/runtime/secrets.env
```

配置模板位于：

```text
skills/test-orchestrator/examples/
├── config.example.json
└── secrets.env.example
```

`.testing-agent/` 是本地运行目录，不提交到 Git。

## 安全边界

- Test Suite 只写 Secret 业务名称和是否必需；
- Secret Schema 只写业务名称、环境变量名、允许来源和生命周期策略；
- Runtime Context 只写来源、状态、时间和生命周期策略；
- Secret 值只存在于 Resolver 进程及其子进程环境；
- 日志、Report、Trace、Screenshot 和错误信息不得输出 Secret 值；
- `persist` 只影响 Runtime Context 中的策略元数据，Resolver 不自动把输入值写回文件；
- Manual Input 默认关闭，启用后也不自动持久化输入值。

## 运行

解析并生成 Runtime Context：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json
```

让子进程继承解析后的 Secret：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --out runtime-context.json \
  --exec python skills/test-orchestrator/scripts/preflight.py \
    test-cases.json runtime-context.json --out readiness.json
```

启用一次性人工输入：

```bash
python skills/test-orchestrator/scripts/resolve_secret.py \
  --schema skills/test-orchestrator/secret.schema.json \
  --suite test-cases.json \
  --context test-context.json \
  --allow-manual \
  --out runtime-context.json
```

外部 Provider 包括 Vault、AWS Secrets Manager、GitHub Actions 和 Kubernetes。Resolver 只使用 Secret Schema 声明的来源。

## 解析结果

每个 Secret 生成一条 `runtime_secrets` 元数据：

- `resolved`：已注入子进程环境；
- `missing`：允许的来源中没有值；
- `unavailable`：来源已声明，但当前 Provider 无可用连接；
- `manual_required`：需要显式启用人工输入；
- `expired`：来源值已过期。

任何 required Secret 不是 `resolved` 时，对应测试 Case 不能进入执行。
