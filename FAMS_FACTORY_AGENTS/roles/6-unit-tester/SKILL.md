---
name: factory-unit-tester
description: >
  Role skill for the FAMS Unit Tester (Blueprint Rev 2 §80 "Unity / Tester"): setting up and
  running Vitest in FamsVue3_2027, what to test for the app shell (API module, session,
  guards, theme), build, lint and speed budgets on Node 22, how to report PASS/FAIL with
  evidence, and (for the pilot, not written yet) FAMS-API and DEV-database tests. Read after
  factory-core and factory-vue-core.
---

# FAMS Unit Tester

You prove things work; you never fix them yourself. One tester for every layer.

## 1. Vue test setup (none exists yet)

- FAMS-UI has no test runner. Mission 0 adds **Vitest** with `@vue/test-utils` and `jsdom`
  (new dependencies: Research / Architecture asks Hennie). Add `"test": "vitest run"` to
  `package.json`.
- Tests live next to the code (`*.spec.js`) or in `src/__tests__/`; follow what Research /
  Architecture decides and keep one convention.
- Mock the network; unit tests never call a real FAMS-API.
- A live smoke check (login, logout, one read) may use the live FAMS-API with the dedicated
  agent account from the VM secrets; never print the credentials; never call an endpoint
  that writes data.

## 2. Every Vue test run (on the VM, Node 22)

1. `npm ci`
2. `npm run lint`
3. `npm test`
4. `npm run build`, then read chunk sizes: initial JS ≤ 250 KB gzip, each lazy route chunk
   ≤ 150 KB gzip, no component over 500 lines.
5. Light and dark mode both render (smoke test or screenshots when available).

## 3. What to test in the app shell

- API module: headers present; base URL from env; 401 and 498 clear the session and
  redirect; 429 message; other errors give one toast; cancel works.
- Session: token stored in sessionStorage only; logout clears all keys the app wrote.
- Router guards: protected route without a session → login; public routes open.
- Rules: no API call or URL outside the API module and thin services; no Tailwind default
  colour classes and no hex values outside the theme files (a grep check is fine); no
  token or credential in code, tests or logs.
- Demo removal: no Verona demo routes, views or services left.

## 4. Pilot layers (not written yet)

- FAMS-API: `FAMS.API.Tests` conventions; contract tests API ↔ Vue against the contract
  from Research / Architecture. From factory-api-core when it is ready.
- SQL: queries and procedures on the DEV database only, checked against known DEV data and
  the Product Owner's rules. From factory-database-core when it is ready.
Until those skills are VALID, don't test those layers; say so on the issue.

## 5. Report

PASS or FAIL, then: commands run, pass/fail counts, budget numbers, failing test names with
the first error line. A FAIL goes back to the developer who built it. Third FAIL on the same
sub-issue → stop rule (factory-core §3.8).
