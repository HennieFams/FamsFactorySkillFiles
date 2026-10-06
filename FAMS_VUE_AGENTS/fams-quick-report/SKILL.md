---
name: fams-quick-report-specialized
description: Use when rebuilding or extending any FAMS Portal "Quick Report" sub-view — filter-panel-driven reports, KPI stat card rows, data grids with export, pivot tables, live ATG monitoring grids, calendar heatmaps, chart views, or map views. Also use when integrating with the legacy api24.fams.co.za backend or migrating clientKey/accountkey query-string auth to headers. Reverse-engineered from the legacy cloud.fams.co.za Quick Report menu — a reference for the rebuild, not a literal 1:1 spec. ⚠️ Do not confuse "QuickDisp/QuickDispenseNew" (a reporting view here) with the fams-dispensing skill's Quick Dispensing feature (a transactional write action) — they are different features that share a name.
---

# FAMS Quick Report — Specialized Skill

## 📋 Metadata
| Field | Value |
|-------|-------|
| **VERSION** | 1.0.0 (reverse-engineered from legacy cloud.fams.co.za) |
| **STATUS** | 🔵 Reference spec — describes the legacy system to be rebuilt, not existing Vue 3 code |
| **SOURCE** | Exploratory review of legacy FAMS Portal "Quick Report" menu |
| **DEPENDENCIES** | fams-portal-master (directory conventions, service layer), fams-vue-core (PrimeVue components, styling), fams-tanks-business (ATG/tank data feeding Quick ATG) |
| **NEXT REVIEW** | 2026-11-01 |

---

## ⚠️ Naming Collision — Read This First

The legacy menu has sub-views literally called **"QuickDisp (Legacy)"** (`/QuickDispense`) and **"QuickDisp (New)"** (`/QuickDispenseNew`). These are **reporting/analytics views** over historical dispensing transactions — filter panel or KPI cards + data grid, read-only.

This is **not** the same feature as the `fams-dispensing` skill, which covers the transactional **Quick Dispensing dialog** (`Dispensing.vue` / `DispensingDialog.vue`) — a write action that logs a new fuel transaction and mutates tank/equipment balances.

**Naming recommendation for the rebuild:** keep the transactional feature named `dispensing` (already built) and name this reporting feature something disambiguated, e.g. `dispensing-report` or `dispensing-analytics` — do not reuse "Dispensing" for both a route and a report view. They likely read from the same underlying transaction data eventually, which is a legitimate integration point, but the UI, composables, and route names must stay distinct.

---

## Quick Reference

**When to Use This Skill:**
- Rebuilding any of the 10 Quick Report sub-views listed in §2
- Building one of the 8 reusable report patterns in §3 (Filter Panel, KPI Row, Data Grid, Pivot Table, Live Monitor Grid, Calendar Heatmap, Chart View, Map View)
- Wiring a report view to the legacy `api24.fams.co.za` backend
- Deciding where report auth (`clientKey`/`accountkey`) should live in the new app

**Don't Use This For:**
- The transactional Quick Dispensing write-action feature — see `fams-dispensing`
- Tank volume math itself — see `fams-tanks-business` (Quick ATG only *displays* what that skill calculates)
- Generic PrimeVue/Tailwind reference — see `fams-vue-core`

---

## 1. Application Shell (Legacy Reference)

- Dark-themed collapsible left sidebar with top-level groups: Dashboard, Quick Report, FAMS Reports, FAMS IOT, FAMS Manager, FAMS Allocation, FAMS Filtering, FAMS Integrity, FAMS Setup.
- Quick Report is one expandable group containing the 10 sub-views below.
- Top bar: site/account selector, Dashboard link, Tools/Profile/Support menus, notification bell.
- Opened sub-views render as browser-tab-style strips (multiple reports can stay open as tabs simultaneously) — in the Vue 3 rebuild this maps naturally to a tabbed-view / keep-alive router pattern rather than one-page-at-a-time navigation. Confirm with the team whether multi-tab-open is a requirement to preserve or legacy incidental behavior before building it.

---

## 2. Sub-view Inventory & Target Route Names

| Legacy Label | Legacy Route | Core Pattern (§3) | Suggested New Route |
|---|---|---|---|
| QuickDisp (Legacy) | `/QuickDispense` | Filter Panel + Data Grid | `/main/reports/dispensing-legacy` |
| QuickDisp (New) | `/QuickDispenseNew` | KPI Row + Rich Filter Panel + Modern Grid | `/main/reports/dispensing` *(see naming collision warning above)* |
| Quick Pivot | `/QuickPivot` | Pivot Table Builder | `/main/reports/pivot` |
| Quick Balancing | `/QuickBalancing` | Filter Panel + Data Grid | `/main/reports/balancing` |
| Quick ATG | `/TankLevels` | Live Monitoring Grid | `/main/reports/tank-levels` |
| Quick Analytics | `/PBAnalytics` | Simple Grid | `/main/reports/analytics` |
| Quick Calendar View | `/QuickCalendarView` | Calendar Heatmap | `/main/reports/calendar` |
| Quick Chart View | `/QuickChartView` | Chart View | `/main/reports/charts` |
| Quick Map view | `/StoreLocator` | Map View | `/main/reports/map` |
| Quick GPS Info view | `/QuickViewGPSInformation` | Filter Panel + Data Grid | `/main/reports/gps` |

