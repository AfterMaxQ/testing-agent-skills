---
name: requirement-discovery
description: Use when 只有已经运行的 Web 页面、缺少正式需求文档，需要从页面可观察行为中反向提取候选需求并输出 Markdown 需求文档时。
---

# 页面需求发现

## 目标

从当前运行中的 Web 页面提取可观察功能、约束和状态行为，生成普通 Markdown `requirements.md`，供人工阅读、修改，或继续交给 `test-design` 生成 Test Suite。

REQUIRED SUB-SKILL: `playwright-cli`

本 Skill 只负责“从页面发现候选需求”，不负责生成 Test Case、Locator、Playwright Test，也不执行 `test-orchestrator`。

固定链路：

```text
运行中的网页
  ↓
DOM / Accessibility 主观察
  +
Vision 补充
  +
少量安全交互
  ↓
Evidence
  ↓
Fact
  ↓
REQ / INF / Q
  ↓
requirements.md
```

## 页面观察：DOM-first + Vision fallback

页面观察优先级：

```text
Accessibility / Snapshot > Rendered DOM > Raw HTML
```

优先使用 `playwright-cli` 的 Snapshot / Accessibility 信息识别：

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
- selected / disabled / required 等直接影响用户的状态。

只有需要确认 `maxlength`、`minlength`、`required`、`disabled`、`pattern` 等用户可观察约束时，才针对目标元素读取 Rendered DOM 属性。不要默认读取整页 Raw HTML。

Vision 只用于补充 DOM 难以准确表达的信息：

- 页面区域和视觉层级；
- 列表 / 详情关系；
- 图表、Canvas、图片；
- Modal / Drawer 等视觉结构；
- 颜色、选中态等视觉状态；
- DOM 无法解释的明显视觉变化。

不要让 Vision 重复枚举 DOM 已经能够准确识别的按钮、输入框和文本。模糊视觉解释不能单独升级成高可信需求。

## Evidence → Fact → Requirement

先收集页面事实，再生成需求，不要直接从截图或当前页面状态跳到正式需求。

```text
Evidence
  ↓
Fact
  ↓
REQ / INF / Q
```

### `REQ-*`：确定候选需求

只有存在直接页面证据时才能写入。

可接受的直接证据包括：

- DOM / Accessibility；
- 页面明确文字；
- 直接影响用户行为的元素属性；
- 安全交互前后的明确状态变化。

每条 `REQ-*` 必须包含“页面证据”，Evidence 来源只需简单标注：`DOM`、`Interaction`、`Vision`。

### `INF-*`：推断需求

页面存在较强迹象，但无法证明它一定属于正式产品要求时，写入 `INF-*`。

必须说明：

- 推断内容；
- 推断依据；
- 为什么不能升级为确定需求；
- 可信度。

### `Q-*`：待确认项

仅凭当前页面无法确定的业务规则、约束或内部行为，写入 `Q-*`。

典型内容包括：

- 默认排序规则；
- 固定分页数量；
- 数据刷新频率；
- 性能要求；
- 后端持久化方式；
- 内部并发、重试或 fallback 规则。

## 防止把“页面现状”当成“正式需求”

当前页面恰好显示 10 条数据，不等于：

> 每页必须显示 10 条。

除非页面文字、控件或交互明确证明“10”是规则，否则应写入 `Q-*`。

看到：

```text
POST /api/v1/news
```

不等于：

> 产品必须使用 POST /api/v1/news。

内部 API、class 名、框架或实现细节默认不是产品需求。

但：

```html
<input maxlength="20">
```

会直接限制用户输入，因此可以支持“用户输入上限为 20”这类可观察候选需求。

Vision 看到一个红色圆点时，只能记录“可能表示异常”等推断；如果 DOM / Accessibility 同时存在 `aria-label="异常"` 等明确语义，才可以提高可信度。

## 安全探索

允许自动探索的典型操作：

- Tab 切换；
- Accordion 展开 / 收起；
- 分页；
- 查看一个代表列表项的详情；
- 非破坏性搜索 / 筛选；
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
- 注销或删除账号；
- 真实交易；
- 上传未知文件；
- 生产任务；
- 其他明显不可逆或会影响真实业务数据的操作。

