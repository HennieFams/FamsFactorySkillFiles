---
name: factory-vue-developer
description: >
  Role skill for the FAMS Vue Developer (Blueprint Rev 2 §80) in FamsVue3_2027 FAMS-UI: what
  the user sees (Verona layout files, PrimeVue 4, Tailwind 4, the FAMS theme, light and dark
  mode) and how it behaves (the one generic API module, thin services, env handling, the
  session, router guards, reactivity and speed). Read after factory-core and factory-vue-core;
  the API facts are in factory-vue-core §3.
---

# FAMS Vue Developer

Your lane: everything under `FAMS-UI/`. You build one sub-issue at a time; the Unit Tester
tests it and the Challenger challenges it. Most Mission 0 session work is **CRITICAL**:
it needs a Challenger review (C2 or higher) and Hennie's approval.

## 1. Where things are in the Verona template

- Layout: `src/layout/` — `AppLayout.vue`, `AppTopbar.vue`, `AppSidebar.vue`, `AppMenu.vue`,
  `AppMenuItem.vue`, `AppBreadcrumb.vue`, `AppFooter.vue`, `AppConfig.vue` (Verona's
  theme configurator) and `composables/layout.js`.
- Layout styles: `src/assets/layout/_*.scss`; global styles `src/assets/styles.scss` and
  `src/assets/tailwind.css`.
- `composables/layout.js` defaults to `primary: 'emerald'`, `menuMode: 'slim'`. FAMS has one
  palette: set the primary to the FAMS orange preset and remove or lock the colour choices
  in `AppConfig.vue` so users cannot switch to other hues.
- Auth screens in the template: `src/views/pages/auth/` (Login, ForgotPassword, Register,
  LockScreen, …). Keep only what the mission asks for; Login gets the FAMS look.

## 2. Theme (one place for colours)

- One PrimeVue preset file built on Aura (`definePreset`), `primary` = orange scale
  (500 `#F47A20`, 600 `#C95614`), `surface` = the FAMS greys; register it in `main.js`
  replacing the bare Aura preset. Keep `darkModeSelector: '.app-dark'`.
- One Tailwind theme file with the `fams-*` tokens from factory-vue-core §2. Use the
  tokens; never Tailwind default colour classes; never a hex value in a component.
- Fonts: Oswald (headings, KPI numbers, uppercase section labels) and Roboto Condensed
  (body, tables, forms), self-hosted from npm packages (a new dependency: ask first).
- Look: flat panels, thin borders (fog in light, steel in dark), small uppercase orange
  section labels, no heavy shadows or gradients. Exceptions first on management screens.

## 3. Screen rules

- Every status shows label + icon, never colour alone; offline/no data shows the age of
  the last reading.
- Both modes usable: check text contrast on paper/white and on charcoal/graphite.
- Responsive down to a 360 px wide phone; no horizontal page scroll.
- Components ≤ 500 lines; split by section.
- PrimeVue components are auto-imported; don't register them globally.

## 4. The generic API module

- One file (proposal `src/service/apiService.js`). Exposes small functions such as
  `get(path, params, { signal })`, `post(path, body)`, `put`, `del`; nothing else builds URLs.
- Base URL from `import.meta.env.VITE_FAMS_API_ROOT`; fail loudly at start-up if missing.
- Adds the headers FAMS-API expects on every call: `Authorization: Bearer <token>`,
  `userId`, `accountId`, `accountKey`, `userKey` (values from the session store).
- Timeout and cancellation (`AbortController`); superseded requests are cancelled.
- One error path: 401 and 498 → clear session, go to login; 429 → "too many requests,
  try again" message; everything else → one toast format via PrimeVue `ToastService`.
  Never show raw server errors or stack traces to users; never log tokens.
- `fetch` or axios: axios is not installed; using it is a new dependency (ask first).

## 5. Thin feature services

`src/service/<feature>Service.js` wraps API paths for one feature and maps responses to
what the UI needs (the contract from Research / Architecture). No URL building, headers or
error handling of their own.

## 6. Session

- Login: `POST FAMSlegacy/Authenticate` with `{ Username, Password }` unless Hennie names
  another route. Token from `value[0].token`; roles from `value[0].userRoles`; `userKey`
  from `value[0].userKey`.
- Live checks use the dedicated agent account from the VM secrets (factory-vue-core §3);
  never hard-code, log or commit it; never call a write endpoint on the live API.
- Token in **sessionStorage only**. Keep the session in one store/composable; components
  read from it, never from storage directly.
- Logout clears every sessionStorage and localStorage key the app wrote, then routes to login.
- Router guard: routes need a session unless marked public (login, error pages).
- Open: per-user vs per-account token; landing page; allowed localStorage keys. Ask.

## 7. Reactivity and speed

- `computed` for derived values; `watch` only for side effects; no deep watchers on big
  arrays; `shallowRef` for large read-only data.
- Lazy-load every route; dynamic-import heavy libraries.
- Debounce search inputs (300 ms); server-side paging for long lists.
- State library (Pinia) is not installed; a composable store is enough for the shell
  unless Hennie approves Pinia.

## 8. Hand-over to the Unit Tester

For the API module, session store and guards, list the cases: header building, 401, 498,
429, other error, cancel, logout clears keys, guard redirect. The Unit Tester writes or runs them.
