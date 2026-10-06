---
name: fams-ui-standards
description: >
  FAMS house rules for every Vue 3 UI project built by the FAMS Vue Agents — the
  FAMS colour palette and typography (from the Mining Operational Intelligence /
  VINIS x FAMS x MASANA documents), status colours, the one-API-file rule
  (apiService.js + thin feature services, no API calls from pages), speed and
  reactivity budgets, and the legacy FAMS-UI patterns that must not be copied.
  Read this FIRST for any FAMS Vue work. Where it conflicts with fams-portal-master,
  fams-vue-core, fams-quick-report, fams-dispensing or fams-tanks-business, THIS
  skill wins.
metadata:
  owner: Hennie
  status: VALID
  lastValidated: 2026-10-06
---

# FAMS UI Standards (house rules for the FAMS Vue Agents)

The imported Vue skills (`fams-portal-master`, `fams-vue-core`, `fams-quick-report`,
`fams-dispensing`, `fams-tanks-business`, `fams-atg-communications`) are kept exactly as
delivered. This skill only adds rules and resolves conflicts.

**Precedence:** FAMS Core (approval boundaries, evidence standard) → this skill →
the imported Vue skills → anything else. If two rules still conflict, stop and ask
the Vue Lead; don't pick one silently.

Paths on the Paperclip VM (inside the container):

| What | Path |
|---|---|
| Code pack (scripts, agent instructions, config) | `/paperclip/fams-vue-agents` |
| Copy of all Vue skills incl. `fams-dispensing/reference/` | `/paperclip/fams-vue-agents/skills/` |
| Integration index + archive (START_HERE.txt, FILE_MANIFEST.md, …) | `/paperclip/fams-vue-agents/skills/docs/` |
| Project starter template | `/paperclip/fams-vue-agents/templates/vue3-starter/` |
| Working clones of Azure DevOps repos | `/paperclip/fams-vue-agents/workspace/repos/<repo>` |

`FAMS_API_CORE-v2.md` is referenced by several imported skills but **does not exist**.
Don't look for it. The real API contract is the legacy one in § 3 below.

---

## 1. Colour palette — the only colours allowed

Source: *VINIS × FAMS × MASANA – Mining Intelligence* (NotebookLM prompt, § 2) and the
*Mining Operational Intelligence* deck. These replace every colour in the imported
skills (indigo primary, blue/slate/emerald examples, purple/teal export buttons,
green "Live" pill).

