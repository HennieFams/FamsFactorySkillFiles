---
name: factory-mission
description: >
  How a FAMS factory mission runs (Blueprint Rev 2 Feature Template and §80–§83), for the
  Product / Coordinator, Research / Architecture, Knowledge / Documentation and the
  Independent Challenger: the 8-role team, how a mission flows from a human request to a merged, recorded result;
  the Feature File; the approval and risk matrix as the humans apply it; the mission record
  and coordinator metrics for the pilot scorecard; and how to escalate to Hennie, Andre or
  Franco. Read after factory-core.
---

# FAMS mission — how the factory runs a mission

Sources: Blueprint Rev 2 (summary in Hennie's project), FAMS 2027 90-day plan, readiness
decisions r1–r3 and D4–D16, Notion (FAMS Workspace Portal → IT Planning).

## 1. The factory team (Blueprint Rev 2 §80, decision D16)

| # | Role | Paperclip agent | Mission 0 (app shell) | Pilot (tank card) |
|---|---|---|---|---|
| 1 | FAMS Product / Coordinator | FAMS Product Leader | yes | yes |
| 2 | Research / Architecture (+ Contract Guardian) | Research / Architecture Agent | yes | yes |
| 3 | SQL Developer (DEV database only) | not created yet | — | yes |
| 4 | ASP.NET Developer (FAMS-API) | not created yet | — | yes |
| 5 | Vue Developer | Vue Developer | yes | yes |
| 6 | Unit Tester (Blueprint "Unity / Tester") | Unit Tester | yes | yes |
| 7 | Knowledge / Documentation | not created yet | yes | yes |
| 8 | Independent Challenger (different model family) | Independent Challenger | yes | yes |

Outside the factory (own skills, not routed through this flow): Database Integrity Agent,
FAMS Support Agent. Never route work to a role whose agent does not exist; tell Hennie.

Pilot order (Blueprint §82): human approval → Paperclip → Coordinator → Architecture →
contract → SQL → ASP.NET → Vue → Unit Tester → Challenger → human review → staging.

## 2. Mission flow

1. **Request.** A human asks through Hermes → fams-ceo-mcp → the standing Paperclip issue, or
   opens a Paperclip issue directly. Product work items also live in Notion: "FAMS Features"
   (enhancements to existing systems) and "FAMS New Development" (new builds), both under
   FAMS Workspace Portal → IT Planning.
2. **Feature File.** The Product Leader writes one for anything bigger than a small fix (§3).
3. **Go-ahead.** Andre (Product owner) approves starting a pilot or feature; Hennie approves
   anything technical on the human-approval list (factory-core §3.4).
4. **Route** to Research / Architecture as one Paperclip issue with the Feature File linked. One agent
   works at a time across the whole factory.
5. **Plan → build → test → challenge**: Architecture splits the work, the developer builds, the Unit Tester tests, the Challenger challenges (developers never approve their
   own work); the Challenger is called when §4 says so.
6. **Human merge.** Hennie completes every pull request; agents never merge.
7. **Staging go-ahead** from Andre; production is always a human decision outside the agents.
8. **Close** with the mission record (§5) and any proposed learning for Knowledge/Docs.

## 3. Feature File (one mission contract)

Fields: Feature ID (`FAMS-2027-0000n`) · title · problem · user · value · target behaviour ·
excluded · affected components · contracts (OpenAPI/DTO, owned by Research / Architecture) ·
impacts (SARS, billing, IoT control, customer data: say "none" explicitly) · acceptance
criteria · test plan · risk tier · Challenger level · rollback · AI budget (runs, retries)
· owner · status. A missing field is written as an open question, never guessed.

Current missions: **FAMS-2027-00000 = Mission 0**, the FamsVue3_2027 app shell, a shakedown of
the factory with the Vue roles (measured, used as the baseline) · **FAMS-2027-00001 = the
pilot**, Tank Communication & Health Card (SQL → API → Vue), the mission the Day-90 gate is
judged on.

## 4. Approval and Challenger matrix

The tiers and the human-approval list come from Rev 2 and factory-core. The Challenger level
per row and who besides Hennie signs (Andre, Franco) are a **proposal until Hennie confirms
it** (plan item c2, copying the matrix into the Product Leader's instructions).

| Change | Risk | Approval | Challenger |
|---|---|---|---|
| Wording, formatting, internal docs, routine tests | LOW | Unit Tester + Challenger C1 | C0–C1 |
| Dashboard component, minor UI, low-risk refactor | LOW | Unit Tester + Challenger | C1 |
| New API endpoint, new report, backward-compatible API change | MEDIUM | Unit Tester + Challenger + Hennie at merge | C1–C2 |
| Schema change, material migration, billing, pricing | HIGH | Hennie (+ Andre for billing/pricing) | C2, different model family |
| Auth/security, SARS logic or outputs, firmware, IoT control | CRITICAL | Hennie; Franco for compliance questions | C3 |
| Release to staging | — | Andre | — |

Mandatory Challenger triggers: SARS, regulatory, billing, pricing, auth/security,
production migrations, customer-data exposure, new architecture, ROI cases, forecasting,
new integrations, IoT control, firmware, customer-facing AI models.

## 5. Mission record and coordinator metrics (pilot scorecard)

Per mission, on the issue and later in Notion: model and version per agent · runs and
retries per sub-issue · loops back to a developer · Challenger calls and findings ·
human minutes (review, rescue, answering questions) · **time waiting for a human, logged
separately** · calendar days from go-ahead to staging.
Coordinator metrics: routing latency (request → assigned), age of blocked issues,
clarification loops (times an agent had to ask), hand-offs that lost context.

## 6. Escalation

- Technical, risk, merge, stop: **Hennie** (Mon–Thu 08:00–16:50, Fri 08:00 to 14:00–16:00 SAST).
- Product scope, priorities, pilot start, staging: **Andre**.
- Operations impact and compliance questions: **Franco**.
Ask on the issue in one message with the decision needed and the options; end the run.
