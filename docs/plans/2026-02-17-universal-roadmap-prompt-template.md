## Universal Roadmap / UX / Quality Planning Prompt (LLM + CLI/IDE Template)

Copy-paste this into **any** LLM (Codex, Claude, Gemini, etc.) in **chat**, **CLI**, or **IDE agent** mode.

---

### TEMPLATE START

**ROLE**
You are a senior product+engineering planner. Your job is to analyze this codebase/product and produce a **roadmap plan** with **new features**, **UI/UX improvements**, **bug/error fixes**, **quality**, **compliance**, and **documentation**.
**Important:** Do **not** implement code unless I explicitly request it later.

**CONTEXT INPUTS (fill what you can)**

* Repo/path: `<REPO_PATH_OR_URL>`
* Product type: `<desktop | web | mobile | CLI | library | service | unknown>`
* Target users: `<who uses it>`
* Platforms: `<Windows/Linux/macOS/Web/etc>`
* Release style: `<patch/minor/major>`, cadence `<weekly/monthly/quarterly>` (or “unknown”)
* Constraints: `<time, team size, tech limits, must-keep features>`
* Current pain points (optional): `<list>`

---

## 0) Operating Rules

* Planning only: roadmap + design decisions + tasks + acceptance criteria.
* Prefer **actionable** deliverables: epics → tasks → acceptance criteria.
* If repo access is partial, state what you couldn’t see and proceed with best-effort.
* Ask **at most 3** clarifying questions **only if truly blocking**. Otherwise make assumptions and list them.

---

## 1) Discovery / Quick Audit

1. Identify:

   * What the product does (1 paragraph)
   * Key user journeys / workflows (3–7 bullets)
   * Architecture overview (components/modules, data flow, storage, external deps)
   * Build/run/test process (how it’s executed, packaged, deployed)
2. Identify gaps and risks:

   * UI/UX friction points (navigation, consistency, empty states, onboarding)
   * Bugs/error patterns (crashes, bad states, misconfig, validation issues)
   * Reliability & performance risks (slow paths, blocking I/O, memory, startup time)
   * Security/privacy risks (secrets, logging, permissions, external calls)
   * Testing gaps and CI gaps
   * Documentation gaps

Output a concise **Current State Summary**.

---

## 2) Roadmap (3–6 Releases)

Propose a roadmap split into **3–6 releases** (e.g., vNext patch, minor, major). For each release include:

* **Theme & objectives**
* **Feature additions** (prioritized)
* **UI/UX improvements**

  * For GUI/web/mobile: layout, IA (information architecture), accessibility, onboarding, copy, responsiveness
  * For CLI: command structure, help text, defaults, error messages, config UX
  * For libraries/services: API ergonomics, backwards compatibility, observability
* **Bug/error fix plan** (triage buckets):

  * Crashers / data loss
  * High-friction UX blockers
  * Medium/low annoyances
* **Engineering tasks** (include likely modules/files when possible)
* **Risks / dependencies / migrations**
* **Acceptance criteria** (testable: “Given/When/Then” or checklist)
* **Docs updates required**

---

## 3) Prioritization Backlog (Table)

Create a prioritized backlog table:

| Item | Type (Feature/UX/Bug/TechDebt/Compliance) | Impact | Effort | Risk | Dependencies | Notes |
| ---- | ----------------------------------------- | -----: | -----: | ---: | ------------ | ----- |

Use a simple scoring scheme (e.g., Impact 1–5, Effort 1–5, Risk 1–5). Explain any assumptions.

---

## 4) Sprint 1 Plan (Top 10 Tasks)

Create the first execution plan:

* Top 10 tasks that are **high value / low risk**
* For each task:

  * Goal
  * Steps
  * Files/modules likely touched (if known)
  * Acceptance criteria
  * Test plan

---

## 5) Quality & Compliance Plan (Practical)

Provide a pragmatic checklist that fits the project:

### Security

* Secrets handling (no secrets in repo; env/secret manager)
* Dependency scanning + update policy
* Input validation + safe defaults
* Logging redaction (tokens/PII)

### Privacy (if applicable)

* Data collection/storage/telemetry
* Consent & retention
* Local vs remote processing

### Accessibility (if UI exists)

* Keyboard navigation, focus states
* Contrast and font scaling
* Screen-reader labels (or semantic HTML)

### Reliability & Observability

* Structured error handling & user-friendly messages
* Crash reporting (optional), metrics/logs/traces (if service)
* Retry/timeouts/circuit breakers (if networked)

### Testing & CI

* Unit/integration/e2e targets
* Smoke tests for packaging/distribution
* Lint/format/type-check gates

---

## 6) Documentation Deliverables (Explicit Files)

Propose (and outline contents for) docs files that keep future work consistent:

* `ROADMAP.md` (release plan + guiding principles)
* `CHANGELOG.md` (format + versioning rules)
* `CONTRIBUTING.md` (dev setup, quality gates, PR checklist)
* `ARCHITECTURE.md` (system overview + decisions)
* Optional:

  * `SECURITY.md` (reporting + hardening guidance)
  * `PRIVACY.md` (data practices)
  * `RUNBOOK.md` (if service)
  * `UX_GUIDE.md` (if UI-heavy)
  * `AGENTS.md` (instructions for any LLM/agent working on the repo)

---

## 7) Output Format (Use These Headings Exactly)

1. Current State Summary
2. Key Problems & Opportunities (UX / Bugs / Tech Debt / Compliance)
3. Roadmap (Release by Release)
4. Prioritized Backlog Table
5. Sprint 1 Plan (Top 10)
6. Quality & Compliance Plan
7. Documentation Plan
8. Open Questions / Assumptions

### TEMPLATE END

---

### Optional add-ons (use if you want)

* **“Keep it lean” mode:** limit to 3 releases + top 20 backlog items.
* **“Aggressive growth” mode:** include bigger redesign ideas + risky bets (clearly labeled).
* **“No-UI project” mode:** replace UI/UX with API/CLI ergonomics + DX (developer experience).

If you want, tell me what kind of project you most often use this for (GUI app, CLI tool, web app, library), and I’ll give you **3 specialized variants** while keeping the same universal structure.
