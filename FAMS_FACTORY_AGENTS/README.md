# FAMS_FACTORY_AGENTS — the factory's skill set (2026 →)

New skill set for the FAMS AI factory agents (15 agents in 5 groups), written fresh from the code and Hennie's
decisions (13 Oct 2026). The older skill folders in this repo (FAMS_API_CORE, FAMS_ATG,
FAMS_CORE, FAMS_DATABASE_CORE, FAMS_INTEGRITY, FAMS_INTEGRITY_CHECK, FAMS_TANKS,
FAMS_VUE_AGENTS, FAMS_VUE_CORE, fams-support-agent/skills) are **left as they are**: the
agents running today still use them.

## Layout

```
FAMS_FACTORY_AGENTS/
  REGISTRY.md                version, owner, status, sources for every skill below
  _core/                     factory-core            every agent, read first
  command/
    _shared/                 factory-command-shared
    product-leader/          factory-product-leader  (CEO agent / coordinator)
    challenger/              factory-challenger      (non-Claude model)
    knowledge-docs/          factory-knowledge-docs
  vue-team/
    _shared/                 factory-vue-shared
    vue-lead/  vue-html-css/  vue-javascript/  vue-tester/  vue-reviewer/
  api-team/                  (owns FAMS-API; tank-card pilot)
    _shared/  api-architect/  api-developer/  api-tester/
  sql-team/                  (DEV database; tank-card pilot)
    _shared/  sql-developer/  sql-tester/
  operations/
    _shared/  data-integrity/  support/
```

Each folder holds one `SKILL.md` (plus reference files later if a skill grows).
An agent loads three skills: **factory-core + its group's `_shared` + its own role skill**.
Example: FAMS Vue JavaScript = `factory-core`, `factory-vue-shared`, `factory-vue-javascript`.

## Rules

- Skill names all start with `factory-` so they never clash with the older skills in Paperclip.
- Metadata lives in `REGISTRY.md`, not in the SKILL.md files.
- A rule that applies to every agent goes in `_core`; to a whole group, in that group's
  `_shared`; only role-specific knowledge goes in the role folder. Fix a rule in one place.
- A skill whose description starts with "NOT READY" must not be assigned to an agent.
- Owner and Knowledge Steward: Hennie. Every change gets a line in REGISTRY.md.

## Switching an agent over (later, after the skill setup phase)

Paperclip lists skills from this repo by name (e.g. `henniefams/famsfactoryskillfiles/factory-vue-lead`).
After a `git pull` on the VM, check the new names appear in the company skill list (the
folder names start with `_`; confirm Paperclip imports those), then change the agent's
skill list (e.g. `BASE`/`skills` in `fams-vue-agents/scripts/create-agents.mjs`). Nothing
is switched yet.
