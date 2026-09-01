# Exploratory Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the URL-only `requirement-discovery` flow with a lightweight `exploratory-testing` Skill that dynamically maps, plans, explores, probes anomalies, enforces coverage, and produces `exploration-report.md` without forcing `requirements.md → test-cases.json` before testing.

**Architecture:** Keep the formal requirement-driven path unchanged (`test-design → test-orchestrator`). For URL-only input, rename `requirement-discovery` to `exploratory-testing` and implement the approved Application Map → Exploration Missions → Observe/Update → Coverage Gate loop entirely as Skill-level guidance on top of the existing `playwright-cli`. `requirements.md` becomes an optional post-exploration export rather than a required intermediate contract.

**Tech Stack:** Markdown Agent Skills, existing Microsoft Playwright CLI Skill, existing repository documentation. No new runtime dependency, Python/TypeScript module, JSON Schema, database, LangGraph, multi-agent framework, crawler, or browser engine.

**Spec:** `docs/superpowers/specs/2026-09-01-exploratory-testing-design.md`

## Global Constraints

- Rename `skills/requirement-discovery/` to `skills/exploratory-testing/`; the active Skill frontmatter name must be exactly `exploratory-testing`.
- URL-only exploration must not require `requirements.md → test-design → test-cases.json` before interacting with and testing the application.
- Formal Requirement / PRD / AC input continues to use the existing `test-design → test-orchestrator` path unchanged.
- `exploratory-testing` must continue to declare `playwright-cli` as its required browser sub-skill and must not reimplement browser execution.
- Initial observation remains `Accessibility / Snapshot > Rendered DOM > Raw HTML`; Vision is supplemental, not the primary enumerator.
- The exploration protocol must include Feature Inventory, Application Map, Exploration Missions, Normal / Edge / Combination lenses, Before / Action / After / Delta, a lightweight Exploration Ledger, Confirmation Probes, implicit oracles, and a Coverage Gate.
- `max_depth = 2` and `max_interactions = 30` are hard exploration budgets, not successful-completion conditions.
- Area saturation must switch to a different uncovered area; it must not terminate the entire exploration by itself.
- Normal completion requires the Coverage Gate to be satisfied and no unresolved suspicious behavior that still needs a safe Confirmation Probe.
- URL-only finding classes are `CONFIRMED_BEHAVIOR`, `STRONG_ANOMALY`, `SUSPECTED_ANOMALY`, and `UNKNOWN`; do not relabel these as formal PASS / FAIL.
- URL-only run status is `COMPLETED`, `PARTIAL`, or `BLOCKED`.
- Primary URL-only output is `exploration-report.md`; `requirements.md` is optional after exploration.
- Keep the existing destructive-action safety boundary. Unsafe areas are reported but excluded from mandatory coverage.
- Do not modify Test Suite `1.4`, Test Context `1.2`, Readiness `1.0`, Report `1.3`, Secret Resolver, Preflight, Provision, Reflight, or public JSON schemas.
- Do not add Multi-agent, LangGraph, Supervisor, SQLite / DB, Persistent Memory, Application Map JSON Schema, Exploration Ledger JSON, custom Browser Engine, custom Crawler, custom Selector Engine, Action Tape JSONL, automatic reproduction code generation, or combinatorial exhaustive testing.

---

### Task 1: Replace `requirement-discovery` with `exploratory-testing`

**Files:**
- Create: `skills/exploratory-testing/SKILL.md`
- Delete: `skills/requirement-discovery/SKILL.md`
- Reference only: `skills/playwright-cli/SKILL.md`
- Reference only: `docs/superpowers/specs/2026-09-01-exploratory-testing-design.md`

**Interfaces:**
- Consumes: a running Web URL plus `playwright-cli` browser capabilities.
- Produces: `exploration-report.md` as the primary artifact; optionally `requirements.md` after exploration.
- Does not produce: formal `test-cases.json`, formal PASS/FAIL judgments, or changes to `test-orchestrator` contracts.

