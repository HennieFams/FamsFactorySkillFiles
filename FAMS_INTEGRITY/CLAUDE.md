# FAMS Integrity AI — Project Instructions

This project investigates data integrity in the FAMS Azure SQL database.

**The actual skill definition is in `SKILL.md`** — that file (with its YAML
frontmatter) is what the Skill system reads to decide when to trigger and
what to do. This CLAUDE.md is Claude Code's separate project-memory file
(auto-loaded every session in this repo) and exists to point you at the
right place and give a couple of standing rules that apply regardless of
which specific investigation you're running.

## Standing rules
- All database access goes through `scripts/fams_db.py` (read-only guard +
  always-rollback). The login has admin rights; the guard is the only thing
  preventing writes. Never open a connection any other way.
- Never run UPDATE/DELETE yourself. For a data fix, give the user the
  read-only SELECT preview, the exact ID list, and the write statement to run
  in SSMS after review.
- Never hardcode DB credentials — env vars only (see `scripts/fams_db.py`).
- Start every investigation in `SKILL.md`, which routes you into
  `knowledge/`, `anomaly-library/`, `business-rules/`, `algorithms/`,
  `investigation/`, `reports/`, `prompts/`, and `datasets/` as needed.