| Token | Hex | Use |
|---|---|---|
| `charcoal` | `#30383D` | Dark-mode background, light-mode text, sidebar |
| `graphite` | `#3C4449` | Dark-mode panels/cards, table headers in dark mode |
| `steel` (mid grey) | `#737B80` | Secondary text, icons, borders in dark mode, "normal" status |
| `fog` (light grey) | `#D9DADB` | Borders/dividers in light mode, disabled, "no data" |
| `paper` (off-white) | `#F3F3F1` | Light-mode page background |
| `white` | `#FFFFFF` | Light-mode cards, text on dark/orange |
| `orange` (FAMS orange) | `#F47A20` | **Primary accent**: primary buttons, active nav/tab, focus ring, links, highlights, live/active indicators, chart series 1 |
| `orange-deep` | `#C95614` | Hover/pressed orange, **critical** status |
| `orange-glow` | `#FF8A2A` | Glow/outline on dark panels, pulsing critical indicator |
| `amber` | `#F2A541` | **Warning / exception** status only (the document names amber without a hex; this value is fixed here — don't vary it) |

Rules:

- Orange is the accent. Everything else is charcoal/greys/off-white. No other hues —
  no red, green, blue, purple, teal, indigo, emerald, slate, etc. Tailwind's default
  colour utilities (`bg-blue-600`, `text-slate-500`, …) are forbidden; use the
  `fams-*` tokens only.
- Colours live in **one place**: the PrimeVue preset + Tailwind theme in the
  starter template (`src/theme/famsPreset.js`, `src/assets/fams-theme.css`). No hex
  values anywhere else in the code. The Reviewer rejects hard-coded colours.
- PrimeVue `primary` scale = orange (500 `#F47A20`, 600 `#C95614`); `surface` scale =
  the greys above. Use PrimeVue severities only as mapped in § 2.

### Light and dark mode (the two visual modes from the documents)

| | Light — "clean technical white" | Dark — "dark industrial" |
|---|---|---|
| Page background | `paper` | `charcoal` |
| Cards / panels | `white`, 1px `fog` border | `graphite`, 1px `steel` border; highlighted panels get a thin `orange-glow` outline |
| Text | `charcoal`; secondary `steel` | `paper`; secondary `fog` |
| Sidebar | `charcoal` with `paper` text, active item orange | same |

Dark mode is toggled with the `.app-dark` class on `<html>` (as in fams-portal-master).
Default is light. Both modes must be usable — the Tester checks both.

### Typography

- Headings, KPI numbers, page titles: **Oswald** (condensed, bold, often uppercase).
- Body, tables, forms: **Roboto Condensed**.
- Self-hosted via `@fontsource/oswald` and `@fontsource/roboto-condensed` (already in
  the starter) — no Google Fonts CDN call at runtime (speed + offline depots).
- No serif, rounded or playful fonts.

### Look and feel

Short, strong, uppercase section labels (`01 / INTRODUCTION` style small orange
eyebrow text above headings); thin orange rules; flat panels, no heavy shadows or
gradients. Management screens lead with **exceptions**, not raw data: "what needs
attention" first, detail below.

---

## 2. Status colours (replaces the red/amber/emerald matrix in the imported skills)

Colour is never the only signal: every status shows **label + icon** too.

| Status | Colour | Treatment | PrimeVue severity |
|---|---|---|---|
| Critical (overfill ≥95 %, run-out ≤5 %, failed, voided-with-error) | `orange-deep` | Solid fill, white text, `pi pi-exclamation-triangle`; may pulse with `orange-glow` | `danger` (mapped to orange-deep in the preset) |
| Warning / exception (85–95 %, 5–15 %, needs investigation) | `amber` | Amber fill or left accent bar, charcoal text, `pi pi-exclamation-circle` | `warn` (mapped to amber) |
| Active / live / selected | `orange` | Orange outline or dot, "LIVE" label | `info` (mapped to orange) |
| Healthy / normal | `steel` | Neutral — grey text or outline, `pi pi-check` | `secondary` / `success` (mapped to steel) |
| Offline / no data / stale | `fog` | Dashed `fog` outline, "NO DATA" or "OFFLINE", **always with the age of the last reading** | `contrast` (mapped to fog/charcoal) |

The thresholds themselves (95/85/15/5 %, 10-minute offline rule) still come from
`fams-tanks-business`; only the colours change. FAMS Tanks / FAMS Vue Core rules still
apply: never show an operational value without its timestamp; "no data" ≠ zero.

---

## 3. API access — one generic file + thin feature services

This is the legacy FAMS-UI rule (`FAMS-UI/src/main.js` `$ajaxGet/$ajaxPost/$ajaxPut/
$ajaxDelete/$ajaxPostAny`), ported to Vue 3. It refines fams-portal-master Part 6.

```
src/service/apiService.js        ← THE ONLY file that imports axios. Base URL, headers,
                                    timeouts, error handling, 401/498 → login.
src/service/<Feature>Service.js  ← thin: one function per endpoint, calls apiService only.
src/views/fams/<feature>/use*.js ← composables/stores call the Feature services.
src/views/**/*.vue, components/  ← NEVER call the API, never import axios/fetch/apiService.
```

Rules:

1. Only `src/service/apiService.js` may import `axios` (or use `fetch`/`XMLHttpRequest`).
   ESLint enforces it (`no-restricted-imports` + `no-restricted-globals` in the
   starter). A lint error is a failed build.
2. `.vue` files must not import `apiService` or any `*Service.js` directly — data comes
   in through a composable (`use<Feature>…js`) or a Pinia store. (This deliberately
   tightens fams-portal-master Part 8, whose example page imports `OperatorService`.)
3. Feature services are **thin**: build the URL/params, call `apiService.get/post/put/
   delete`, return `response.data`. No headers, no error toasts, no retries there.
4. **Headers** are set only in `apiService.js`, with the legacy names the FAMS API
   expects (don't invent `X-…` headers):

   | Header | Value (legacy source) |
   |---|---|
   | `Authorization` | `Bearer <accessToken>` (`sessionStorage.accessToken`) |
   | `userId` | `JSON.parse(sessionStorage.roles).id` |
   | `accountId` | `localStorage.userAccountId` |
   | `accountKey` | `localStorage.userAccountKey` |
   | `userKey` | `localStorage.userKey` |

   In the Vue 3 apps these values live in the `authStore` (Pinia, persisted the same
   way); `apiService` reads them from there. Never put `clientKey`/`accountKey` in the
   query string (fams-quick-report § 4).
5. **Base URL** from `import.meta.env.VITE_ROOT_API` (legacy `VUE_APP_ROOT_API`):
   production `https://API24.fams.co.za/api/`, development
   `https://localhost:44341/api/`. Paths are `Controller/Action`, e.g.
   `QuickViewDispensing/Get_Reportinglogbook`.
6. **Login** is the one unauthenticated call: `POST FAMSlegacy/Authenticate`
   `{ Username, Password }` → `response.data.value[0].token` (legacy `$signIn`, uses
   `$ajaxPostAny`). Then `Role/GetPermissions`.
7. **Error handling** (legacy behaviour, keep it):

   | Status | Action | Toast severity |
   |---|---|---|
   | 401 | clear session, go to login | warn |
   | 498 (token expired) | clear session, go to login | warn |
   | 402, 403, 404, 405 | show `response.data.title` / `.message` | warn |
   | 429 | show message ("too many requests") | error |
   | no response (network/timeout) | show `error.message` | error |

   Toasts are raised through `src/service/notify.js` (an app-level toast bus), not by
   calling `useToast()` inside `apiService` — `useToast()` only works inside a
   component's `setup()`, so the fams-portal-master Part 6.1 example would throw.
8. Never log or display tokens, keys or headers.

---

## 4. Speed and reactivity (speed is a requirement, not polish)

- Every route is lazy-loaded (`component: () => import(...)`). Heavy libraries
  (charts, maps, pivot, Excel export) are imported dynamically inside the feature that
  needs them, never in `main.js`.
- PrimeVue components are auto-imported per use (unplugin-vue-components), not
  registered globally.
- Lists: server-side paging with `DataTable :lazy="true"`; `virtualScrollerOptions`
  for anything that can exceed ~200 rows client-side. Large read-only arrays go in
  `shallowRef`. Never fetch "all rows" to filter in the browser when the API can
  filter.
- Derived values use `computed`; `watch` only for side effects (fams-vue-core § 7
  "watcher abuse"). No deep watchers on large arrays.
- Debounce search inputs (300 ms). Cancel superseded requests (`AbortController`
  through `apiService`).
- Show skeletons, not spinners covering the page; keep previous data visible while
  refreshing.
- Auto-refresh uses one shared `useAutoRefresh` composable that pauses when the tab is
  hidden (fams-quick-report § 3.2).
- **Budgets** (checked by the Tester on `npm run build`):
  - initial JS (entry + vendor chunks loaded on first page) ≤ **250 KB gzip**;
  - any single lazy route chunk ≤ **150 KB gzip**;
  - no route component > 500 lines (fams-vue-core § 2).
  A budget breach fails the test run unless the Lead records an approved exception
  in the PR description.

---

## 5. Legacy FAMS-UI (Vue 2) — study it, don't copy it

Legacy repo: Azure DevOps `TecmoFams / Fams24 / Fams24`, folder `FAMS-UI/` (Vue 2,
Vuexy template, Vuesax + BootstrapVue + Element UI, Vuex, vue-cli 3, **Node 14.21.3**).
It only builds on Node 14 (node-sass 4, vue-cli 3); the agents' container runs Node 24.
**Read its source; never `npm install`, build or run it**, and never copy its
`package.json` versions into new projects. New projects use the starter's toolchain
(Node ≥ 20.19). Use it to learn
**what screens exist, which endpoints they call and with what parameters** — not how
to build them.

Do **not** carry over:

- Direct `axios`/`$http`/`fetch` calls in views (≈20+ files under
  `src/views/ui-elements/FAMSUI/` and dashboards do this) — always go through § 3.
- Multiple UI kits at once (Vuesax, BootstrapVue, Element, Syncfusion, ag-Grid,
  Flexmonster, amCharts, ECharts, Chart.js, ApexCharts). New apps use PrimeVue +
  Tailwind only; one charting library per app, chosen by the Lead.
- Copy-pasted error handling in every request helper (now one place).
- Secrets in source: `main.js` contains a Google Maps API key and a commented-out
  Syncfusion licence key; `.env.*` contains a Flexmonster key. **Never copy any key,
  token or licence into new code, issues, comments or PRs.** Keys come from env vars
  set by humans.
- Options API, mixins, `Vue.prototype.$…` globals, `this.$vs.notify`.

---

## 6. Repository and delivery rules (all five Vue agents)

- Before starting a **new project**, the Vue Lead asks the requester (on the Paperclip
  issue) which Azure DevOps project and repo it goes in, and whether that repo already
  exists. Agents cannot create repos — a human creates them. No code until answered.
- Git only through `/paperclip/fams-vue-agents/scripts/devops.mjs` (clone, branch,
  commit-push, pull request). It only pushes branches named `agents/<issue>-<slug>`,
  never `main`/`master`/`develop`/`release/*`, and never force-pushes.
- Every change reaches `main` through a pull request that a human approves and merges.
  Agents never approve or complete PRs.
- New projects start from `templates/vue3-starter` (already wired for § 1–4: preset,
  fonts, apiService, notify, lint rules, budgets, Vitest).
- Plain JavaScript only (no TypeScript), Vue 3 Composition API with `<script setup>`,
  PrimeVue 4, Tailwind 4, Pinia, Vue Router — as fams-portal-master Part 1.1.