- [ ] **Step 1: Verify the old Skill exists and the new Skill does not yet exist**

Run from repository root:

```bash
python -c "from pathlib import Path; assert Path('skills/requirement-discovery/SKILL.md').is_file(); assert not Path('skills/exploratory-testing/SKILL.md').exists(); print('precondition ok')"
```

Expected: prints `precondition ok`.

- [ ] **Step 2: Read the approved spec and current old Skill before editing**

Read completely:

```text
docs/superpowers/specs/2026-09-01-exploratory-testing-design.md
skills/requirement-discovery/SKILL.md
skills/playwright-cli/SKILL.md
```

Do not copy the old `REQ / INF / Q → requirements.md` flow as the new primary flow. Preserve only still-valid pieces: DOM-first observation, Vision supplement, safe interactions, SPA awareness, external-origin boundary, and destructive-action safeguards.

- [ ] **Step 3: Create the new Skill with the new identity and purpose**

Create `skills/exploratory-testing/SKILL.md` with frontmatter equivalent to:

```yaml
---
name: exploratory-testing
description: Use when 只有一个已经运行的 Web 页面或 URL、缺少正式 Requirement / PRD / AC，需要 Agent 自主建立应用地图、规划探索任务、执行探索式测试、识别异常并输出 exploration-report.md 时。
---
```

The opening contract must explicitly state:

```text
REQUIRED SUB-SKILL: playwright-cli

This Skill is for URL-only / unknown-expected exploration.
It does not replace test-design for formal requirements.
It does not require requirements.md or test-cases.json before exploration begins.
```

The top-level flow in the Skill must be:

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

- [ ] **Step 4: Implement the observation and Application Map rules in the Skill**

The Skill must state these exact priority and responsibilities:

```text
Accessibility / Snapshot > Rendered DOM > Raw HTML
DOM / Accessibility = semantic controls, visible text, selected/disabled/required state
Vision = layout, visual hierarchy, list/detail relation, charts/canvas/images, modal/drawer, visual state, layout anomaly
```

Initial observation must first build a **Feature Inventory**, not immediately click controls. For each meaningful area, the Agent should internally identify at least:

```text
Area
Control / interaction surface
Interaction type
Stateful? yes/no
Input or Filter? yes/no
Safety: safe / gray / unsafe
Priority: high / medium
Known effect
Unknown relation
```

The **Application Map** must represent observed state relations rather than only UI elements, for example:

```text
Source Filter --changes--> News List
Source Filter --changes--> Total Pages
Page Size --changes--> Visible Item Count
Search --?--> Result State
```

No JSON persistence is required.

- [ ] **Step 5: Implement Exploration Planner and Mission rules**

The Skill must define an `Exploration Mission` as a lightweight dynamic objective, not a formal Test Case. Each Mission should internally answer:

```text
Goal
Why this is informative
Target area/control
Probe/action
What state or relationship to observe
```

For each applicable high-value feature, use three exploration lenses without spawning separate agents:

```text
Normal       = ordinary user behavior
Edge         = high-information boundary / empty / non-existing / invalid-but-safe behavior
Combination  = representative interaction between stateful controls that affect the same or related state
```

Combination selection must explicitly avoid Cartesian-product explosion. Prefer combinations where both controls affect the same business state, e.g. `Filter + Search` or `Page Size + Pagination`.

Planner priority must be written as:

```text
1. Unknown state relation
2. Suspicious behavior needing confirmation
3. Uncovered high-value interaction
4. Edge coverage for Input / Filter
5. Meaningful stateful combination
6. Medium-value secondary functionality
```

- [ ] **Step 6: Implement the execution loop and lightweight Exploration Ledger**

Every significant interaction must follow:

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

After significant actions such as Search submit, Filter change, Pagination, Tab, Page Size, Modal open, navigation, or safe form submission, re-read the relevant DOM / Accessibility state before planning the next action.

The Skill must require an internal lightweight ledger with the logical columns:

```text
Area | Mission | Action | Delta | Result
```

