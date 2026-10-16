---
name: factory-vue-javascript
description: >
  Role skill for the FAMS Vue JavaScript agent: the one generic API module, thin feature
  services, env handling, the session (login, token in sessionStorage, logout, 401/498),
  router guards, state and reactivity, and speed in FamsVue3_2027. Read after factory-core
  and factory-vue-shared; the API facts are in factory-vue-shared §3.
---

# FAMS Vue JavaScript

Your lane: behaviour and data. Most of your Mission 0 work is **CRITICAL** risk (auth and
session): it needs a Challenger review and Hennie's approval.

## 1. The generic API module

- One file (proposal `src/service/apiService.js`). Exposes small functions such as
  `get(path, params, { signal })`, `post(path, body)`, `put`, `del`; nothing else builds URLs.
- Base URL from `import.meta.env.VITE_FAMS_API_ROOT`; fail loudly at start-up if missing.
- Adds the headers FAMS-API expects on every call: `Authorization: Bearer <token>`,
  `userId`, `accountId`, `accountKey`, `userKey` (values from the session store).
- Timeout and cancellation (`AbortController`); superseded requests are cancelled.
- One error path: 401 and 498 → clear session, go to login; 429 → "too many requests,
  try again" message; everything else → one toast format via PrimeVue `ToastService`.
  Never show raw server errors or stack traces to users; never log tokens.
- `fetch` or axios: axios is not installed; using it is a new dependency (Lead asks).

## 2. Thin feature services

`src/service/<feature>Service.js` wraps API paths for one feature and maps responses to
what the UI needs. No URL building, headers or error handling of their own.

## 3. Session

- Login: `POST FAMSlegacy/Authenticate` with `{ Username, Password }` unless Hennie names
  another route. Token from `value[0].token`; roles from `value[0].userRoles`; `userKey`
  from `value[0].userKey`.
- Live checks use the dedicated agent account from the VM secrets (factory-vue-shared §3);
  never hard-code, log or commit it; never call a write endpoint on the live API.
- Token in **sessionStorage only**. Keep the session in one store/composable; components
  read from it, never from storage directly.
- Logout clears every sessionStorage and localStorage key the app wrote, then routes to login.
- Router guard: routes need a session unless marked public (login, error pages).
- Open: per-user vs per-account token; landing page; allowed localStorage keys. Ask.

## 4. Reactivity and speed

- `computed` for derived values; `watch` only for side effects; no deep watchers on big
  arrays; `shallowRef` for large read-only data.
- Lazy-load every route; dynamic-import heavy libraries.
- Debounce search inputs (300 ms); server-side paging for long lists.
- State library (Pinia) is not installed; a composable store is enough for the shell
  unless Hennie approves Pinia.

## 5. Tests you hand to the Tester

For the API module, session store and guards, list the cases: header building, 401, 498,
429, other error, cancel, logout clears keys, guard redirect. The Tester writes or runs them.
