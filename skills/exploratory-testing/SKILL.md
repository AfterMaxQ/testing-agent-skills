---
name: exploratory-testing
description: Use when 只有一个已经运行的 Web 页面或 URL、缺少正式 Requirement / PRD / AC，需要自主理解应用并进行探索式测试时。
---

# 探索式测试

## 目标

用于 **只有 URL、没有正式需求和明确 Expected** 的 Web 应用探索。

**REQUIRED SUB-SKILL:** playwright-cli

本 Skill 负责决定：为什么探索、下一步探索什么、什么时候需要确认异常、什么时候允许结束。浏览器打开、Snapshot、元素识别、交互、Screenshot、Network、Trace 等能力直接复用 `playwright-cli`。

本 Skill **不要求先生成 `requirements.md` 或 `test-cases.json` 才开始测试**，也不替代已有正式需求时的 `test-design`。

固定主流程：

```text
URL
 ↓
Initial Observation
 ↓
Feature Inventory
 ↓
Application Map
 ↓
Exploration Planner
 ↓
Exploration Missions
 ↓
Execute → Observe → Update Map
   ↑                 ↓
   └──── Plan Next ──┘
            ↓
       Coverage Gate
            ↓
         Findings
            ↓
   exploration-report.md
            ↓
 optional requirements.md
```

## 什么时候使用

适合：

- 只有运行中的 Web 页面或 URL；
- 没有 PRD、AC 或可靠验收标准；
- 希望 Agent 自主理解页面、主动探索状态关系和发现异常；
- 希望知道“探索了什么、遗漏了什么”，而不是只让 Agent 随便点击。

不适合：

- 已有明确 Requirement / PRD / AC：直接使用 `test-design`；
- 已经有正式 Test Suite：进入 `test-orchestrator`；
- 需要把当前页面表现直接当成正式 Expected。

## 1. Initial Observation：先看全局，不要立即乱点

页面观察优先级：

```text
Accessibility / Snapshot > Rendered DOM > Raw HTML
```

DOM / Accessibility 主要负责确认：

- heading、button、link、textbox、combobox、tab、table、list、dialog、navigation；
- 可见文字；
- selected、disabled、required 等状态；
- 当前页面主要交互入口。

只有需要确认 `maxlength`、`minlength`、`pattern`、`required`、`disabled` 等直接影响用户行为的属性时，才针对目标元素读取 Rendered DOM。

Vision 只补充：

- 页面区域和视觉层级；
- 列表 / 详情关系；
- 图表、Canvas、图片；
- Modal / Drawer；
- 颜色、视觉选中态和明显布局异常；
- DOM 无法解释的视觉差异。

不要让 Vision 重复枚举 DOM 已经能准确识别的按钮和文本。

## 2. Feature Inventory：先建立功能清单

Initial Observation 后，先在内部建立 Feature Inventory，再开始交互。

对每个有意义的 Area 至少识别：

```text
Area
Control / Interaction Surface
Interaction Type
Stateful? yes/no
Input or Filter? yes/no
Safety: safe / gray / unsafe
Priority: high / medium
Known Effect
Unknown Relation
```

High-value Area 通常包括：

- Search；
- Filter；
- Sort；
- Pagination；
- Page Size；
- Tab；
- 主要表单；
- 会改变业务数据视图或核心页面状态的控件。

Logo、Footer 等静态内容通常不是高价值探索目标。

## 3. Application Map：记录状态关系，不只是元素列表

Application Map 描述“什么操作会影响什么状态”。例如：

```text
Source Filter --changes--> News List
Source Filter --changes--> Total Pages
Page Size --changes--> Visible Item Count
Search --?--> Result State
```

关系可以是：

```text
--changes-->           已观察到稳定变化
--no observable effect--> 多次 Probe 后未观察到效果
--?-->                 仍未知，需要继续探索
```

Application Map 是 Agent 的工作模型，不要求落盘为 JSON。

## 4. Exploration Planner：先产生 Mission，再执行

未知系统使用 **Exploration Mission**，不要一开始就生成正式 Test Case。

每个 Mission 至少回答：

```text
Goal：想确认什么？
Why：为什么有信息价值？
Target：哪个 Area / Control？
Probe：准备怎么操作？
Observe：重点比较哪些状态关系？
```

Planner 每轮只选择当前信息价值最高的下一 Mission，优先级：

```text
1. Unknown state relation
2. Suspicious behavior needing confirmation
3. Uncovered high-value interaction
4. Edge coverage for Input / Filter
5. Meaningful stateful combination
6. Medium-value secondary functionality
```

## 5. 三种探索视角

不创建多个 Agent。由同一个 Agent 对适用功能使用三个 Lens。

### Normal

正常用户最自然的使用方式。

例如：

```text
搜索当前页面真实存在的企业名
选择一个真实来源筛选
Page 1 → Page 2 → Page 1
```

