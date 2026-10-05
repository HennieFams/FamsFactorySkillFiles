# FAMS Support Agent — build pack

Paperclip agent that wakes when a Freshdesk ticket is created, compares it with past
resolved tickets (monthly per-ticket JSON exports in Azure Blob Storage), and — only when there is a strong,
consistent known fix — emails a proposed answer to **schalk@fams.co.za**. Customers are
never contacted.

```
Freshdesk "ticket created" automation ──POST + Bearer──▶ Caddy :443 (only the /fire path is public)
                                                            │
                                         Paperclip routine "Triage new Freshdesk tickets"
                                                            │ wakes
                                                  FAMS Support Agent (claude_local)
     ┌───────────────────────────────┬──────────────────────┼─────────────────────────────┐
 Freshdesk MCP (read-only)     ledger.py               search_similar.py              send_email.py
 list_recent / get_ticket /    claim → mark;           SQLite FTS5 index of           SendGrid proxy; refuses any    
 get_ticket_conversation       one email per ticket    resolved tickets + replies     address not allow-listed
                                                            ▲
                                       nightly routine: sync_blob.py → build_index.py
                                       (Azure Blob JSON → data/raw → data/history.db)
```

**Decision rule** (full version in `skills/similar-ticket-triage/SKILL.md`):
HIGH = ≥3 past tickets, same problem, ≥2 other customers, same concrete fix → email.
MEDIUM = 2 tickets from 2 other customers with the same fix → email flagged MEDIUM.
The proposed reply is written in the ticket's language (Afrikaans or English).
Anything weaker, or anything that needs this customer's own data checked → do nothing (logged).

## What's in the folder

| Path | Purpose |
|---|---|
| `agent/AGENTS.md` | Agent instructions (role + hard rules) |
| `skills/similar-ticket-triage/SKILL.md` | Step-by-step procedure, confidence table, email template |
| `scripts/sync_blob.py` | Mirror the JSON/CSV exports from Blob (only changed files), then rebuild index |
| `scripts/build_index.py` | Exports → SQLite FTS5 index of resolved tickets + agents' public replies |
| `scripts/search_similar.py` | Ranked similar tickets + clusters of agreeing resolutions (JSON) |
| `scripts/notion_sync.py` | Read-only copy of the Notion knowledge base (Approved entries, known fixes, guidance) — section 3b |
| `scripts/ledger.py` | Claim/mark processed tickets; stops duplicates |
| `scripts/send_email.py` | Sends via the FAMS SendGrid proxy (or dryrun) with a recipient allow-list |
| `config/column_map.json` | Export format settings (Freshdesk JSON default; CSV optional) |
| `config/agent.env.example` | Template for the secrets/settings file (real one lives only in the container) |
| `scripts/freshdesk_readonly_mcp.py` | Read-only Freshdesk MCP server (GET calls only) |
| `deploy/workspace/` | Installed as the agent's `.mcp.json` and `.claude/settings.json` |
| `deploy/set_config.sh` | Writes `agent.env` inside the container (hidden prompts) |
| `deploy/install.sh` | Installs into the Paperclip container at `/paperclip/fams-support-agent` (venv + uv), no restart |
| `deploy/paperclip-routines.json` | The two routines and their triggers |
| `deploy/Caddyfile` | Public HTTPS for the webhook path only |
| `deploy/freshdesk-automation-rule.md` | Exact Freshdesk rule settings |
| `tests/` | Synthetic tickets + `smoke_test.sh` (offline end-to-end check) |

---

## 1. Install on the VM

Paperclip runs in Docker (`docker-server-1`, compose folder `/data/paperclip/docker`) and its
agents run **inside that container as root**. So the agent's files go on Paperclip's existing
data volume, which the container sees as `/paperclip`:

| Inside the container | On the VM (same files) |
|---|---|
| `/paperclip/fams-support-agent` | `/data/docker/volumes/docker_paperclip-data/_data/fams-support-agent` |

That volume is already on the `/data` disk and survives container restarts and rebuilds, so
**no compose change and no Paperclip restart** are needed. The installer adds a private uv
binary and a Python virtualenv in that folder; the Paperclip image itself is not modified.