All routes nest under `/main` per the Master Skill's routing convention (Part 5) so they inherit the app shell/auth guard.

---

## 3. Reusable Pattern Library

### 3.1 Filter Panel
**Used by:** QuickDisp (Legacy), Quick Balancing, Quick GPS Info, Quick Pivot (simplified)
- From/To date pickers, defaulting to first/last day of current month
- Optional report-type combobox (long list of named report variants — e.g. General view, Usage per Product, Usage per Store, SARS/Logbook, Stock Received, etc.)
- Prominent primary-color Submit CTA, disables/lightens while loading
- Optional Default/Custom sub-tabs (Custom = saved/user-defined filter variant)

**Vue 3 component:** `components/report/FilterPanel.vue`, driven by a shared `useReportFilters.js` composable holding `{ fromDate, toDate, reportType }` state — reusable across every sub-view that needs it rather than reimplemented per view.

### 3.2 KPI / Stat Card Row
**Used by:** QuickDisp (New)
- Compact stat cards (Total Transactions, Total Volume, Total Cost, Equipment Count, Products, Avg Transaction) with a "Hide Statistics" toggle
- Sits above a richer filter panel with collapsible Hide/Reset actions and multi-select fields (Product, Store, Equipment, Master Equipment, Allocation 1, Cost Centre, Visible Columns), each with a "(n/total)" selection-count badge
- Live-status pill + Auto Refresh checkbox + manual Refresh button in the header

**Vue 3 component:** `components/report/KpiStatCardRow.vue`. The "Live"/Auto Refresh behavior should use a shared `useAutoRefresh.js` composable (polling interval + pause-on-hidden-tab), not a one-off `setInterval` per view.

### 3.3 Data Grid
**Used by:** QuickDisp (Legacy & New), Quick Balancing, Quick GPS Info, Quick Analytics
- Column headers matching selected report type
- Per-column or global search box
- Page-size selector, pagination controls
- Export: Excel, CSV, Print (legacy) / Export, Pop Out, Refresh (new)
- Footer totals row on aggregate-capable reports
- New-style grid adds colored pill badges for categorical values, relative timestamps, colored left-accent status bars
- Empty state: centered "No data Available" message

**Vue 3 component:** `components/report/DataGrid.vue` wrapping PrimeVue `DataTable` per `fams-vue-core`'s component reference — don't hand-roll pagination/sorting; use `:lazy`. Export logic belongs in a shared `useDataExport.js` composable (CSV/Excel builders), not duplicated per grid.

### 3.4 Pivot Table
**Used by:** Quick Pivot
- Draggable dimension/measure "chip" palette (Allocation×4, Authorization, Consumption, CostCentre, Date variants, Driver, EqpTag, FuelAttendant, FuelPrice, Hour, JobNumber, KM, MasterEquipment, Measurement, Product, Rebate, Registration, Time, Volume)
- Aggregator selector (default: Sum of Volume)
- Row shelf / Column shelf drop zones (Column shelf pre-populated with Year, Month, Day)
- Resulting cross-tab grid with computed aggregates and totals
- Export CSV / Excel / Reset actions

**Vue 3 component:** `components/report/PivotBuilder.vue`. This is the most complex pattern in the set — evaluate whether a drag-drop pivot library (rather than hand-built drag/drop) is warranted before committing engineering time; note this as an open architecture decision, not a solved pattern.

### 3.5 Live Monitoring Grid
**Used by:** Quick ATG (Tank Levels)
- Toggles: Show All Tanks, Show Only Active Tanks, Auto Refresh; manual Reload button
- Columns: Tank Name, Date of Reading, Tank Capacity, Dip (mm), Current Level (L), Water Level (mm), Temp (°C), Ullage (L), "View Historical" link
- Tabs: ATG Grid / ATG Chart (same underlying tank data, two views)

**Vue 3 component:** `components/report/LiveMonitorGrid.vue`. **This is where `fams-tanks-business` plugs in** — the Current Level / capacity / status values displayed here should come from that skill's volume-calculation and threshold logic, not be recomputed independently in the report layer.

### 3.6 Calendar Heatmap
**Used by:** Quick Calendar View
- Month-grid calendar with pill badges on active days showing a summary value (e.g. volume)
- Prev/Next month navigation
- Multiple related report tabs alongside the calendar (Expired EQP License, Service Dates, Expired Employee/PDP License, ATG vs Consumption, ATG Stock Reconciliation)

**Vue 3 component:** `components/report/CalendarHeatmap.vue`

