# FAMS_FACTORY_AGENTS — the factory's skill set (2026 →)

Skill set for the FAMS AI factory, following **Blueprint Rev 2 §79 (initial skill seed)
and §80 (first mini-team, 8 roles)** — decision D16, 16 Oct 2026. Written fresh from the
code and Hennie's decisions. The older skill folders in this repo (FAMS_API_CORE, FAMS_ATG,
FAMS_CORE, FAMS_DATABASE_CORE, FAMS_INTEGRITY, FAMS_INTEGRITY_CHECK, FAMS_TANKS,
FAMS_VUE_AGENTS, FAMS_VUE_CORE, fams-support-agent/skills) are **left as they are**: the
Database Integrity Agent and the FAMS Support Agent still use them, outside the factory.

## Layout

```
FAMS_FACTORY_AGENTS/
  REGISTRY.md                    version, owner, status, sources for every skill below
  _core/                         factory-core             every factory agent, read first
  knowledge/                     §79 seed + the mission template
    vue-core/                    factory-vue-core         (FAMS_VUE_CORE)
    api-core/                    factory-api-core         (FAMS_API_CORE)
    database-core/               factory-database-core    (FAMS_DATABASE_CORE)
    tanks/                       factory-tanks            (FAMS_TANKS)
    atg/                         factory-atg              (FAMS_ATG)
    mission/                     factory-mission          (Feature File, flow, approvals)
  roles/                         §80 first mini-team
    1-product-coordinator/       factory-product-leader   FAMS Product / Coordinator
    2-research-architecture/     factory-research-architecture  (+ Contract Guardian)
    3-sql-developer/             factory-sql-developer
    4-aspnet-developer/          factory-api-developer    ASP.NET Developer
    5-vue-developer/             factory-vue-developer
    6-unit-tester/               factory-unit-tester      ("Unity / Tester")
    7-knowledge-docs/            factory-knowledge-docs
    8-challenger/                factory-challenger       (different model family)
  _deprecated/                   15 retired names, kept because Paperclip can't delete
```

An agent loads **factory-core + the knowledge skills its role needs + its role skill**
(the "Loads" column in REGISTRY.md). Example: Vue Developer = `factory-core`,
`factory-vue-core`, `factory-vue-developer`.

Mission 0 (app shell) uses roles 1, 2, 5, 6, 7 and 8. Roles 3 and 4 join for the pilot
(Tank Communication & Health Card).

## Rules

- Skill names all start with `factory-` so they never clash with the older skills in Paperclip.
- Metadata lives in `REGISTRY.md`, not in the SKILL.md files.
- A rule for every agent goes in `_core`; shared domain knowledge in `knowledge/`; only
  role-specific knowledge in `roles/`. Fix a rule in one place.
- A skill whose description starts with "NOT READY" or "DEPRECATED" must not be assigned.
- Owner and Knowledge Steward: Hennie. Every change gets a line in REGISTRY.md.

## Paperclip

Paperclip lists skills from this repo by name (e.g. `henniefams/famsfactoryskillfiles/factory-core`).
After a push, use **Check for updates** on an imported skill to pull the new content, and
import new names from the repo. Imported skills cannot be deleted, so a retired name stays
in the list with a DEPRECATED description.
