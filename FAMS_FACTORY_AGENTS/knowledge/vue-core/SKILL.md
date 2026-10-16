---
name: factory-vue-core
description: >
  FAMS_VUE_CORE (Blueprint Rev 2 §79): Vue knowledge for every role that works on
  FAMS-UI (Vue Developer; Research / Architecture, Unit Tester and Challenger when they
  plan, test or challenge Vue work) in the FamsVue3_2027 portal: the starting template and stack, the FAMS
  palette, fonts and status colours, the one-API-file rule, how login and the session work
  against FAMS-API, speed budgets, and what not to copy from the legacy Vue 2 FAMS-UI. Read
  after factory-core; your role skill builds on this one.
---

# FAMS Vue core (FAMS_VUE_CORE)

Sources (checked 13 Oct 2026): FamsVue3_2027 `development-agent` (FAMS-UI/), FAMS-API in
FamsVue3_2027 and Fams24 (`TokenController`, `FAMSlegacyController`, `Program.cs`), legacy
Fams24 FAMS-UI (`src/main.js`, `src/store/auth/moduleAuthActions.js`), Hennie's decisions of
6 and 12 Oct 2026.

## 1. The app and its starting point

- Repo **FamsVue3_2027**, folder **`FAMS-UI/`**, base branch **`development-agent`**.
  It is a new portal with a modern look; most of it will replace the legacy portal.
  Deployment target: **Azure** (not Vercel).
- `development-agent` holds the **bare Verona template** (PrimeVue) — this is the agreed
  starting point. Hennie's own branches (`hennie-feature/*`, `feature/Login*`,
  `development`) are not yours: don't branch from them, diff against them or copy from them.
- Stack as it stands: Vue 3.4, vue-router 4 (`createWebHistory`), PrimeVue 4.5 with the
  Aura preset and `darkModeSelector: '.app-dark'`, Tailwind 4 + `tailwindcss-primeui`,
  Vite 5, `@` → `src/`. PrimeVue components are auto-imported per use
  (`unplugin-vue-components` + `PrimeVueResolver`); `ToastService` and
  `ConfirmationService` are installed. Plain JavaScript (no TypeScript).
- **Not there yet** (each is a work item, not an assumption): no Pinia, no axios, no test
  runner, no Node pin, no FAMS theme files, no fonts, no `.env` handling. Adding a
  dependency is a decision: name it and why in the plan; Hennie approves it in the PR.
- Node **22 LTS**. Build: `npm ci` then `npm run build` (clean build on Node 22.23 passes
  and lint passes on the bare template, 12 Oct). The Windows `node_modules` on a
  developer laptop does not work on Linux; always `npm ci` on the VM.
- Demo content to remove: `src/views/{apps,dashboards,e-commerce,uikit,user-management,utilities}`,
  demo `src/service/*Service.js`, `src/assets/demo`, demo routes and menu items, and
  `vercel.json`. `src/assets/.git` is a stray nested git folder: remove it.

## 2. Look: palette, fonts, status (Hennie's decisions)

Only these colours, defined in **one place** (a PrimeVue preset file plus one Tailwind
theme file); no hex value anywhere else in the code, no Tailwind default colour classes.

| Token | Hex | Use |
|---|---|---|
| charcoal | `#30383D` | dark background, light-mode text, sidebar |
| graphite | `#3C4449` | dark-mode panels and cards |
| steel | `#737B80` | secondary text, icons, dark-mode borders, "normal" status |
| fog | `#D9DADB` | light-mode borders, disabled, "no data" |
| paper | `#F3F3F1` | light-mode page background |
| white | `#FFFFFF` | light-mode cards, text on dark/orange |
| orange | `#F47A20` | the accent: primary buttons, active nav, focus, links, live |
| orange-deep | `#C95614` | hover/pressed, **critical** status |
| orange-glow | `#FF8A2A` | outline on dark panels, pulsing critical |
| amber | `#F2A541` | **warning / exception** only |

- PrimeVue `primary` = orange scale; `surface` = the greys. Light mode is the default;
  dark mode = `.app-dark` on `<html>`. Both must work.
- Fonts: **Oswald** for headings, page titles and KPI numbers; **Roboto Condensed** for
  body, tables and forms; self-hosted (npm font packages), never a CDN call.
