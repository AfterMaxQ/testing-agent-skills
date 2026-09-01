# Requirement Discovery 设计文档

日期：2026-09-01

## 1. 背景

当前 Testing Agent Skills 已形成一条稳定链路：

```text
需求 / PRD
  ↓
test-design
  ↓
test-cases.json
  ↓
test-orchestrator
  ↓
Browser / API / Log-Trace / Static Inspection
  ↓
Evidence
  ↓
Report
```

现有 `test-design` 的前提是：需求已经存在，并且需求是 Expected 的事实来源。

现在需要补充一条新的前置能力：当只有一个已经运行的 Web 页面、没有正式需求文档时，Agent 可以先观察现有产品，从页面中提取候选需求，生成普通 Markdown 需求文档，再交给现有 `test-design`。

该能力命名为：`requirement-discovery`。

## 2. 目标

新增独立 Skill：

```text
skills/requirement-discovery/SKILL.md
```

它负责：

```text
运行中的网页
  ↓
DOM / Accessibility 主观察
  +
Vision 补充
  +
少量安全交互
  ↓
页面事实
  ↓
功能需求 / 推断需求 / 待确认项
  ↓
requirements.md
```

`requirements.md` 是普通 Markdown 文档，可由人直接阅读、修改，也可以继续作为 `test-design` 的输入。

## 3. 非目标

第一版不做以下事情：

- 不生成 `test-cases.json`；
- 不生成 Playwright Test；
- 不生成 Locator 或测试代码；
- 不新增 JSON Schema；
- 不新增 Requirement Validator；
- 不实现新的 Browser Crawler；
- 不实现新的截图、DOM 或 Selector 工具；
- 不修改 `test-orchestrator`；
- 不建立数据库、状态服务或额外执行框架；
- 不进行 Bug 根因分析；
- 不把整个站点爬完。

浏览器能力直接复用现有 `playwright-cli` Skill。

## 4. 与现有 Skill 的职责边界

### `requirement-discovery`

回答：

> 当前产品页面表现出了哪些可以被观察和验证的候选需求？

输出：`requirements.md`。

### `test-design`

回答：

> 根据已经给定的需求，应该设计哪些测试场景、断言和运行条件？

输出：`test-cases.json`。

### `playwright-cli`

回答：

> 浏览器具体怎么打开、观察、点击、读取 DOM、截图和比较状态？

负责实际 Browser 操作。

### `test-orchestrator`

继续负责测试执行阶段的 Preflight、Provision、Reflight、Evidence 和 Report。

因此新增后的两条入口为：

```text
正式 PRD ───────────────► test-design
                              │
网页 ► requirement-discovery ┘
          │
          ▼
    requirements.md
          │
          └──────────────► test-design
```

## 5. 页面观察策略

采用：**DOM-first + Vision fallback / 补充**。

### 5.1 DOM / Accessibility 为主

优先使用 Playwright Snapshot / Accessibility 信息识别：

- heading；
- button；
- link；
- textbox；
- checkbox；
- radio；
- combobox；
- tab；
- table；
- list；
- dialog；
- navigation；
- 可见文字；
- selected / disabled / required 等对用户有直接影响的状态。

优先级：

```text
Accessibility / Snapshot
  > Rendered DOM
  > Raw HTML
```

只有需要确认 `maxlength`、`minlength`、`required`、`disabled`、`pattern` 等具体属性时，才针对目标元素读取 DOM 属性。

### 5.2 Vision 作为补充

视觉能力主要补充 DOM 不擅长表达的信息：

- 页面主要区域和布局关系；
- 列表 / 详情等视觉层级；
- 图表、Canvas 和图片内容；
- Modal / Drawer 等视觉结构；
- 颜色、选中态等视觉状态；
- DOM 难以解释的页面变化。

不要让 Vision 重复枚举 DOM 已经能准确识别的按钮、输入框和文本。

视觉推断不能在缺少其他证据时直接升级成高可信业务需求。

### 5.3 Safe Interaction

允许自动探索的典型操作：

- Tab 切换；
- Accordion 展开 / 收起；
- 分页；
- 查看一个代表列表项的详情；
- 非破坏性搜索和筛选；
- Dropdown 展开；
- Modal 打开 / 关闭；
- Tooltip / Hover；
- 同一应用内的普通导航。

默认不自动执行：

- 删除；
- 支付；
- 发布；
- 发送消息；
- 修改密码；
- 注销 / 删除账号；
- 真实交易；
- 上传未知文件；
- 生产任务；
- 其他明显不可逆或影响真实业务数据的操作。

对 `保存`、`提交`、`确认`、`创建`、`发送`、`同步` 等灰区操作，第一版默认只记录入口，不执行，除非能够明确确认环境安全且操作可逆。

