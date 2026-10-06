# FAMS Vue 3 starter

Starting point for every new FAMS Vue project built by the FAMS Vue Agents. Already wired
for `fams-ui-standards`:

| Rule | Where |
|---|---|
| FAMS palette, light/dark mode, status colours | `src/theme/palette.js`, `src/theme/famsPreset.js`, `src/assets/fams-theme.css`, `src/components/shared/StatusTag.vue` |
| Oswald + Roboto Condensed (self-hosted) | `src/main.js` |
| One API file (legacy headers + error handling) | `src/service/apiService.js`, `src/service/notify.js`, `src/stores/authStore.js` |
| Thin feature services | `src/service/AuthService.js`, `src/service/DispensingReportService.js` (example) |
| Data via composables, never from pages | `src/views/fams/dashboard/useDashboardData.js` |
| Lazy routes, auth guard | `src/router/index.js` |
| Lint rules (no API calls in pages, no axios/fetch outside apiService, no default Tailwind colours, no hex) | `eslint.config.js` |
| Speed budgets | `scripts/check-budget.mjs` |

```bash
npm install
npm run dev        # http://localhost:5173
npm run check      # lint + unit tests + build + budget  (what the Vue Tester runs)
```

Copy the folder into the new repo, set `"name"` in `package.json`, delete the example
`DispensingReportService.js`/dashboard content once real features exist, and commit
`package-lock.json`.
