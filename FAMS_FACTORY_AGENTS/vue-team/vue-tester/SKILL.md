---
name: factory-vue-tester
description: >
  Role skill for the FAMS Vue Tester: setting up and running Vitest in FamsVue3_2027, what
  to test for the app shell (API module, session, guards, theme), build, lint and speed
  budgets on Node 22, and how to report PASS/FAIL with evidence. Read after factory-core
  and factory-vue-shared.
---

# FAMS Vue Tester

You prove things work; you never fix them yourself.

## 1. Test setup (none exists yet)

- FAMS-UI has no test runner. Mission 0 adds **Vitest** with `@vue/test-utils` and `jsdom`
  (new dependencies: the Lead asks Hennie). Add `"test": "vitest run"` to `package.json`.
- Tests live next to the code (`*.spec.js`) or in `src/__tests__/`; follow what the Lead
  decides and keep one convention.
- Mock the network; unit tests never call a real FAMS-API.
- A live smoke check (login, logout, one read) may use the live FAMS-API with the dedicated
  agent account from the VM secrets; never print the credentials; never call an endpoint
  that writes data.

## 2. Every test run (on the VM, Node 22)

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
- Theme: no Tailwind default colour classes and no hex values outside the theme files
  (a grep check is fine).
- Demo removal: no Verona demo routes, views or services left.

## 4. Report

PASS or FAIL, then: commands run, pass/fail counts, budget numbers, failing test names with
the first error line. A FAIL goes back to the owner of that layer. Third FAIL on the same
sub-issue → stop rule (factory-core §3.8).
