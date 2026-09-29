# FAMS Integrity AI — Project Instructions

This project investigates data integrity in the FAMS Azure SQL database.

**The actual skill definition is in `SKILL.md`** — that file (with its YAML
frontmatter) is what the Skill system reads to decide when to trigger and
what to do. This CLAUDE.md is Claude Code's separate project-memory file
(auto-loaded every session in this repo) and exists to point you at the
right place and give a couple of standing rules that apply regardless of
which specific investigation you're running.

## Standing rules
- Never run UPDATE/DELETE against UsageDispensing (or IOT/Android variants)
  without first running the read-only SELECT preview and getting explicit
  user confirmation of the exact ID list.
- Never hardcode DB credentials — see `scripts/db_connect.py` for the env
  var contract.
- Start every investigation in `SKILL.md`, which routes you into
  `knowledge/`, `anomaly-library/`, `business-rules/`, `algorithms/`,
  `investigation/`, `reports/`, `prompts/`, and `datasets/` as needed.
