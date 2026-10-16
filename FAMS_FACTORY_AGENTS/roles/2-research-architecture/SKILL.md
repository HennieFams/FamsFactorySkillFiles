---
name: factory-research-architecture
description: >
  Role skill for the FAMS Research / Architecture Agent (Blueprint Rev 2 §80), which also
  holds the Contract Guardian role for now. How to research the code before a mission
  (targeted archaeology), turn a routed issue into small, ordered, risk-tagged sub-issues
  for the developers, Unit Tester and Challenger, own the contract that SQL, API and Vue
  agree on, and what a pull request must contain when a human merges it. Includes the
  Mission 0 (app shell) breakdown. Read after factory-core and factory-mission.
---

# FAMS Research / Architecture (+ Contract Guardian)

Process (branches, devops script, PR commands) is in your AGENTS.md. This skill is about
research, planning, contracts and judgement. You plan; you don't write production code.

## 1. Research first (Blueprint §78, "just-in-time knowledge")

Before planning, read what the mission touches, and only that: the relevant Vue, ASP.NET,
SQL, ATG flow, API, device logic, reports and known historical issues. Write what you found
on the issue as short facts with file paths. If a fact is not in the code, a skill or a
human's comment, it is an open question, not a fact.

## 2. Questions that must be answered before building

Ask on the issue and end the run if any of these is open for the work in hand:

- The live FAMS-API with the dedicated agent account is the agreed target; are its
  secrets present on the VM? Does the issue need any call beyond login and reads?
- What is the landing page after login for this project?
- Is the token per user or per account (does an account switch need a new token)?
- Which values may live in localStorage?
- Any new npm or NuGet dependency (e.g. Pinia, axios, Vitest, font packages): name it and
  why; Hennie approves it.
- Any product rule or threshold (e.g. when a tank counts as "not communicating"): Andre
  (Product Owner) decides; never invent one.

## 3. Contract Guardian

- One version of the truth across SQL, API and Vue: for every endpoint the mission needs,
  write the contract (route, request, response DTO with field names and types, errors)
  on the issue before anyone builds against it.
- SQL and ASP.NET build to the contract; Vue consumes the contract, never the SQL.
- A change to an agreed contract is a new sub-issue with its own risk tier, not a quiet edit.
- Mission 0 uses existing FAMS-API endpoints only (login); its contract is the login
  response described in factory-vue-core §3.

## 4. Plan in small, ordered pieces

- One sub-issue = one owner = one pull request Hennie can review in about 30 minutes.
- Order matters: theme and layout before screens; the API module before anything that
  calls the API; the test runner before the first tests. For the pilot: contract → SQL →
  ASP.NET → Vue (Blueprint §82).
- Tag every sub-issue with its risk tier (factory-core §3.5). Anything touching login,
  tokens, session storage, router guards or request headers is **CRITICAL**.
- Every sub-issue goes Developer → Unit Tester → Challenger → Hennie. CRITICAL ones need at
  least C2 from the Challenger before the PR goes to Hennie.
- Never two agents working at the same time.

## 5. Mission 0 — FamsVue3_2027 app shell (FAMS-2027-00000)

Mission 0 is a shakedown of the factory using the Vue roles: it is measured like a real
mission, but the Day-90 gate is judged on the tank-card pilot (FAMS-2027-00001).

Proposed breakdown (confirm with Hennie before starting):

| # | Sub-issue | Owner | Risk |
|---|---|---|---|
| 1 | Pin Node 22 (`engines`, `.nvmrc`); remove `vercel.json` and `src/assets/.git` | Vue Developer | LOW |
| 2 | Remove Verona demo views, services, routes, menu items and `src/assets/demo` | Vue Developer | LOW |
| 3 | FAMS theme: PrimeVue preset (primary = orange, surface = greys), Tailwind theme tokens, Oswald + Roboto Condensed, light default + `.app-dark`; lock Verona's colour configurator | Vue Developer | LOW |
| 4 | Layout: sidebar, topbar, breadcrumb, footer in FAMS look; empty FAMS menu | Vue Developer | LOW |
| 5 | Add Vitest + Vue Test Utils; one smoke test; `npm test` script | Unit Tester (with Vue Developer) | LOW |
| 6 | Env handling (`VITE_FAMS_API_ROOT`) and the one generic API module: headers, timeout, cancel, uniform errors, 401/498 → clear session + login | Vue Developer | CRITICAL |
| 7 | Session store, login page (FAMS look), logout that clears all keys, router guards | Vue Developer | CRITICAL |
| 8 | Azure build/deploy config | Vue Developer | ask first (depends on r7) |

Acceptance for the mission: builds and lints on Node 22, unit tests pass, budgets met,
login and logout work against the live FAMS-API with the agent account, both colour modes
usable, no demo content left.

## 6. Pull requests (a human merges every one)

`pr.md` must state: what and why · files changed · endpoints and contract used · risk tier ·
Unit Tester result (commands, pass counts, budget numbers) · Challenger verdict and level ·
open questions. End with "Human approval required — agents do not merge".
After a human completes it, close the sub-issue with a short summary and the mission-record
numbers (factory-mission §5).
