# FAMS Data Integrity Agent — code pack

Code for the daily integrity check. The skills (`FAMS_INTEGRITY`,
`FAMS_INTEGRITY_CHECK`) are docs-only because Paperclip's skill importer rejects
skills that contain executable scripts. Everything executable lives here and is
installed into the Paperclip container, the same way `fams-support-agent` is.

| Path | Purpose |
|---|---|
| `scripts/fams_db.py` | The only DB access layer: env-var credentials, lexing read-only guard, always-rollback, `ApplicationIntent=ReadOnly` |
| `scripts/run_checks.py` | Daily engine: windows per client, data pull, checks C01–C24, writes `findings.json` + evidence CSVs |
| `scripts/integrity_checks.py` | The checks (pure functions over DataFrames) |
| `scripts/fams_sources.py` | Live-DB source and export-directory source |
| `scripts/run_query.py`, `scripts/db_connect.py` | Ad hoc read-only query runner / connection test (used by FAMS Integrity investigations) |
| `config/config.json` | Accounts per client, boundaries, thresholds, known patterns — edit here, in git |
| `sql/get_ReportinglogbookRev6SARS.sql` | Production SARS proc, verbatim (reference for `business-rules/sars-schedule6.md`) |
| `tests/` | Offline tests: guard bypass suite + end-to-end engine run on synthetic data |
| `agent/` | Agent instructions for the Paperclip agent |
| `deploy/install.sh` | Installs into `/paperclip/fams-integrity-agent` (venv via uv), no restart |

## 1. Install / update on the VM

```bash
cd /data/paperclip/github-skills/FamsFactorySkillFiles && git pull
sudo bash fams-integrity-agent/deploy/install.sh
```

Expected ending: `python deps: OK` and `67 passed`.

## 2. Connection test (inside the container)

The agent's process gets `FAMS_DB_HostName`, `FAMS_DB_DBName`, `FAMS_DB_UserName`,
`FAMS_DB_Password` from Paperclip secrets. To test by hand, open a shell in the
container with those set (never paste them into chat or an issue):

```bash
sudo docker exec -it docker-server-1 bash
H=/paperclip/fams-integrity-agent; PY=$H/.venv/bin/python
$PY $H/scripts/db_connect.py --test
```

## 3. First supervised run

```bash
$PY $H/scripts/run_checks.py --out $H/runs/test-$(date +%F)
```

Check the printed summary, then `runs/.../<Client>/findings.json`: `data_sources`
(every table should have rows), `data_gaps` (no `FAILED` entries) and `checks_run`.
Confirm DB timestamps are SAST (`db_timezone` in config).

## 4. Paperclip agent

Agent instructions: `cat /paperclip/fams-integrity-agent/agent/AGENTS.md` (see
`agent/PAPERCLIP_INSTRUCTIONS.md`). Skills to attach: FAMS Core, FAMS Database Core,
FAMS Integrity Check, FAMS Integrity.

## Running locally (Claude Code / Cowork)

```bash
pip install -r fams-integrity-agent/scripts/requirements.txt
export FAMS_SQL_USER=... FAMS_SQL_PASSWORD=...     # in your own shell only
python fams-integrity-agent/scripts/db_connect.py --test
python fams-integrity-agent/scripts/run_checks.py --client ShipTech --out out
python -m pytest -q fams-integrity-agent/tests
```