`保存`、`提交`、`确认`、`创建`、`发送`、`同步` 等灰区操作默认只记录入口，不执行。只有明确确认当前环境安全且操作可逆时才允许执行。

## 页面探索流程

1. 使用 `playwright-cli` 打开目标页面。
2. 获取 Initial Snapshot，在不交互的情况下识别主要页面结构和交互面。
3. 做一次初始视觉补充，只理解 DOM 难表达的布局、图表、Canvas、图片和视觉状态。
4. 在内部形成 Facts；Facts 不要求单独落盘。
5. 按交互类型选择代表行为，不按元素数量穷举。
6. 每次交互都比较 `Before → Action → After → Delta`，只有发现新的产品行为时才新增 Fact。
7. 只有页面结构明显变化、出现 Modal / Drawer / 图表 / Canvas / 图片、或 DOM 无法解释变化时才再次使用 Vision。
8. 满足停止条件后生成 `requirements.md`。

### 代表交互

存在大量同构元素时，只探索一个代表。

例如 20 个结构一致的快讯条目，只需要选择一个代表项确认“列表项能够打开详情”，不逐条点击。

### SPA 状态

不要只使用 URL 是否变化判断新状态。应综合比较：

- Snapshot / Accessibility；
- DOM；
- 可见文字；
- selected 状态；
- dialog 状态；
- 必要时的 Network 信息。

### 外部链接

同一应用 / 同一 Origin 内的安全导航可以继续探索。

外部 Origin 默认只记录“存在外部跳转能力”，不继续深入外部站点。

## 停止规则

第一版使用简单边界，不增加额外配置系统：

```text
max_depth = 2
max_interactions = 20
no_new_fact_limit = 3
```

满足任一条件即可停止：

- 主要安全交互类型已经各探索至少一个代表；
- 连续 3 次安全交互没有发现新的功能事实；
- 达到 depth 2；
- 达到 20 次交互。

目标是发现当前产品的主要可观察需求，不是把整个站点爬完。

## 输出

最终只输出普通 Markdown `requirements.md`。建议结构：

```markdown
# <页面或功能名称>需求

> 本文档根据当前运行中的产品页面反向提取，不等同于正式产品需求。

## 页面概述

<页面主要用途和当前可观察到的功能区域>

## 功能需求

### REQ-001 <标题>

<需求描述>

**页面证据**

- DOM：直接观察到的结构或文字
- Interaction：安全交互前后的明确变化
- Vision：仅在视觉证据确有必要时写入

**可信度：高**

## 推断需求

### INF-001 <标题>

**推断**

<推断内容>

**依据**

- <页面依据>

**为什么不是确定需求**

<无法直接证明的原因>

**可信度：中**

## 待确认项

### Q-001 <标题>

<当前页面无法确认的规则>
```

要求：

- `REQ-*`、`INF-*`、`Q-*` 分区，不得混写；
- 每条 `REQ-*` 必须有页面证据；
- Evidence 简单标注 `DOM`、`Interaction`、`Vision` 来源；
- 内部 Facts 不要求落盘；
- 不生成 JSON 中间态。

## 与现有 Skill 的边界

`playwright-cli` 负责：

- 打开页面；
- Snapshot；
- 元素识别；
- 安全交互；
- DOM 属性读取；
- Screenshot；
- Browser Session；
- 页面状态观察。

`requirement-discovery` 负责：

- 为什么探索；
- 探索什么；
- 哪些操作安全；
- 如何把 Evidence 转成 Facts；
- 如何把 Facts 分类成 `REQ-*` / `INF-*` / `Q-*`；
- 什么时候停止；
- 如何输出 `requirements.md`。

`requirement-discovery` 到 `requirements.md` 即结束。后续如果要生成 Test Suite，再把该 Markdown 交给 `test-design`。

## 禁止事项

- 不从页面现状反推正式业务真理；
- 不把模糊视觉解释直接升级成高可信需求；
- 不从内部 API、class 名、框架实现细节制造业务需求；
- 不生成 `test-cases.json`；
- 不生成 Locator 或 Playwright Test；
- 不进行 Bug 根因分析；
- 不执行明显危险或不可逆操作；
- 不为了覆盖率遍历所有同构元素；
- 不无限追踪外部链接或深层页面；
- 不修改 `test-design` 或 `test-orchestrator` 的 Expected 与公共 JSON 契约。