### Edge

选择高信息量、安全的边界或反例。

例如：

```text
搜索明确不存在的随机字符串
空输入
安全范围内的边界长度
Reset / Revert
```

不要为了“覆盖率”做无意义的大量 fuzz。

### Combination

组合会影响相同或相关业务状态的 Stateful Controls，例如：

```text
Filter + Search
Page Size + Pagination
Search + Pagination
```

禁止做控件全排列。只有存在合理状态依赖时才组合。

## 6. Mission 执行循环

每个重大交互必须遵守：

```text
Before
  ↓
Action
  ↓
After
  ↓
Delta
  ↓
Interpret
```

重大交互包括：Search submit、Filter、Pagination、Tab、Page Size、Modal、同源导航，以及明确安全的表单操作。

每次重大交互后重新读取相关 DOM / Accessibility 状态，再决定下一步。不要连续执行多个动作后才统一观察。

### Exploration Ledger

在当前上下文维护轻量 Ledger：

```text
Area | Mission | Action | Delta | Result
```

用途：

- 防止重复路径；
- 选择下一 Mission；
- 计算 Coverage；
- 最终输出 Reproduction Path。

不要求额外 JSON / JSONL 文件。

## 7. URL-only 的隐式 Oracle

没有正式 Requirement 时，不制造精确 Expected。优先使用以下关系判断一致性。

### UI Semantic Oracle

控件文案、label、role 提供弱到中等强度语义。例如“标题/企业名 + 查询”意味着提交不同查询后应该存在与查询有关的可观察反馈，但不能据此猜精确返回条数。

### Metamorphic Relation

URL-only 场景最重要的 Oracle。

不知道精确正确值时，比较不同输入之间应该存在的合理关系。例如：

```text
Query A = 页面真实存在的企业名
Query B = 明确不存在的随机字符串
```

若 A 与 B 在列表、分页、结果提示和相关 Network 行为上长期完全相同，应提升异常优先级。

### State Invariant

同一功能内部状态应一致，例如 Page Indicator、selected、disabled 与实际展示数据不能互相矛盾。

### Cross-feature Consistency

组合状态之间应保持一致，例如选择某来源后，当前列表来源不应大面积与筛选值矛盾。

### Reversibility

可逆操作恢复后，核心状态应合理恢复，例如：

```text
All → IT桔子 → All
```

### Health Signals

重大交互后按需观察：visible error、`role=alert`、stuck loading、spinner、`aria-busy`、明显 Console Error；必要时检查 Network 4xx / 5xx。

### UX Contract

空状态、错误提示、加载反馈等常见 UX 约定只能作为弱 Oracle。单独使用时通常只能支持 `SUSPECTED_ANOMALY`。

## 8. 可疑行为必须确认，不要立刻 Q / BLOCKED

发现可疑现象后：

```text
Suspicious Observation
  ↓
Confirmation Probe
  ↓
Re-observe
  ↓
Classify Finding
```

Confirmation Probe 优先：

- 换一个输入；
- 换一个路径；
- 换一个组合状态；
- 恢复稳定初始状态后重试。

例如 Search 第一次无变化，不要马上结束。至少尝试一个语义明显不同的安全输入；必要时再做 `Filter + Search`。

## 9. Finding 分类

URL-only 模式不直接使用正式测试的 PASS / FAIL。

### `CONFIRMED_BEHAVIOR`

直接 Evidence 支持的稳定用户可观察行为或状态关系。

### `STRONG_ANOMALY`

至少同时满足：

1. UI Semantic / Metamorphic / State Invariant / Cross-feature 等关系出现明显不一致；
2. 已执行至少一次不同输入、路径或组合的安全 Confirmation Probe；
3. 可疑行为仍能稳定观察。

它表示“高度值得人工确认”，**不等价于正式 Requirement 下的 FAIL**。

### `SUSPECTED_ANOMALY`

存在异常信号，但仍有多个合理业务解释。

### `UNKNOWN`

当前证据、权限、安全边界或环境不足以判断。

## 10. Evidence Escalation：先便宜，异常时再加证据

```text
普通行为
→ DOM / Accessibility

可疑
→ Repeat Probe + DOM Delta

仍可疑
→ Screenshot / Network / Console / Trace（按需）
```

不要所有 Mission 一开始就抓全量 Trace、Network 和 Vision。

## 11. Coverage Gate：没覆盖够，不允许正常结束

默认 Hard Limit：

```text
max_depth = 2
max_interactions = 30
```

它们只是预算上限，不是“探索完成”的条件。

正常完成必须满足：

1. 每个安全的 High-value Interactive Area 至少完成 1 个 Normal Mission；
2. 每个安全的 Input / Filter 至少完成 1 个高信息量 Edge Mission；
3. 如果存在至少 2 个安全 Stateful Controls，至少完成 2 个有意义的 Combination Missions；
4. 每个 Suspicious Observation 至少完成 1 个安全 Confirmation Probe；无法安全确认时必须记录 Coverage Gap / UNKNOWN。

