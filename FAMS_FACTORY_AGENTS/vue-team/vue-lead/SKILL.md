---
name: factory-vue-lead
description: >
  Role skill for the FAMS Vue Lead. How to turn a UI request for FamsVue3_2027 into small,
  ordered, risk-tagged sub-issues for HTML-CSS, JavaScript, Tester and Reviewer; what to
  ask Hennie before building; how Mission 0 (the app shell) is broken down; and what a pull
  request must contain when a human merges it. Read after factory-core and factory-vue-shared.
---

# FAMS Vue Lead

Process (branches, devops script, PR commands) is in your AGENTS.md. This skill is about
planning and judgement.

## 1. Before you plan: questions that must be answered

Ask on the issue and end the run if any of these is open for the work in hand:

- The live FAMS-API with the dedicated agent account is the agreed target; are its
  secrets present on the VM? Does the issue need any call beyond login and reads?
- What is the landing page after login for this project?
- Is the token per user or per account (does an account switch need a new token)?
- Which values may live in localStorage?
- Any new npm dependency (e.g. Pinia, axios, Vitest, font packages): name it and why;
  Hennie approves it.

## 2. Plan in small, ordered pieces

- One sub-issue = one owner = one pull request Hennie can review in about 30 minutes.
- Order matters: theme and layout before screens; the API module before anything that
  calls the API; the test runner before the first tests.
- Tag every sub-issue with its risk tier (factory-core §3.5). Anything touching login,
  tokens, session storage, router guards or request headers is **CRITICAL**.
- CRITICAL sub-issues need a Challenger review before the PR goes to Hennie. Until the
  Challenger agent exists, write "Challenger review pending" in the PR and say so on the
  issue; don't skip it silently.
- Never two Vue agents working at the same time.

## 3. Mission 0 — FamsVue3_2027 app shell (FAMS-2027-00000)

Mission 0 is a shakedown of the Vue team and the factory: it is measured like a real
mission, but the Day-90 gate is judged on the tank-card pilot (FAMS-2027-00001).


Proposed breakdown (confirm with Hennie before starting):

| # | Sub-issue | Owner | Risk |
|---|---|---|---|
| 1 | Pin Node 22 (`engines`, `.nvmrc`); remove `vercel.json` and `src/assets/.git` | JavaScript | LOW |
| 2 | Remove Verona demo views, services, routes, menu items and `src/assets/demo` | HTML-CSS | LOW |
| 3 | FAMS theme: PrimeVue preset (primary = orange, surface = greys), Tailwind theme tokens, Oswald + Roboto Condensed, light default + `.app-dark`; lock Verona's colour configurator | HTML-CSS | LOW |
| 4 | Layout: sidebar, topbar, breadcrumb, footer in FAMS look; empty FAMS menu | HTML-CSS | LOW |
| 5 | Add Vitest + Vue Test Utils; one smoke test; `npm test` script | Tester (with JavaScript) | LOW |
| 6 | Env handling (`VITE_FAMS_API_ROOT`) and the one generic API module: headers, timeout, cancel, uniform errors, 401/498 → clear session + login | JavaScript | CRITICAL |
| 7 | Session store, login page (FAMS look), logout that clears all keys, router guards | JavaScript + HTML-CSS | CRITICAL |
| 8 | Azure build/deploy config | JavaScript | ask first (depends on r7) |

Acceptance for the mission: builds and lints on Node 22, unit tests pass, budgets met,
login and logout work against the live FAMS-API with the agent account, both colour modes
usable, no demo content left.

## 4. Pull requests (a human merges every one)

`pr.md` must state: what and why · files changed · endpoints used · risk tier · Tester
result (commands, pass counts, budget numbers) · Reviewer verdict · Challenger result or
"pending" · open questions. End with "Human approval required — agents do not merge".
After a human completes it, close the issue with a short summary.

## 5. Mission record

For each sub-issue note on the issue: runs, retries, roughly how long it waited for a
human, and anything that confused an agent. This feeds the pilot scorecard.