The ledger is used for deduplication, next-Mission planning, coverage accounting, and final reproduction-path summaries. It must **not** require a JSON / JSONL file.

- [ ] **Step 7: Implement implicit oracles, anomaly handling, and evidence escalation**

The Skill must define these implicit oracles for URL-only testing:

```text
UI Semantic Oracle
Metamorphic Relation
State Invariant
Cross-feature Consistency
Reversibility
Health Signals
UX Contract (weak oracle only)
```

`Metamorphic Relation` must be emphasized for unknown-expected testing: compare meaningfully different safe inputs rather than requiring an exact expected count/value.

A suspicious observation must not immediately become a strong anomaly. Require:

```text
Suspicious Observation
  ↓
Confirmation Probe using a different input, path, combination, or reset state
  ↓
Re-observe
  ↓
Classify Finding
```

Finding classes must be:

```text
CONFIRMED_BEHAVIOR
STRONG_ANOMALY
SUSPECTED_ANOMALY
UNKNOWN
```

A `STRONG_ANOMALY` requires both a meaningful consistency/semantic/metamorphic violation and at least one successful safe Confirmation Probe that reproduces the suspicious behavior.

Evidence escalation must be:

```text
ordinary behavior → DOM / Accessibility
suspicious → repeat probe + DOM Delta
still suspicious → Screenshot / Network / Console / Trace only when useful
```

- [ ] **Step 8: Implement Coverage Gate and stopping semantics**

The Skill must distinguish hard budgets from completion criteria.

Hard budgets:

```text
max_depth = 2
max_interactions = 30
```

Coverage Gate for normal completion:

```text
1. Every safe high-value interactive area: at least 1 Normal Mission.
2. Every safe Input / Filter: at least 1 high-information Edge Mission.
3. If at least 2 safe Stateful Controls exist: at least 2 meaningful Combination Missions.
4. Every Suspicious Observation: at least 1 safe Confirmation Probe, or explicitly record why it could not be confirmed.
```

Area saturation rule:

```text
approximately 3 safe probes with no new relation, unknown-resolution, or anomaly evidence
→ mark current area saturated
→ restore a stable state
→ switch to the highest-value uncovered area
```

Area saturation must not terminate the whole run.

Normal completion condition:

```text
Coverage Gate satisfied
AND
no unresolved suspicious behavior still requiring a safe Confirmation Probe
```

If hard budget is exhausted before coverage is satisfied, final run status must be `PARTIAL`, not `COMPLETED`.

Run statuses must be:

```text
COMPLETED
PARTIAL
BLOCKED
```

- [ ] **Step 9: Implement output contract and optional requirements export**

Primary output must be `exploration-report.md` with these sections:

```markdown
# Exploratory Testing Report

## 1. Application Overview
## 2. Application Map
## 3. Confirmed Behaviors
## 4. Strong Anomalies
## 5. Suspected Anomalies
## 6. Unknown / Unsafe Areas
## 7. Exploration Coverage
## 8. Reproduction Paths
```

Use `BEH-*` identifiers for confirmed behaviors and `ANOM-*` for anomalies.

Every anomaly entry must include:

```text
Observed phenomenon
Key probes / reproduction path
Before / After difference
Implicit oracle used
Evidence
Classification
```

Coverage section must include a table equivalent to:

```markdown
| Area | Normal | Edge | Combination | Result |
|---|---|---|---|---|
| Search | ✓ | ✓ | ✓ | Strong anomaly |
| Source Filter | ✓ | ✓ | ✓ | Confirmed |
| Pagination | ✓ | N/A | ✓ | Confirmed |
```

At the top or end of the report, explicitly state `COMPLETED`, `PARTIAL`, or `BLOCKED`.

Optional `requirements.md` may be exported **after** exploration from confirmed behaviors, UI semantics, and stable state relations. Preserve `REQ-* / INF-* / Q-*` only for that optional export. Never turn the currently observed anomalous behavior itself into a formal requirement.

- [ ] **Step 10: Preserve the existing safety and boundary rules**

