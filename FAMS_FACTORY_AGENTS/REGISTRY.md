# FAMS factory skill registry

Metadata for every skill in `FAMS_FACTORY_AGENTS/` (Blueprint Rev 2 §19). Owner of every
skill: **Hennie (Knowledge Steward)**. Statuses: VALID · REVIEW REQUIRED · UNDER REVIEW ·
DEPRECATED · ARCHIVED; "not started" = placeholder only.
A skill becomes VALID when Hennie has reviewed it against the code/decisions named under
Sources. Only VALID skills are given to agents.

## Factory skill set (D16, 16 Oct 2026: Blueprint Rev 2 §79 seed + §80 roles)

### Core and knowledge (§79 seed)

| Skill | Folder | Version | Status | For | Sources | Last validated | Next review |
|---|---|---|---|---|---|---|---|
| factory-core (FAMS_CORE) | _core | 1.1.0 | REVIEW REQUIRED (D16 wording) | every factory agent | Blueprint Rev 2; decisions r1–r3, D4–D16 (phase-1/READINESS.md); branching model | 2026-10-15 (1.0.0) | on Hennie's review |
| factory-vue-core (FAMS_VUE_CORE) | knowledge/vue-core | 1.1.0 | REVIEW REQUIRED (renamed from factory-vue-shared, wording only) | Vue Developer; Architecture, Unit Tester, Challenger on Vue work | FamsVue3_2027 development-agent; FAMS-API TokenController, FAMSlegacyController, Program.cs; legacy Fams24 FAMS-UI main.js and moduleAuthActions.js; fams-ui-standards decisions | 2026-10-15 (1.0.0) | on Hennie's review |
| factory-api-core (FAMS_API_CORE) | knowledge/api-core | — | not started | ASP.NET Developer, Architecture, Unit Tester | — | — | pilot prep |
| factory-database-core (FAMS_DATABASE_CORE) | knowledge/database-core | — | not started | SQL Developer, Architecture, Unit Tester | — | — | pilot prep (r5) |
| factory-tanks (FAMS_TANKS) | knowledge/tanks | — | not started | pilot roles | — | — | pilot prep (archaeology §78) |
| factory-atg (FAMS_ATG) | knowledge/atg | — | not started | pilot roles | — | — | pilot prep (archaeology §78) |
| factory-mission (Feature Template) | knowledge/mission | 0.2.0 | UNDER REVIEW (renamed from factory-command-shared; 8-role team) | Coordinator, Architecture, Knowledge/Docs, Challenger | Blueprint Rev 2 §59, §80–§83; 90-day plan; decisions r1–r3, D4–D16 | — | on Hennie's review |

### Roles (§80 first mini-team)

| # | Skill | Folder | Version | Status | Paperclip agent | Loads | Made from |
|---|---|---|---|---|---|---|---|
| 1 | factory-product-leader | roles/1-product-coordinator | 0.2.0 | UNDER REVIEW | FAMS Product Leader (ex-CEO) | core, mission | command/product-leader |
| 2 | factory-research-architecture | roles/2-research-architecture | 1.1.0 | REVIEW REQUIRED | Research / Architecture Agent (ex-Vue Lead) | core, mission, vue-core (+ api-core, database-core, tanks, atg for the pilot) | vue-lead 1.0.0 + api-architect plan + §78 |
| 3 | factory-sql-developer | roles/3-sql-developer | — | not started | not created | core, database-core, tanks, atg | sql-developer stub |
| 4 | factory-api-developer (ASP.NET Developer) | roles/4-aspnet-developer | — | not started | not created | core, api-core, database-core | api-developer stub |
| 5 | factory-vue-developer | roles/5-vue-developer | 1.1.0 | REVIEW REQUIRED | Vue Developer (ex-Vue JavaScript) | core, vue-core | vue-javascript 1.0.0 + vue-html-css 1.0.0 merged |
| 6 | factory-unit-tester | roles/6-unit-tester | 1.1.0 | REVIEW REQUIRED | Unit Tester (ex-Vue Tester) | core, vue-core (+ api-core, database-core for the pilot) | vue-tester 1.0.0 + api/sql tester plans |
| 7 | factory-knowledge-docs | roles/7-knowledge-docs | 0.2.0 | UNDER REVIEW | not created | core, mission | command/knowledge-docs |
| 8 | factory-challenger | roles/8-challenger | 0.2.0 | UNDER REVIEW | Independent Challenger (ex-Vue Reviewer) | core, mission, vue-core | command/challenger + vue-reviewer 1.0.0 checklist |

Paused: the Vue HTML-CSS agent (work moved to the Vue Developer). Outside the factory, with
their existing skills: Database Integrity Agent, FAMS Support Agent.

### Deprecated (kept because Paperclip cannot delete an imported skill)

All in `_deprecated/<name>/`, 16 Oct 2026 (D16). Each SKILL.md now only says what replaced it.

| Skill | Replaced by |
|---|---|
| factory-command-shared | factory-mission |
| factory-vue-shared | factory-vue-core |
| factory-vue-lead | factory-research-architecture |
| factory-vue-html-css, factory-vue-javascript | factory-vue-developer |
| factory-vue-tester, factory-api-tester, factory-sql-tester | factory-unit-tester |
| factory-vue-reviewer | factory-challenger |
| factory-api-shared | factory-api-core |
| factory-api-architect | factory-research-architecture (Contract Guardian) |
| factory-sql-shared | factory-database-core |
| factory-operations-shared, factory-data-integrity, factory-support | nothing (agents stay outside the factory) |

## Change history

- 2026-10-16 — D16: team realigned to Blueprint Rev 2 §80 (8 roles) and §79 seed names. New: factory-research-architecture, factory-vue-developer, factory-unit-tester, factory-vue-core, factory-api-core, factory-database-core, factory-tanks, factory-atg, factory-mission. Kept and updated: factory-core, factory-product-leader, factory-challenger, factory-knowledge-docs, factory-sql-developer, factory-api-developer. 15 deprecated. Changed VALID skills set to REVIEW REQUIRED until Hennie re-approves — Claude for Hennie.
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