## 6. 从 Evidence 到 Requirement

必须经过下面的逻辑：

```text
Evidence
  ↓
Fact
  ↓
Requirement / Inference / Question
```

不要从截图或页面状态直接跳到正式需求。

### 6.1 功能需求 `REQ-*`

只有页面有直接证据支持时才能写入。

典型证据包括：

- DOM / Accessibility；
- 页面明确文字；
- 元素属性形成的用户可观察约束；
- 安全交互前后的明确状态变化。

每条 `REQ-*` 必须回答：

> 我凭什么这么说？

无法给出直接页面证据时，不得放入确定需求。

### 6.2 推断需求 `INF-*`

当现有页面存在较强迹象，但无法证明它一定属于正式产品要求时，放入推断需求。

例如：

- 当前分类具有明显高亮；
- 页面存在“删除”入口，但为了安全未实际执行；
- 视觉上存在某种状态含义，但页面没有明确文案确认。

推断需求必须说明：

- 推断内容；
- 推断依据；
- 为什么不能升级为确定需求；
- 可信度。

### 6.3 待确认项 `Q-*`

页面不足以判断的规则进入待确认项。

例如：

- 默认排序规则；
- 固定分页数量；
- 数据刷新频率；
- 性能要求；
- 后端持久化方式；
- 内部并发、重试或 fallback 规则。

## 7. 防止“产品现状 = 需求”

第一版强制遵守以下规则。

### 7.1 当前值不能自动成为固定规则

看到当前页面有 10 条数据，不能直接生成：

> 每页必须显示 10 条。

除非页面文字、控件或交互能够明确证明 10 是规则，否则进入待确认项。

### 7.2 用户可观察约束可以成为候选需求

例如：

```html
<input maxlength="20">
```

该属性直接限制用户输入，因此可以支持“输入长度上限为 20”的候选需求。

但看到：

```text
POST /api/v1/news
```

默认不能生成“产品必须使用 POST /api/v1/news”，因为这是内部实现，而不是用户可观察要求。

### 7.3 模糊视觉解释不得直接成为高可信需求

例如视觉模型看到红色圆点，只能说明“可能表示异常”。

如果 Accessibility / DOM 同时出现 `aria-label="异常"` 等明确语义，才可以提升可信度。

## 8. 页面探索流程

一次 Discovery 固定按以下顺序执行。

### Step 1：打开目标页面

使用现有 `playwright-cli` 打开运行中的页面。

### Step 2：建立 Initial Snapshot

在不执行交互的情况下，收集主要页面结构和可交互元素。

### Step 3：做一次初始视觉补充

截图主要用于理解布局、视觉层级、图表、Canvas、状态色和 DOM 难以表达的结构。

### Step 4：形成初始页面 Facts

例如：

```text
F001 页面存在“快讯资讯”标题
F002 页面存在搜索输入框
F003 页面存在多个分类 Tab
F004 页面存在快讯列表
```

Facts 是 Agent 内部工作信息，不要求单独落盘。

### Step 5：识别安全交互类型

按交互类型探索代表行为，而不是按元素数量穷举。

例如存在 20 个同构列表项时，只选一个代表项确认“列表项可查看详情”。

### Step 6：每次交互比较 Before / Action / After

```text
Before
  ↓
Action
  ↓
After
  ↓
Delta
```

只有状态变化揭示了新产品行为时，才新增 Fact。

### Step 7：必要时再次调用 Vision

仅在以下情况重新使用视觉：

- 页面结构发生明显变化；
- 新出现 Modal / Drawer；
- 出现图表、Canvas 或图片；
- DOM 无法解释状态差异；
- 视觉状态本身就是功能的一部分。

普通 DOM 状态变化不需要每次截图重新分析。

### Step 8：满足停止条件后生成 Markdown

第一版使用简单停止条件：

- 所有主要安全交互类型至少探索一个代表；或
- 连续多次安全交互没有发现新的功能事实；或
- 达到最大探索深度；或
- 达到最大交互次数。

建议默认：

```text
max_depth = 2
max_interactions = 20
no_new_fact_limit = 3
```

这些是默认探索边界，不需要额外配置系统。

## 9. 探索范围

### 9.1 深度

默认只探索当前页面及其核心下一层状态：

```text
Depth 0：输入页面
Depth 1：当前页面直接可到达的核心状态
Depth 2：核心功能的下一层状态
```

达到 Depth 2 后停止继续向更远页面扩散。

### 9.2 外部链接

同一应用 / 同一 Origin 内的安全导航可以继续探索。

外部 Origin 默认只记录“存在外部跳转能力”，不继续深入外部站点。

### 9.3 SPA