- Status colours (colour is never the only signal: always label + icon):
  critical = orange-deep · warning = amber · active/live = orange · normal = steel ·
  offline/no data = fog, dashed, **with the age of the last reading**.
  The thresholds behind a status are Product Owner decisions; never hard-code one that
  is not in an issue or a decision.
- Never show an operational value without its timestamp. "No data" is not zero.

## 3. API access — one generic file, thin services

- **One** generic API module (e.g. `src/service/apiService.js`) owns the base URL, all
  headers, timeouts, cancellation (`AbortController`) and error handling.
- Each feature may have one **thin service file** that calls the generic module.
- **Pages and components never call the API or build URLs.** The Unit Tester and the Challenger reject it.
- Base URL comes from a Vite env variable (proposal: `VITE_FAMS_API_ROOT`); never
  hard-code a URL.

### Which API and which login (Hennie, 15 Oct)

- Vue work runs against the **live FAMS-API** using **one dedicated agent account**.
  Never use a personal, colleague or client login.
- The account's username and password are **secrets on the VM** (environment / Paperclip
  secrets), never in the repo, an `.env` file that is committed, a test, a comment or a log.
  If they are missing, stop and ask.
- With that account, make only the calls the issue needs: login, and reading data to show.
  **Never call an endpoint that creates, updates or deletes FAMS data**, even if the UI has
  a button for it; build such screens against mocks until Hennie approves a live test.
- Unit tests always mock the network. Live calls are for a short, named smoke check
  (e.g. "login and logout work") recorded on the issue.
- FAMS-API code belongs to the ASP.NET Developer; Vue work never changes it.

### FAMS-API facts (read from the code, 13 Oct)

- 126 of the 127 controllers answer on `api/<Controller>`; 32 of them (incl. `FAMSlegacy`) also
  answer on `<Controller>` without `api/`, which is how the legacy UI calls them. CORS
  allows any origin. Auth is JWT Bearer. A rate limiter is on, so **429** can happen.
- **Login used by the legacy UI:** `POST {root}FAMSlegacy/Authenticate` with body
  `{ "Username": <email>, "Password": <password> }` (anonymous). The legacy UI reads
  `response.data.value[0].token`, `.userRoles` (with `.id`, `.username`, `.userRoles[].code`)
  and `.userKey`. Other login routes exist (`FAMSlegacy/Login`, `api/Token`, `api/skaap`);
  don't use them unless Hennie says so.
- **Headers on every call** in the legacy UI: `Authorization: Bearer <token>`, `userId`,
  `accountId`, `accountKey`, `userKey`. Keep the same header names: FAMS-API expects them.
- The API does not send 498 itself today, but the legacy UI treats 498 as "token expired";
  handle it the same as 401.

### Session rules (decided 6 Oct)

- The token lives in **sessionStorage only**, never localStorage.
- **401 and 498:** clear the session and go to the login page. Every other error code is
  handled the same way everywhere (one toast style, one place in the API module).
- **Logout clears every session and local storage key** the app wrote.
- The landing page after login is decided per project; ask.
- Open question (don't guess): is the token per user or per account? The legacy
  `selectaccount` screen may not refresh it after an account switch.
- Not decided yet: which non-auth values may live in localStorage. Propose in the plan
  (e.g. theme only) and let Hennie decide.
- Auth and session code is **CRITICAL** risk: it needs Hennie's approval and a Challenger
  review; it is never merged on an agent's say-so (nothing is).

## 4. Speed (a requirement, not polish)

- Every route lazy-loaded; heavy libraries imported inside the feature that needs them.
- Server-side paging for long lists; `shallowRef` for large read-only arrays; `computed`
  for derived values, `watch` only for side effects; debounce search (300 ms); cancel
  superseded requests through the API module; skeletons instead of full-page spinners.
- Budgets checked on `npm run build`: initial JS ≤ **250 KB gzip**; any lazy route chunk ≤
  **150 KB gzip**; no component over 500 lines. The bare template's entry chunk is about
  152 KB gzip (703 KB raw) — the demo removal should bring it down.

## 5. Legacy FAMS-UI (Fams24, Vue 2) — study, don't copy

Use it to learn which endpoints, headers and screens exist. Don't copy its patterns:
API calls defined on `Vue.prototype` and repeated per HTTP verb, the same error block
copied five times, tokens and user data spread over `localStorage` and `sessionStorage`,
firebase keys cleared by name search, a 2,761-line router file, Vuesax 3 components.