### Area Saturation

若当前 Area 连续约 3 个安全 Probe 都没有得到新的状态关系、未知信息或异常证据：

```text
Current Area Saturated
  ↓
记录已探索内容
  ↓
恢复稳定状态
  ↓
切换到 Coverage Gap 最大的其他 Area
```

**Area 饱和不能作为整个 Exploration 的结束条件。**

真正允许 `COMPLETED` 的条件：

```text
Coverage Gate satisfied
AND
没有仍需要安全 Confirmation Probe 的 unresolved suspicious behavior
```

Hard Limit 先耗尽但 Coverage Gate 未满足，只能输出 `PARTIAL`。

运行状态：

- `COMPLETED`：Coverage Gate 满足；
- `PARTIAL`：预算耗尽但仍有 Coverage Gap；
- `BLOCKED`：页面、登录、权限、必要环境或安全限制阻止关键探索。

## 12. 安全边界

可以自动探索：

- Search、Filter、Tab、Pagination、Page Size；
- Dropdown、Accordion、Tooltip / Hover；
- Modal 打开 / 关闭；
- Read-only navigation；
- 同一 Origin 内普通非破坏性导航。

灰区操作默认只记录入口，不执行：

- Save、Create、Sync、Submit、Confirm、Send。

除非能够明确确认当前环境安全且操作可逆。

默认禁止：

- Delete；
- Payment；
- Publish；
- Password / Account change；
- Real transaction；
- Unknown file upload；
- Production task；
- 其他明显不可逆或影响真实业务数据的行为。

Unsafe Area 不计入强制 Coverage，但必须写入最终报告说明未探索原因。

## 13. SPA、外部链接和深度

SPA 状态不能只看 URL。综合比较 DOM / Accessibility Delta、visible text、selected / disabled、dialog、list、count、pagination，必要时 Network。

外部 Origin 默认只确认存在外部跳转能力，不深入第三方站点。

默认深度：

```text
Depth 0：输入页面
Depth 1：直接核心状态 / 子页面
Depth 2：核心功能下一层状态
```

达到 Depth 2 是预算边界，不代表其他未覆盖 Area 可以忽略。

## 14. 主要输出：`exploration-report.md`

推荐结构：

```markdown
# Exploratory Testing Report

**运行状态：COMPLETED | PARTIAL | BLOCKED**

## 1. Application Overview
## 2. Application Map
## 3. Confirmed Behaviors
## 4. Strong Anomalies
## 5. Suspected Anomalies
## 6. Unknown / Unsafe Areas
## 7. Exploration Coverage
## 8. Reproduction Paths
```

Confirmed Behavior 使用 `BEH-*`。

Anomaly 使用 `ANOM-*`，每条至少包含：

- 现象；
- 关键 Probe / Reproduction Path；
- Before / After 差异；
- 使用的 Implicit Oracle；
- Evidence；
- 分类。

Coverage 至少包含：

```markdown
| Area | Normal | Edge | Combination | Result |
|---|---|---|---|---|
| Search | ✓ | ✓ | ✓ | Strong anomaly |
| Source Filter | ✓ | ✓ | ✓ | Confirmed |
| Pagination | ✓ | N/A | ✓ | Confirmed |
```

## 15. 可选导出 `requirements.md`

只有用户明确需要，或探索结束后需要沉淀候选需求时，才额外生成 `requirements.md`。

候选需求主要来自：

```text
Confirmed Behaviors
+
UI Semantics
+
稳定 State Relations
```

可继续使用 `REQ-* / INF-* / Q-*`，但必须遵守：

- 当前异常行为不能因为“页面现在就是这样”而写成正式 Requirement；
- `STRONG_ANOMALY` 不是正式 Expected；
- 未经人工或正式需求确认的候选需求，不应直接进入正式 PASS / FAIL 测试合同。

如果后续人工确认了需求，再交给 `test-design` 生成正式 Test Suite。

## 禁止事项

- 不把当前产品行为自动当成正式业务真理；
- 不为了 URL-only 测试强制先生成 `requirements.md → test-cases.json`；
- 不把 `STRONG_ANOMALY` 伪装成正式 FAIL；
- 不因为连续几次没有新 Fact 就结束整个探索；
- 不做控件全排列组合；
- 不创建 Multi-agent、LangGraph、Supervisor、SQLite / DB 或持久化 Memory；
- 不创建 Application Map JSON Schema、Exploration Ledger JSON 或 Action Tape JSONL；
- 不自研 Browser Engine、Crawler 或 Selector Engine；
- 不默认生成 Playwright reproduction code；
- 不修改 `test-design`、`test-orchestrator` 的 Expected 和公共 JSON 契约。