不能只根据 URL 是否变化判断新状态。

应结合：

- Snapshot / Accessibility Delta；
- 可见文字变化；
- selected 状态；
- Dialog 状态；
- DOM 变化；
- 必要时的 Network 信息。

## 10. 输出格式

输出文件为普通 Markdown：`requirements.md`。

建议结构：

```markdown
# <页面 / 功能名称>需求

> 本文档根据当前运行中的产品页面反向提取，不等同于正式产品需求。

## 页面概述

<页面主要用途和当前能够观察到的功能区域>

## 功能需求

### REQ-001 <标题>

<需求描述>

**页面证据**

- DOM：...
- Interaction：...
- Vision：...

**可信度：高**

## 推断需求

### INF-001 <标题>

**推断**

...

**依据**

- ...

**为什么不是确定需求**

...

**可信度：中**

## 待确认项

### Q-001 <标题>

<当前页面无法确认的内容>
```

要求：

- `REQ-*`、`INF-*`、`Q-*` 分区，不得混写；
- 每条确定需求必须包含页面证据；
- Evidence 简单标注来源：DOM、Interaction、Vision；
- 不要求输出内部 Facts 列表；
- 不要求 JSON 中间态。

## 11. 与 `playwright-cli` 的复用方式

`requirement-discovery` 声明：

```text
REQUIRED SUB-SKILL: playwright-cli
```

由 `playwright-cli` 负责：

- 打开页面；
- Snapshot；
- 元素识别；
- 安全交互；
- DOM 属性读取；
- Screenshot；
- Browser Session；
- 页面状态观察。

`requirement-discovery` 只定义：

- 为什么探索；
- 探索什么；
- 哪些操作安全；
- 如何把 Evidence 转成 Facts；
- 如何把 Facts 分类成 REQ / INF / Q；
- 什么时候停止。

不重新包装或复制 Playwright CLI 的具体命令文档。

## 12. 第一版目录变化

只新增：

```text
skills/
├── requirement-discovery/
│   └── SKILL.md
├── test-design/
├── test-orchestrator/
└── playwright-cli/
```

必要时同步更新：

```text
README.md
USAGE.md
```

第一版不新增其他运行时代码。

## 13. 实际运行示例

输入：一个已经运行的“快讯资讯”页面。

初始 Snapshot 发现：

```text
heading "快讯资讯"
textbox "搜索快讯"
tab "全部" selected
tab "国内"
tab "国际"
多个快讯列表项
button "下一页"
```

安全探索：

1. 切换“国际”Tab，列表内容变化；
2. 点击一个代表快讯，出现详情；
3. 在搜索框输入关键词，列表变化；
4. 点击“下一页”，列表变化。

最终可能生成：

```text
REQ-001 用户可以查看快讯列表
REQ-002 用户可以查看快讯详情
REQ-003 用户可以切换快讯分类
REQ-004 用户可以搜索快讯
REQ-005 用户可以分页浏览快讯

INF-001 当前分类应具有明显选中状态

Q-001 快讯默认排序规则
Q-002 单页固定条数
Q-003 数据刷新规则
```

如果页面存在“删除”“发布”等入口，默认不执行，只根据可见证据决定是否记录为推断需求。

## 14. 第一版验收标准

第一版只要求满足以下五点：

1. 给定一个正常运行的 Web 页面，可以独立生成可读的 `requirements.md`；
2. 页面主要功能不能明显漏掉，同构重复元素不穷举；
3. 每个 `REQ-*` 都必须包含直接页面证据；
4. 无法证明的规则必须进入 `INF-*` 或 `Q-*`，不能伪装成确定需求；
5. Discovery 不执行明显危险、不可逆或影响真实业务数据的操作。

## 15. DOM 与 Vision 效果比较

组长提出需要实测多模态视觉与元素定位的效果。

第一版不建设额外 Benchmark 平台，直接选择若干真实页面，对比三种运行方式：

```text
A. DOM / Accessibility only
B. Vision only
C. DOM-first + Vision
```

人工比较最终需求文档的：

- 主要功能漏检；
- 错误需求；
- 无依据推断；
- 页面结构理解；
- 后续是否容易交给 `test-design`。

最终推荐方案仍为 `DOM-first + Vision`，但以真实页面结果验证该判断。

## 16. 设计原则总结

第一版坚持：

```text
少新增东西
复用 playwright-cli
DOM-first
Vision 补充
安全探索
Evidence → Fact → Requirement
REQ / INF / Q 分离
普通 Markdown 输出
不侵入现有测试执行链路
```

目标不是构建一个完整的产品逆向工程平台，而是给现有 Testing Agent 补上一个轻量、可信、可人工审核的“网页 → 候选需求”入口。