```bash
git clone https://github.com/<org>/fams-support-agent.git ~/fams-support-agent
cd ~/fams-support-agent
sudo bash deploy/install.sh
```
Expected ending: `python deps: OK` and the uv version. To update later:
`cd ~/fams-support-agent && git pull && sudo bash deploy/install.sh` (keeps `data/` and your
`column_map.json`).

Every other command in this README that starts with `$PY` runs **inside the container**. Open
a shell there first:
```bash
sudo docker exec -it docker-server-1 bash
export SUPPORT_AGENT_HOME=/paperclip/fams-support-agent
PY=$SUPPORT_AGENT_HOME/.venv/bin/python; S=$SUPPORT_AGENT_HOME/scripts
```

**Repo hygiene:** the repo holds code and instructions only. Secrets and environment-specific
URLs live only in `config/agent.env` inside the container; runtime data (index, ledger, outbox) stays in
`/paperclip/fams-support-agent/data` and is git-ignored. Never commit real ticket exports —
they contain customer names, phone numbers and sometimes passwords.

## 2. Secrets and settings (`config/agent.env`)

Paperclip's agent form has no fields for environment variables or extra CLI arguments, so
the agent's secrets and settings live in one file inside the container,
`/paperclip/fams-support-agent/config/agent.env` (chmod 600, never in git). Fill it in from
the VM; what you type is hidden:

```bash
sudo bash deploy/set_config.sh
```

| Asked for | Where to get it |
|---|---|
| Freshdesk API key | Freshdesk → profile picture → Profile settings → *Your API Key* |
| Blob SAS URL | Storage account → Containers → `ticketingfolder` → *Shared access tokens*, **Read + List**, HTTPS only, 12 months → *Blob SAS URL* |
| SendGrid proxy base URL | the api24 SendGrid base, `https://…/api/SendGrid` (unauthenticated — never commit it) |
| Notion integration token | see section 3b (optional until the knowledge base is connected) |
| Email mode | `dryrun` for now |
| Start time | now, in UTC — older tickets are ignored |

It ends by printing the settings and whether each secret is present. Run it again any time
to change one value (blank = keep).

**How the guard rails work without CLI flags:**
- Freshdesk access is a small **read-only MCP server** in this pack
  (`scripts/freshdesk_readonly_mcp.py`). It contains only GET calls, so replying, noting or
  editing in Freshdesk is impossible, whatever the agent tries.
- The agent's working folder (`/paperclip/fams-support-agent/workspace`) holds `.mcp.json`
  (loads only that server) and `.claude/settings.json` (denies curl, wget and web fetches).
- `send_email.py` sends only to `SUPPORT_EMAIL_ALLOWED_TO` and checks the HTTP status.

## 3. History format + first index build

The history is the monthly per-ticket JSON export you already upload to Blob
(`ticket_<id>.json` with `original` + `conversations`, plus `_summary.json`). The indexer:

- uses only **resolved (4) / closed (5)** tickets;
- drops **outbound tickets (source 10)** — e.g. agents sending login details — and redacts
  anything that looks like `Password: …` / `Wagwoord: …` before indexing;
- treats the **agents' public replies** as the resolution, the customer's later messages as
  extra symptoms, and **private notes** as reviewer-only context;
- counts "different users" by **company_id** (falls back to requester_id), because the
  export has no requester email;
- weights the **description** above the subject (subjects are often just the company name)
  and handles Afrikaans + English.

Settings live in `config/column_map.json` (globs, statuses, excluded sources; a CSV layout is
there too if you ever export CSV instead — set `"format": "csv"`).

1. The prefix is `ticketingfolder/freshdesk_conversations/tickets_tecmo/` (confirmed: blob
   names do start with `ticketingfolder/`). It's already the default in `agent.env`.
2. Build it once by hand, in the container shell from step 1:
```bash
export AZURE_BLOB_CONTAINER_SAS_URL='https://...'      # same value as the secret
export AZURE_BLOB_PREFIX='ticketingfolder/freshdesk_conversations/tickets_tecmo/'   # adjust after the check above
$PY $S/sync_blob.py
```
   It prints e.g. `{"indexed_tickets": 640, "with_agent_reply": 610, "distinct_requesters": 85}`.
