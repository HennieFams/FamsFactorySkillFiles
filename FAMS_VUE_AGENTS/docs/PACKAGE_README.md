# FAMS Portal — Claude Code Skills

Drop this folder's contents into the root of your FAMS-UI repository and `git add .claude docs README.md`.

## Layout

```
.claude/skills/                 ← Claude Code auto-loads these when the task matches
├── fams-portal-master/         ← Load first for most FAMS-UI work (architecture, reactivity, Pinia, routing, services, deploy)
├── fams-vue-core/               ← PrimeVue 4 components, Tailwind styling, Pilot #1 UI (TankCard, DeviceStatus)
├── fams-atg-communications/     ← Serial/TCP, Veeder-Root protocol, checksum validation (IoT/edge layer)
├── fams-tanks-business/         ← Tank volume math, capacity thresholds, telemetry status
├── fams-dispensing/             ← Quick Dispensing feature (🟡 prototype — see gap checklist in its SKILL.md)
│   └── reference/                  Working bug-fixed source files for the dispensing feature
└── fams-quick-report/           ← Legacy "Quick Report" menu rebuild spec (🔵 reference, 10 sub-views, 8 UI patterns)
                                     ⚠️ contains a naming collision warning vs. fams-dispensing — read it first

docs/
├── FAMS_SKILLS_INTEGRATION_INDEX.md   ← Dependency map + reading order across all 5 skills
└── archive/                            Prior consolidation summaries, v2 draft docs, superseded reactive-patterns doc
                                         (context only — not loaded as skills, not needed day-to-day)
```

## Why the split

Claude Code decides whether to load a skill by matching your request against its `description:` frontmatter. Keeping each skill scoped to one folder with a tight description means the right context gets pulled in automatically instead of always loading everything. The `docs/archive/` material was mostly repeated project-status narration from earlier consolidation passes — kept for history, not structured as skills, and won't get triggered.

## After committing

Open a Claude Code session anywhere inside this repo and it should pick up the relevant skill(s) automatically — e.g. "add a new dispensing action" should pull in `fams-dispensing` (and `fams-portal-master` for structure). If a skill isn't triggering when it should, the fix is almost always to sharpen its `description:` line, not to change the folder structure.

## Known gaps to track

- `fams-dispensing` is prototype-status: mock data, no service-layer wiring, local-only balance mutation on submit. Its `SKILL.md` has a full checklist (§5) for hardening it — work through that before this feature goes to production.
- `fams-quick-report` describes the **legacy system to be rebuilt**, not existing Vue 3 code — none of its 10 sub-views exist yet in FAMS-UI. It also flags a real security issue in the legacy backend (`clientKey`/`accountkey` passed as URL query params) that must not be carried forward into the rebuild.
- ⚠️ **Naming collision:** "Dispensing" refers to two different features — the transactional quick-action dialog (`fams-dispensing`) and a reporting/analytics view over historical transactions (`fams-quick-report`'s "QuickDispenseNew"). Keep their routes, composables, and component names distinct.
