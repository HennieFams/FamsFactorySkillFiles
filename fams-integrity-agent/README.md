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
| `scripts/send_reports.py` | Emails each client PDF to the four recipients (config `email`), logs to `email_log.json`, never double-sends |
| `scripts/publish_notion.py` | Upserts each site's daily page in the Notion client portal (Data Integrity Reports databases) + uploads the client PDF to Azure Blob |
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

Expected ending: `python deps: OK` and all tests passed.

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

## 4. Notion client portal (one-off setup)

1. **Switch off the old nightly job** that currently creates the "DD Mon YYYY"
   pages in each site's Data Integrity Reports database (and uploads
   `reconciliation-reports/<AccountID>_0_Combined_<date>.pdf`). From go-live the
   agent is the only writer; with both running you get two pages per day.
2. **Share with the integration:** in Notion, share *FAMS Client Portal* (or at
   least *Shiptech (pty) ltd Portal* and *FAMS Clients*) with the internal
   integration **FAMS Agents** with "Can edit content". The token is read from
   `/paperclip/notion-mcp/token` (installed by `fams-notion-mcp/install.sh`).
3. **PDF storage secret:** add a Paperclip secret `FAMS_BLOB_CONNECTION_STRING`
   (connection string of the storage account that holds the
   `reconciliation-reports` container) to the integrity agent. Without it pages
   are still published, just without the PDF link.
4. **Dry run** inside the container on a run folder produced by this version (older runs have no per-day data), no network writes:
   ```bash
   $PY $H/scripts/publish_notion.py --run-dir $H/runs/test-2026-10-02 --client PMC-Phalaborwa --dry-run
   ```
   then look at `runs/test-2026-10-02/PMC-Phalaborwa/notion_preview/*.json`.
5. **First live write on one site** (via an agent issue, so the secrets are present):
   `publish_notion.py --run-dir … --client PMC-Phalaborwa --pdf PMC-Phalaborwa=<pdf>`,
   then check the page in Notion before letting the full routine run.

Site ↔ AccountID ↔ database mapping lives in `config/config.json → notion.sites`
(verified 2026-10-05 from the AccountIDs in the old job's PDF links).

## 5. Paperclip agent

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