3. Sanity-check with a real past problem (try both languages):
```bash
$PY $S/search_similar.py --description "bowser transaksies trek nie deur op FAMS nie"
$PY $S/search_similar.py --description "no data reflecting on FAMS portal"
```
4. Offline test of the whole script chain (no Azure/Freshdesk needed), on the VM from the repo: `bash tests/smoke_test.sh`

**What to expect from the hit rate.** In the November sample, most closed tickets were
solved by a question, a site visit, a quote or work "on our side" — only a few replies state a
reusable fix (e.g. the OWW/Limesale bowser battery explanation, changing vehicle registrations
and setting DWN). The agent is built to stay quiet on the rest, so at first expect it to email
Schalk on a minority of tickets. That share grows as agents write the actual fix into their
replies.

## 3b. Notion knowledge base (FAMS Workspace Portal → FAMS Support)

The support team writes solved cases in Notion; the agent learns from the **Approved** ones.
`scripts/notion_sync.py` (read-only) copies three things:

| Notion | Becomes | Used for |
|---|---|---|
| **Support Knowledge Base** (Status = Approved) | `data/raw/notion/ticket_KB-<n>.json`, indexed with the history as ticket id `KB-<n>` | similar-case search — an approved entry is strong evidence (see SKILL.md table) |
| **Known Fixes Playbook** (Status = Approved) | `data/notion/known_fixes_notion.md` | playbook matches; same code as `known_fixes.md` → Notion wins |
| page section **Support guidance** | `data/notion/guidance.md` | rules applied to every proposed answer |

Draft, Retired, and the guide's `EXAMPLE …` entry are ignored; a retired entry disappears from
the index on the next sync. Credentials are redacted the same way as ticket history.

**Connect it once:**
1. notion.so/profile/integrations → **New integration** → *Internal*, name "FAMS Support Agent",
   workspace FAMS, capabilities **Read content only** → copy the token (`ntn_…`).
2. Open the **FAMS Support** page → `•••` → **Connections** → add "FAMS Support Agent"
   (this gives it the page and both databases, nothing else).
3. On the VM: `sudo bash deploy/set_config.sh` → paste the token at the Notion prompt
   (Enter for everything else).
4. Test in the container shell:
```bash
H=/paperclip/fams-support-agent; $H/.venv/bin/python $H/scripts/notion_sync.py
# {"notion": "ok", "kb_entries": 0, "known_fixes": 0, "guidance_points": 4, ...}
```
`kb_entries`/`known_fixes` stay 0 until entries are set to **Approved**.

It runs at the start of every triage run (skipped if the last sync is < 60 min old) and in the
nightly refresh routine. The database/page ids are built in; override them in `agent.env`
(`NOTION_KB_DATABASE_ID`, `NOTION_FIXES_DATABASE_ID`, `NOTION_SUPPORT_PAGE_ID`) if the pages move.

## 4. Create the agent in Paperclip

Agents → **New Agent**:

| Field | Value |
|---|---|
| Name | FAMS Support Agent |
| Role | general |
| Reports to | your CEO agent |
| Adapter | **Claude Code**, same sign-in/subscription as the CEO agent |
| Model | same as the CEO agent (a Sonnet model is plenty) |
| Working directory (cwd) | `/paperclip/fams-support-agent/workspace` |
| Heartbeat | **off** — it only runs when a routine wakes it |

**Instructions tab:** replace the default text with the short contents of
`agent/PAPERCLIP_INSTRUCTIONS.md`. It tells the agent to read
`/paperclip/fams-support-agent/agent/AGENTS.md` from disk, so later updates arrive with
`install.sh` and you never have to re-paste.

**Freshdesk access:** the agent reads Freshdesk through the read-only command line
`scripts/freshdesk.py` (GET requests only). This works however Paperclip launches Claude Code.
The same calls are also available as an MCP server (`scripts/freshdesk_readonly_mcp.py`,
`workspace/.mcp.json`) if Paperclip ever loads project MCP servers — not required.

**Test run.** Create an issue assigned to the agent:
> *Lockdown check: follow your instructions file, then run `settings.py` and
> `freshdesk.py recent --per-page 3` and report the settings and the three ticket ids and
> subjects. Do not process any tickets and do not send email.*

Expected comment: settings with all three secrets `true`, and three real recent tickets.

## 5. Routines