Keep safe automatic exploration for read-only/search/filter/tab/pagination/page-size/dropdown/accordion/tooltip/modal and same-origin non-destructive navigation.

Keep gray operations (`Save`, `Create`, `Sync`, `Submit`, `Confirm`, `Send`) as record-only by default unless the environment is explicitly known safe and reversible.

Keep destructive or externally consequential operations prohibited by default (`Delete`, `Payment`, `Publish`, password/account changes, real transactions, unknown uploads, production tasks).

Unsafe areas are listed in the final report but excluded from mandatory coverage.

- [ ] **Step 11: Remove the old Skill only after the new Skill exists**

Delete:

```text
skills/requirement-discovery/SKILL.md
```

Do not leave two active Skills with overlapping URL-only responsibilities.

- [ ] **Step 12: Run focused structural checks**

Run:

```bash
python -c "from pathlib import Path; p=Path('skills/exploratory-testing/SKILL.md'); s=p.read_text(encoding='utf-8'); assert p.is_file(); assert not Path('skills/requirement-discovery/SKILL.md').exists(); required=['name: exploratory-testing','REQUIRED SUB-SKILL','Application Map','Exploration Mission','Normal','Edge','Combination','Coverage Gate','STRONG_ANOMALY','SUSPECTED_ANOMALY','max_interactions = 30','exploration-report.md']; missing=[x for x in required if x not in s]; assert not missing, missing; print('skill structure ok')"
```

Expected: prints `skill structure ok`.

- [ ] **Step 13: Commit the Skill replacement**

```bash
git add skills/exploratory-testing/SKILL.md skills/requirement-discovery/SKILL.md
git commit -m "feat: replace requirement discovery with exploratory testing"
```

---

### Task 2: Update README and USAGE for the two-mode workflow

**Files:**
- Modify: `README.md` — opening description, architecture diagram, module table, data-flow section, URL-only examples
- Modify: `USAGE.md` — introduction, Skill table, Skill loading paths, URL-only tutorial, recommended prompt, output expectations

**Interfaces:**
- Consumes: the new `skills/exploratory-testing/SKILL.md` contract from Task 1.
- Produces: user-facing documentation that clearly separates formal requirement-driven testing from URL-only exploratory testing.

- [ ] **Step 1: Run a failing documentation check against the old active docs**

Run:

```bash
python -c "from pathlib import Path; files=['README.md','USAGE.md']; bad=[]; good=[]; [bad.append(f) for f in files if 'requirement-discovery' in Path(f).read_text(encoding='utf-8')]; [good.append(f) for f in files if 'exploratory-testing' in Path(f).read_text(encoding='utf-8')]; assert bad and not good, (bad,good); print('old docs confirmed')"
```

Expected: prints `old docs confirmed` before the edits.

- [ ] **Step 2: Rewrite README opening and architecture around two independent entry modes**

The opening must communicate:

```text
Formal Requirement / PRD → test-design → test-orchestrator → PASS/FAIL/BLOCKED
URL only → exploratory-testing → exploration-report.md (+ optional requirements.md)
```

Replace the current URL-only `requirement-discovery → requirements.md → test-design` branch with:

```text
                         User Input
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        Formal Requirement             URL only
                │                       │
                ▼                       ▼
          test-design            exploratory-testing
                │                       │
                ▼                       ▼
          Test Suite              Application Map
                │                       │
                ▼                       ▼
       test-orchestrator         Exploration Missions
                │                       │
                │                Plan ↔ Explore
                │                       │
                ▼                       ▼
             Evidence                Findings
                │                       │
                ▼                       ├─ exploration-report.md
      PASS / FAIL / BLOCKED            └─ optional requirements.md
```

README module table must describe `exploratory-testing` as URL-only application mapping + mission planning + coverage-driven exploration + anomaly reporting, not as a candidate-requirement generator.

State explicitly that `exploratory-testing` is optional and separate from `test-orchestrator`; it does not modify the existing formal Test Suite schemas.