### 3.7 Chart View
**Used by:** Quick Chart View
- Tabs: Usage Per Month / Per Equipment / Per Driver / Per Fuel Attendant
- Month-picker filter + Submit driving the rendered chart

**Vue 3 component:** `components/report/ChartView.vue`

### 3.8 Map View
**Used by:** Quick Map view (StoreLocator)
- Leaflet/OSM-style interactive map
- Tabs: ATG / Fuel Movement to switch the plotted data layer

**Vue 3 component:** `components/report/MapView.vue`

---

## 4. Backend & Auth Conventions — ⚠️ Security Note

- Legacy backend base: `https://api24.fams.co.za/api/{Controller}/{Action}`
- Example: `GET /api/QuickViewDispensing/Get_Reportinglogbook?&clientKey=...&accountkey=...&fromdate=YYYY-MM-DD&todate=YYYY-MM-DD`
- Date filters use `fromdate`/`todate` in `YYYY-MM-DD`, defaulting to first/last day of current month

**⚠️ `clientKey` and `accountkey` are currently passed as query-string parameters.** This leaks credentials into server logs, browser history, and proxy/CDN logs. **For the Vue 3 rebuild:** move these into request headers (an `Authorization: Bearer <token>` scheme, or a custom `X-Client-Key`/`X-Account-Key` header pair at minimum) via the centralized `apiService.js` interceptor described in the Master Skill's Part 6 — do this once, centrally, rather than per-report-service. Do not carry the query-string pattern forward into any new service class.

---

## 5. Directory Placement — Reconciled with Master Skill Conventions

The source document's suggested layout used a standalone `views/quick-report/` tree. That doesn't match the Master Skill's `src/views/fams/<feature>/` convention (Part 1.2) or its feature-module split principle (Page + Sidebar/Dialog + composables). Reconciled placement:

```
src/
├── components/
│   └── report/                        # Shared across ALL Quick Report sub-views
│       ├── FilterPanel.vue
│       ├── KpiStatCardRow.vue
│       ├── DataGrid.vue
│       ├── PivotBuilder.vue
│       ├── LiveMonitorGrid.vue
│       ├── CalendarHeatmap.vue
│       ├── ChartView.vue
│       └── MapView.vue
├── composables/
│   └── report/                        # Cross-cutting, shared by multiple sub-views
│       ├── useReportFilters.js        # date range + report-type state
│       ├── useDataExport.js           # CSV/Excel export helpers
│       └── useAutoRefresh.js          # polling/live-refresh logic
├── service/
│   └── ReportService.js               # centralized api24.fams.co.za client (see §4)
└── views/
    └── fams/
        └── quick-report/               # One folder per sub-view, each a thin page
            ├── DispensingReportLegacy.vue
            ├── DispensingReport.vue    # ⚠️ renamed from "QuickDispenseNew" — see collision warning
            ├── QuickPivot.vue
            ├── QuickBalancing.vue
            ├── TankLevels.vue
            ├── QuickAnalytics.vue
            ├── QuickCalendarView.vue
            ├── QuickChartView.vue
            ├── QuickMapView.vue
            └── QuickGpsInfoView.vue
```

Each `views/fams/quick-report/*.vue` page should stay thin: compose the shared `components/report/*` pieces + the `composables/report/*` state, per-view. Don't let report-specific logic leak back out of these thin pages into the shared components — that's how the shared components become un-reusable again.

---

## 6. Visual Conventions (cross-reference `fams-vue-core`)

- Primary accent: **orange** — active nav items, primary CTAs, active tab underlines, highlight badges
- Distinct export-action colors: **purple** (CSV), **teal** (Excel) — keep these consistent across every Data Grid instance rather than per-view color choices
- Dark sidebar / light content area contrast
- Green "Live" pill for live-status indicators
- Consistent iconography: circular arrow (reload/refresh), magnifying glass (search), chevrons (pagination/month nav)

When implementing in PrimeVue 4 + Tailwind (per `fams-vue-core`), express these as design tokens/Tailwind theme extensions rather than hardcoded hex values scattered across each report component, so the accent scheme stays a single source of truth.

---

## Summary

**This skill covers:**
- ✅ Full sub-view inventory for the Quick Report menu (10 views) with suggested new route names
- ✅ 8 reusable report UI patterns, each mapped to a shared Vue 3 component
- ✅ Real legacy backend contract + a concrete auth-hardening recommendation
- ✅ Directory placement reconciled with the Master Skill's existing conventions
- ⚠️ An explicit naming-collision warning against the `fams-dispensing` skill

**Reference with:**
- `fams-portal-master` Part 5/6 (routing, service layer) for wiring these views in
- `fams-vue-core` for PrimeVue DataTable/component choices and styling tokens
- `fams-tanks-business` for the actual tank math feeding the Live Monitoring Grid
- `fams-dispensing` — read the naming collision warning before touching anything "dispensing"-named

**Next Review:** 2026-11-01
