# FAMS factory skill registry

Metadata for every skill in `FAMS_FACTORY_AGENTS/` (Blueprint Rev 2 §19). Owner of every
skill: **Hennie (Knowledge Steward)**. Statuses: VALID · REVIEW REQUIRED · UNDER REVIEW ·
DEPRECATED · ARCHIVED; "not started" = placeholder only.
A skill becomes VALID when Hennie has reviewed it against the code/decisions named under
Sources. Only VALID skills are given to agents.

## New skill set

| Skill | Folder | Version | Status | For | Sources | Last validated | Next review |
|---|---|---|---|---|---|---|---|
| factory-core | _core | 1.0.0 | VALID | every agent | Blueprint Rev 2; decisions r1–r3, D4–D11 (phase-1/READINESS.md); branching model | 2026-10-15 | Mission 0 retrospective |
| factory-vue-shared | vue-team/_shared | 1.0.0 | VALID | 5 Vue agents | FamsVue3_2027 development-agent; FAMS-API TokenController, FAMSlegacyController, Program.cs; legacy Fams24 FAMS-UI main.js and moduleAuthActions.js; fams-ui-standards decisions (palette, fonts, speed, 6 Oct auth) | 2026-10-15 | Mission 0 retrospective |
| factory-vue-lead | vue-team/vue-lead | 1.0.0 | VALID | FAMS Vue Lead | as above + Mission 0 plan | 2026-10-15 | Mission 0 retrospective |
| factory-vue-html-css | vue-team/vue-html-css | 1.0.0 | VALID | FAMS Vue HTML-CSS | Verona layout files, layout.js | 2026-10-15 | Mission 0 retrospective |
| factory-vue-javascript | vue-team/vue-javascript | 1.0.0 | VALID | FAMS Vue JavaScript | FAMS-API auth code, legacy main.js | 2026-10-15 | Mission 0 retrospective |
| factory-vue-tester | vue-team/vue-tester | 1.0.0 | VALID | FAMS Vue Tester | package.json (no runner yet), build check 12 Oct | 2026-10-15 | Mission 0 retrospective |
| factory-vue-reviewer | vue-team/vue-reviewer | 1.0.0 | VALID | FAMS Vue Reviewer | factory-core, factory-vue-shared | 2026-10-15 | Mission 0 retrospective |
| factory-command-shared | command/_shared | 0.1.0 | UNDER REVIEW | command group | Blueprint Rev 2 summary; 90-day plan; decisions r1–r3, D4–D14; Notion IT Planning (FAMS Features, FAMS New Development) | — | on Hennie's review |
| factory-product-leader | command/product-leader | 0.1.0 | UNDER REVIEW | CEO agent | as above; Vue/integrity agents' escalation rules; CEO AGENTS.md NOT yet compared (not in the repo) | — | on Hennie's review |
| factory-challenger | command/challenger | 0.1.0 | UNDER REVIEW | Challenger (model c3 open) | Blueprint Rev 2 §41–46 (via summary) | — | on Hennie's review |
| factory-knowledge-docs | command/knowledge-docs | 0.1.0 | UNDER REVIEW | Knowledge/Docs (k12 open) | Blueprint §18–21, §76; notion-mcp STATUS; D10, D12 | — | on Hennie's review |
| factory-api-shared | api-team/_shared | — | not started | API team | — | — | — |
| factory-api-architect | api-team/api-architect | — | not started | API Architect (Contract Guardian) | — | — | — |
| factory-api-developer | api-team/api-developer | — | not started | API Developer | — | — | — |
| factory-api-tester | api-team/api-tester | — | not started | API Tester | — | — | — |
| factory-sql-shared | sql-team/_shared | — | not started | SQL team | — | — | — |
| factory-sql-developer | sql-team/sql-developer | — | not started | SQL Developer | — | — | — |
| factory-sql-tester | sql-team/sql-tester | — | not started | SQL Tester | — | — | — |
| factory-operations-shared | operations/_shared | — | not started | operations group | — | — | — |
| factory-data-integrity | operations/data-integrity | — | not started | Data Integrity Agent | — | — | — |
| factory-support | operations/support | — | not started | Support Agent | — | — | — |

## Change history

- 2026-10-16 — D15 wording: the app shell is Mission 0 (FAMS-2027-00000, shakedown); the tank card is the pilot (FAMS-2027-00001) the Day-90 gate is judged on. Wording only in factory-vue-lead, -javascript, -tester, factory-challenger, factory-command-shared, two placeholders, README — Claude for Hennie.
- 2026-10-15 — command group drafted: factory-command-shared, factory-product-leader, factory-challenger, factory-knowledge-docs (0.1.0, UNDER REVIEW) — Claude for Hennie.
- 2026-10-15 — backend-team split into api-team (_shared, api-architect, api-developer, api-tester) and sql-team (_shared, sql-developer, sql-tester); the Unit Tester role sits per team — Claude for Hennie.
- 2026-10-15 — factory-core, factory-vue-shared and the five Vue role skills approved by Hennie → 1.0.0 VALID. Same day: live FAMS-API rule added (Vue team uses the live API only through the dedicated agent account, secrets on the VM, no write calls); FAMS-API code belongs to the API agent group — Claude for Hennie.
- 2026-10-13 — Registry and folder layout created; factory-core, factory-vue-shared and the five Vue role skills drafted (0.1.0); other 12 are placeholders — Claude for Hennie.

## Older skills (left as is; still used by running agents)

| Folder | Used by today | Note from the 13 Oct read |
|---|---|---|
| FAMS_VUE_AGENTS/* (7 skills) | 5 Vue agents | Imported; three claim VALID but cite `/src/FAMS.*` paths that don't exist; fams-tanks-business hard-codes thresholds the Product Owner hasn't set |
| FAMS_CORE | Vue agents (in BASE) | DRAFT |
| FAMS_VUE_CORE, FAMS_TANKS, FAMS_ATG, FAMS_API_CORE | other agents (per Hennie) | DRAFT |
| FAMS_DATABASE_CORE | — | VALID 28 Sep |
| FAMS_INTEGRITY, FAMS_INTEGRITY_CHECK | Data Integrity Agent | production |
| fams-support-agent/skills/similar-ticket-triage | Support Agent | paused |

These findings are why the new set doesn't copy them: the new skills state only what the
code and Hennie's decisions support, and leave product thresholds to the Product Owner.