- [ ] **Step 3: Rewrite README URL-only data flow**

Use the new flow:

```text
URL
→ Initial Observation
→ Feature Inventory
→ Application Map
→ Exploration Missions
→ Execute / Observe / Update
→ Coverage Gate
→ exploration-report.md
→ optional requirements.md
```

Do not state that URL-only must next enter `test-design`. Explain that candidate requirements can be manually confirmed later and then passed to `test-design` if the team wants to freeze them into a formal contract.

- [ ] **Step 4: Update USAGE Skill table and loading instructions**

The four active Skill directories shown to users must be:

```text
skills/exploratory-testing/
skills/test-design/
skills/test-orchestrator/
skills/playwright-cli/
```

The Skill table must distinguish:

```text
exploratory-testing = unknown app / unknown expected
 test-design         = known requirement / known expected
```

Remove the instruction that URL-only users should first generate `requirements.md` and then continue the normal test chain.

- [ ] **Step 5: Replace the URL-only tutorial with an exploratory-testing tutorial**

Recommended user prompt in USAGE must be equivalent to:

```text
请先读取并遵守：
- skills/exploratory-testing/SKILL.md
- skills/playwright-cli/SKILL.md

目标页面：<运行中的页面 URL>
主要输出：exploration-report.md

要求：
1. 先建立 Feature Inventory 和 Application Map，不要打开页面后随便点击；
2. DOM / Accessibility 为主要事实源，Vision 只按需补充；
3. 对高价值功能规划 Normal / Edge / Combination Exploration Missions；
4. 每次重大交互使用 Before → Action → After → Delta；
5. 可疑行为必须做 Confirmation Probe；
6. 使用 Coverage Gate 决定是否允许正常结束；
7. 没有正式 Requirement 时不要把 STRONG_ANOMALY 叫做正式 FAIL；
8. 最终输出 exploration-report.md；
9. 只有明确需要时再额外导出 requirements.md。
```

USAGE should include a compact `exploration-report.md` example containing at least: one `BEH-*`, one `ANOM-*`, a Coverage table, and a final `COMPLETED / PARTIAL / BLOCKED` status.

- [ ] **Step 6: Keep the formal requirement-driven tutorial unchanged in semantics**

Do not change:

```text
requirements / PRD
→ test-design
→ Test Suite 1.4
→ Test Context
→ Secret Resolution
→ Preflight / Provision / Reflight
→ Execute
→ Report
```

Do not rename PASS / FAIL / BLOCKED in the formal Test Suite path.

- [ ] **Step 7: Run user-doc consistency checks**

Run:

```bash
python -c "from pathlib import Path; files=['README.md','USAGE.md']; text='\n'.join(Path(f).read_text(encoding='utf-8') for f in files); required=['exploratory-testing','exploration-report.md','Application Map','Coverage Gate','test-design','test-orchestrator']; missing=[x for x in required if x not in text]; assert not missing, missing; assert 'skills/requirement-discovery/' not in text; print('user docs ok')"
```

Expected: prints `user docs ok`.

- [ ] **Step 8: Commit user-facing docs**

```bash
git add README.md USAGE.md
git commit -m "docs: document exploratory testing workflow"
```

---

### Task 3: Update architecture and current implementation documentation

**Files:**
- Modify: `docs/architecture.md` — overall architecture, old Requirement Discovery section, public-contract description
- Modify: `docs/implementation-plan.md` — current implementation entry modes, current exploratory-testing constraints, runtime boundaries
- Keep as historical records: `docs/superpowers/specs/2026-09-01-requirement-discovery-design.md`
- Keep as historical records: `docs/superpowers/plans/2026-09-01-requirement-discovery.md`

**Interfaces:**
- Consumes: the new Skill contract and user-facing architecture established in Tasks 1-2.
- Produces: internal technical docs that describe the repository as it actually exists after the rename.

- [ ] **Step 1: Confirm architecture docs still describe the old flow before editing**

Run:

