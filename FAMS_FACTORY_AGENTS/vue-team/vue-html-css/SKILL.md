---
name: factory-vue-html-css
description: >
  Role skill for the FAMS Vue HTML-CSS agent: templates, PrimeVue 4 components, Tailwind 4,
  the FAMS theme (preset, tokens, fonts, light and dark mode) and the Verona layout files in
  FamsVue3_2027. Read after factory-core and factory-vue-shared.
---

# FAMS Vue HTML-CSS

Your lane: what the user sees. No API calls, no session logic (that is JavaScript's lane).

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
- One Tailwind theme file with the `fams-*` tokens from factory-vue-shared §2. Use the
  tokens; never Tailwind default colour classes; never a hex value in a component.
- Fonts: Oswald (headings, KPI numbers, uppercase section labels) and Roboto Condensed
  (body, tables, forms), self-hosted from npm packages (a new dependency: Lead asks).
- Look: flat panels, thin borders (fog in light, steel in dark), small uppercase orange
  section labels, no heavy shadows or gradients. Exceptions first on management screens.

## 3. Rules

- Every status shows label + icon, never colour alone; offline/no data shows the age of
  the last reading.
- Both modes usable: check text contrast on paper/white and on charcoal/graphite.
- Responsive down to a 360 px wide phone; no horizontal page scroll.
- Components ≤ 500 lines; split by section.
- PrimeVue components are auto-imported; don't register them globally.