In Paperclip → Routines create the two routines in `deploy/paperclip-routines.json`
(UI is simplest; API: `POST /api/routines/{routineId}/triggers` for each trigger).

- **Triage new Freshdesk tickets** — webhook trigger only (`signingMode: bearer`), no schedule.
  When you save the webhook trigger Paperclip shows `webhookUrl` and `webhookSecret` **once** —
  copy both now. Each run also sweeps Freshdesk's latest tickets against the ledger, so if a
  webhook call is ever lost, that ticket is picked up on the next ticket's run (or click
  *Run now* on the routine to sweep manually).
- **Refresh historical ticket index** — nightly 02:15.

`concurrencyPolicy: coalesce_if_active` is fine: if three tickets arrive during one run they
are swept up together, and the ledger prevents doubles.

## 6. Public HTTPS for the webhook only

Freshdesk is in the cloud, so it needs to reach one URL on the VM. Only the routine-trigger
`/fire` path is exposed; the Paperclip UI stays private.

```bash
sudo apt install -y caddy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo mkdir -p /var/log/caddy && sudo chown caddy:caddy /var/log/caddy
echo 'WEBHOOK_HOST=famsfactory-vm.southafricanorth.cloudapp.azure.com' | sudo tee /etc/default/caddy
sudo systemctl edit caddy     # add:  [Service]  EnvironmentFile=/etc/default/caddy
sudo systemctl restart caddy
```
Azure Portal → VM → Networking → add inbound rule **TCP 443**. Best practice: source = the
Freshdesk outbound IP list for your Freshdesk data centre (Freshdesk support article
"IP whitelisting"; I couldn't fetch the current list from here, so look it up). The path is
also protected by the bearer secret and a 5-minute replay window.

Test from your laptop:
```bash
curl -i -X POST https://<host>/api/routine-triggers/public/<publicId>/fire \
  -H "Authorization: Bearer <webhookSecret>" -H "Content-Type: application/json" -d '{"ticket_id":"test"}'
curl -i https://<host>/                       # must be 404
```

## 7. Freshdesk rule

Follow `deploy/freshdesk-automation-rule.md`.

## 8. Go-live sequence

1. **Dry run (1–2 weeks).** `SUPPORT_EMAIL_MODE=dryrun`. Every email the agent *would* have
   sent is written to `/paperclip/fams-support-agent/data/outbox/` (on the VM:
   `sudo ls /data/docker/volumes/docker_paperclip-data/_data/fams-support-agent/data/outbox`). Review them with Schalk:
   right tickets? right confidence? any false positives?
2. Tune if needed: thresholds/wording in `SKILL.md`; search weights in `search_similar.py`
   (`bm25(..., 4.0 subject, 2.0 description, 0.5 resolution, 1.5 tags)`).
3. **Live to Schalk.** `sudo bash deploy/set_config.sh` → Email mode `fams_proxy`. Every email still lands in the outbox
   folder too, as an audit trail.
4. Later, replying to customers directly is a separate change: remove `create_ticket_reply`
   from the deny lists *and* change hard rules 1–2 in `AGENTS.md`. Don't do one without the other.

## Day-to-day

```bash
# inside the container (step 1 shell)
$PY $S/ledger.py recent 20          # what happened to the latest tickets
$PY $S/ledger.py release <id>       # let a crashed/error ticket be retried
ls -lt $SUPPORT_AGENT_HOME/data/outbox | head
```
Run history and the agent's per-run comments are on the routine's Runs page in Paperclip.

## Things to check during setup

- **How the webhook payload reaches the agent's issue.** Paperclip stores it on the routine
  run; the docs don't say whether it's copied into the issue text. The design doesn't depend
  on it: every run sweeps `list_recent_tickets` and uses the ledger, so the webhook only has
  to *wake* the agent.
- **Project MCP approval.** `.claude/settings.json` in the workspace pre-approves the
  `freshdesk` server (`enableAllProjectMcpServers`). The step-4 test run confirms Claude Code
  loads it; if the agent reports no Freshdesk tools, tell me what it said.
- **Residual risk:** `agent.env` is readable by the agent's user (the scripts need it). The
  instructions forbid reading it and the workspace settings deny the obvious ways, but it
  isn't a hard wall. For stronger isolation later, run the Freshdesk MCP as a separate service.