```bash
python -c "from pathlib import Path; files=['docs/architecture.md','docs/implementation-plan.md']; assert all('requirement-discovery' in Path(f).read_text(encoding='utf-8') for f in files); print('old architecture docs confirmed')"
```

Expected: prints `old architecture docs confirmed`.

- [ ] **Step 2: Replace `Requirement Discovery` architecture with `Exploratory Testing`**

In `docs/architecture.md`, the top-level architecture must show two separate modes, not a merge at `test-design`.

Add an `Exploratory Testing` section that documents:

```text
URL-only purpose
Feature Inventory
Application Map
Exploration Planner / Missions
Normal / Edge / Combination
Before / Action / After / Delta
Confirmation Probe
Implicit Oracles
Coverage Gate
exploration-report.md
optional requirements.md
```

Explicitly state:

```text
exploratory-testing is not part of the public Test Suite / Context / Readiness / Report JSON contracts.
STRONG_ANOMALY is not formal FAIL.
URL-only exploration does not run through test-orchestrator in the first implementation.
```

Keep the formal Test Suite / Context / Secret Resolver / Preflight / Provision / execution-channel / Report sections semantically unchanged.

- [ ] **Step 3: Update the public-contract section without creating a fifth JSON contract**

The public JSON contracts must remain exactly:

```text
skills/test-design/schema.json
skills/test-orchestrator/context.schema.json
skills/test-orchestrator/secret.schema.json
skills/test-orchestrator/readiness.schema.json
skills/test-orchestrator/schema.json
```

State that `exploration-report.md` and optional `requirements.md` are Markdown artifacts, not public JSON schemas.

- [ ] **Step 4: Rewrite `docs/implementation-plan.md` as the current implementation description**

Its entry modes must become:

```text
URL only
  → exploratory-testing
  → exploration-report.md
  → optional requirements.md

Formal Requirement / PRD
  → test-design
  → existing formal execution chain
```

Its `Exploratory Testing` section must summarize the actual v2 constraints:

```text
DOM-first + Vision supplement
Feature Inventory before interaction
Application Map with state relations
Normal / Edge / Combination Missions
Before / Action / After / Delta
implicit oracles
Confirmation Probe
Coverage Gate
max_depth = 2
max_interactions = 30 as hard budgets
COMPLETED / PARTIAL / BLOCKED
primary output exploration-report.md
optional requirements.md after exploration
no new JSON schema / DB / crawler / runner / multi-agent
```

Remove the obsolete active behavior `max_interactions = 20`, `no_new_fact_limit = 3 as global stop`, and `requirements.md → test-design` as the default URL-only route.

- [ ] **Step 5: Preserve historical Superpowers documents as history**

Do not delete or rewrite the old Requirement Discovery spec/plan into pretending the old design never existed. The new design document already states that it supersedes the old URL-only design. Historical Superpowers docs may still contain `requirement-discovery` by design.

- [ ] **Step 6: Run internal-doc consistency checks**

Run:

```bash
python -c "from pathlib import Path; files=['docs/architecture.md','docs/implementation-plan.md']; text='\n'.join(Path(f).read_text(encoding='utf-8') for f in files); required=['exploratory-testing','exploration-report.md','Application Map','Coverage Gate','PARTIAL']; missing=[x for x in required if x not in text]; assert not missing, missing; assert 'skills/requirement-discovery/SKILL.md' not in text; print('architecture docs ok')"
```

Expected: prints `architecture docs ok`.

- [ ] **Step 7: Commit internal docs**

```bash
git add docs/architecture.md docs/implementation-plan.md
git commit -m "docs: align architecture with exploratory testing"
```

---

### Task 4: Repository-wide consistency verification

**Files:**
- Verify only: `skills/exploratory-testing/SKILL.md`
- Verify only: `README.md`
- Verify only: `USAGE.md`
- Verify only: `docs/architecture.md`
- Verify only: `docs/implementation-plan.md`
- Historical exclusion: `docs/superpowers/specs/2026-09-01-requirement-discovery-design.md`
- Historical exclusion: `docs/superpowers/plans/2026-09-01-requirement-discovery.md`
- Verify unchanged: `skills/test-design/schema.json`
- Verify unchanged: `skills/test-orchestrator/context.schema.json`
- Verify unchanged: `skills/test-orchestrator/readiness.schema.json`
- Verify unchanged: `skills/test-orchestrator/schema.json`

**Interfaces:**
- Consumes: all changes from Tasks 1-3.
- Produces: a repository state with one active URL-only Skill and consistent docs, without schema/runtime expansion.

- [ ] **Step 1: Verify active-path references contain no stale `requirement-discovery` references**

Run:

```bash
python -c "from pathlib import Path; files=['README.md','USAGE.md','docs/architecture.md','docs/implementation-plan.md','skills/exploratory-testing/SKILL.md']; hits=[]; [(hits.append(f)) for f in files if 'requirement-discovery' in Path(f).read_text(encoding='utf-8')]; assert not hits, hits; print('no stale active refs')"
```

Expected: prints `no stale active refs`.

Historical Superpowers design/plan documents are intentionally excluded from this check.

- [ ] **Step 2: Verify the new Skill includes every core v2 mechanism**

Run:

```bash
python -c "from pathlib import Path; s=Path('skills/exploratory-testing/SKILL.md').read_text(encoding='utf-8'); required=['Feature Inventory','Application Map','Exploration Mission','Normal','Edge','Combination','Before','After','Delta','Metamorphic','Confirmation Probe','Coverage Gate','COMPLETED','PARTIAL','BLOCKED','exploration-report.md']; missing=[x for x in required if x not in s]; assert not missing, missing; print('core mechanisms present')"
```

Expected: prints `core mechanisms present`.

- [ ] **Step 3: Verify no prohibited new runtime artifacts were added**

Inspect the diff and confirm it contains only the planned Skill/docs paths. In particular there must be no new files matching concepts such as:

```text
application-map.json
exploration-ledger.json
action_tape.jsonl
schema.json under exploratory-testing
*.py under exploratory-testing
*.ts under exploratory-testing
SQLite / DB files
LangGraph configuration
custom crawler/browser engine
```

Run:

```bash
git status --short
git diff --stat HEAD~3..HEAD
```

Expected: only the rename/rewrite Skill and documentation changes from this plan.

- [ ] **Step 4: Verify existing formal test contracts still validate normally**

Do not edit these schemas. Run the existing repository validators against existing examples/fixtures if available. At minimum run:

```bash
python -m py_compile skills/test-design/scripts/validate_testcases.py
python -m py_compile skills/test-orchestrator/scripts/preflight.py
python -m py_compile skills/test-orchestrator/scripts/validate_context.py
python -m py_compile skills/test-orchestrator/scripts/validate_report.py
```

Expected: all commands exit 0. This is a regression guard confirming the URL-only redesign did not disturb formal testing scripts.

- [ ] **Step 5: Run whitespace and repository checks**

```bash
git diff --check
```

Expected: no output and exit 0.

- [ ] **Step 6: Review the final diff against the spec**

Compare the final active files against:

```text
docs/superpowers/specs/2026-09-01-exploratory-testing-design.md
```

Explicitly verify these design decisions are visible in the repository:

```text
Two independent testing modes
URL-only does not require requirements.md/test-cases.json first
Application Map + dynamic Missions
Normal / Edge / Combination
Coverage Gate
Confirmation Probe
Implicit Oracles
COMPLETED / PARTIAL / BLOCKED
STRONG_ANOMALY is not formal FAIL
requirements.md is optional output
No new runtime framework
```

- [ ] **Step 7: Commit any final consistency-only correction if needed**

Only if Step 6 finds a documentation inconsistency, fix that inconsistency and commit:

```bash
git add README.md USAGE.md docs/architecture.md docs/implementation-plan.md skills/exploratory-testing/SKILL.md
git commit -m "docs: finalize exploratory testing consistency"
```

If no correction is needed, do not create an empty commit.
