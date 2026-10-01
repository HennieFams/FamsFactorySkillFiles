# FAMS Support Agent — build pack

Paperclip agent that wakes when a Freshdesk ticket is created, compares it with past
resolved tickets (monthly per-ticket JSON exports in Azure Blob Storage), and — only when there is a strong,
consistent known fix — emails a proposed answer to **schalk@fams.co.za**. Customers are
never contacted.

```
Freshdesk "ticket created" automation ──POST + Bearer──▶ Caddy :443 (only the /fire path is public)
                                                            │
                                         Paperclip routine "Triage new Freshdesk tickets"
                                         (+ hourly safety-net schedule, Mon–Fri 07–18)
                                                            │ wakes
                                                  FAMS Support Agent (claude_local)
     ┌───────────────────────────────┬──────────────────────┼─────────────────────────────┐
 Freshdesk MCP (read-only)     ledger.py               search_similar.py              send_email.py
 get_tickets / get_ticket /    claim → mark;           SQLite FTS5 index of           api24 SendGrid proxy; refuses any
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
| `scripts/ledger.py` | Claim/mark processed tickets; stops duplicates |
| `scripts/send_email.py` | Sends via the api24 SendGrid proxy (or dryrun) with a recipient allow-list |
| `config/column_map.json` | Export format settings (Freshdesk JSON default; CSV optional) |
| `config/mcp.json` | Freshdesk MCP server definition (`uvx freshdesk-mcp`) |
| `config/claude-settings.json` | Deny rules for every Freshdesk write tool, curl, wget, WebFetch |
| `config/paperclip-agent-adapter.json` | Adapter config to copy into Paperclip |
| `deploy/install.sh` | Copies everything to `/data/fams-support-agent`, installs deps + uv |
| `deploy/paperclip-routines.json` | The two routines and their triggers |
| `deploy/Caddyfile` | Public HTTPS for the webhook path only |
| `deploy/freshdesk-automation-rule.md` | Exact Freshdesk rule settings |
| `tests/` | Synthetic tickets + `smoke_test.sh` (offline end-to-end check) |

---

## 1. Install on the VM

```bash
scp fams-support-agent.zip <you>@famsfactory-vm:~
ssh <you>@famsfactory-vm
unzip fams-support-agent.zip && cd fams-support-agent
sudo PAPERCLIP_USER=<user that runs paperclip> bash deploy/install.sh
```
Everything lands on the data disk at `/data/fams-support-agent`. Note the `uvx` path the
script prints — if it isn't on the Paperclip service's PATH, put the full path in
`config/mcp.json` (`"command": "/home/<user>/.local/bin/uvx"`).

## 2. Credentials you need

| Secret (Paperclip → Company → Secrets) | Where to get it |
|---|---|
| `FRESHDESK_API_KEY` | Freshdesk → profile picture → Profile settings → *Your API Key*. The key has that agent's full rights — the agent is kept read-only by the deny rules, not by the key. |
| `AZURE_BLOB_CONTAINER_SAS_URL` | Azure Portal → Storage account → Containers → your export container → *Shared access tokens*. Permissions **Read + List** only, expiry 12 months, HTTPS only. Copy the *Blob SAS URL*. |

**Email** goes through FAMS's existing SendGrid proxy
(`https://api24.fams.co.za/api/SendGrid/SendMessageEmail`, sender already bound on the API
side), the same contract as `shared/email.py`: `{"email", "subject", "body"}`. No mail
credentials are needed on the VM. `send_email.py` still refuses every address except
`SUPPORT_EMAIL_ALLOWED_TO`, and checks the HTTP status before logging "sent".
Check once from the VM that api24 is reachable:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api24.fams.co.za/api/SendGrid/SendMessageEmail \
  -H "Content-Type: application/json" -d '{"email":"schalk@fams.co.za","subject":"VM test","body":"<p>test</p>"}'
```
(Graph and SMTP modes are still in the script if you ever need them — see its header.)

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

1. The adapter config uses `AZURE_BLOB_PREFIX=ticketingfolder/freshdesk_conversations/tickets_tecmo/`
   (the path from the old Azure Function). Blob names normally **don't** include the container
   name, so check the real paths first and drop the leading `ticketingfolder/` if needed:
   `az storage blob list --container-name ticketingfolder --account-name <acct> --num-results 5 --query "[].name" -o tsv`
2. Build it once by hand as the Paperclip user:
```bash
export SUPPORT_AGENT_HOME=/data/fams-support-agent
export AZURE_BLOB_CONTAINER_SAS_URL='https://...'      # same value as the secret
python3 $SUPPORT_AGENT_HOME/scripts/sync_blob.py
```
   It prints e.g. `{"indexed_tickets": 640, "with_agent_reply": 610, "distinct_requesters": 85}`.
3. Sanity-check with a real past problem (try both languages):
```bash
python3 $SUPPORT_AGENT_HOME/scripts/search_similar.py --description "bowser transaksies trek nie deur op FAMS nie"
python3 $SUPPORT_AGENT_HOME/scripts/search_similar.py --description "no data reflecting on FAMS portal"
```
4. Offline test of the whole script chain (no Azure/Freshdesk needed): `bash tests/smoke_test.sh`

**What to expect from the hit rate.** In the November sample, most closed tickets were
solved by a question, a site visit, a quote or work "on our side" — only a few replies state a
reusable fix (e.g. the OWW/Limesale bowser battery explanation, changing vehicle registrations
and setting DWN). The agent is built to stay quiet on the rest, so at first expect it to email
Schalk on a minority of tickets. That share grows as agents write the actual fix into their
replies.

## 4. Create the agent in Paperclip

1. Agents → **FAMS Support Agent** → adapter **Claude Code (claude_local)**, same Anthropic
   subscription as the CEO agent.
2. Copy the fields from `config/paperclip-agent-adapter.json`: `cwd`, instructions file,
   model, `extraArgs`, `env`. For the env entries marked `secretRef`, use the UI's secret
   picker to bind the secret (the JSON just shows which ones are secrets).
   - `extraArgs` loads **only** the Freshdesk MCP (`--strict-mcp-config`, so Hermes / CEO MCP
     servers never reach this agent), applies the deny settings, and passes
     `--disallowedTools` for every Freshdesk write tool.
   - `SUPPORT_AGENT_START_AT`: set to the moment you go live (UTC). Tickets older than this
     are ignored, so the first run doesn't email Schalk about the last 30 days.
   - Leave `SUPPORT_EMAIL_MODE=dryrun` for now.
3. Upload the skill: Skills → add `skills/similar-ticket-triage/SKILL.md` to this agent.
4. **Verify the tool lockdown** — run the agent manually with this task:
   *"List every tool you have whose name starts with mcp__freshdesk, then try to call
   mcp__freshdesk__create_ticket_note on ticket 1 with body 'test'. Report what happened."*
   Expected: only read tools listed; the note call is blocked. If the tool names differ
   (the MCP package renamed them), update both `claude-settings.json` and `extraArgs`.

## 5. Routines

In Paperclip → Routines create the two routines in `deploy/paperclip-routines.json`
(UI is simplest; API: `POST /api/routines/{routineId}/triggers` for each trigger).

- **Triage new Freshdesk tickets** — webhook trigger (`signingMode: bearer`) + business-hours
  hourly schedule. When you save the webhook trigger Paperclip shows `webhookUrl` and
  `webhookSecret` **once** — copy both now.
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
   sent is written to `/data/fams-support-agent/data/outbox/`. Review them with Schalk:
   right tickets? right confidence? any false positives?
2. Tune if needed: thresholds/wording in `SKILL.md`; search weights in `search_similar.py`
   (`bm25(..., 4.0 subject, 2.0 description, 0.5 resolution, 1.5 tags)`).
3. **Live to Schalk.** Set `SUPPORT_EMAIL_MODE=fams_proxy`. Every email still lands in the outbox
   folder too, as an audit trail.
4. Later, replying to customers directly is a separate change: remove `create_ticket_reply`
   from the deny lists *and* change hard rules 1–2 in `AGENTS.md`. Don't do one without the other.

## Day-to-day

```bash
S=/data/fams-support-agent/scripts
python3 $S/ledger.py recent 20          # what happened to the latest tickets
python3 $S/ledger.py release <id>       # let a crashed/error ticket be retried
ls -lt /data/fams-support-agent/data/outbox | head
```
Run history and the agent's per-run comments are on the routine's Runs page in Paperclip.

## Things I couldn't confirm from the docs — check during setup

- **How the webhook payload reaches the agent's issue.** Paperclip stores it on the routine
  run (`triggerPayload`); the docs don't say whether it's copied into the issue text. The
  design doesn't depend on it: every run sweeps `get_tickets` and uses the ledger, so the
  webhook only has to *wake* the agent.
- **Exact `env` secret-reference format** in the adapter JSON — use the UI picker.
- **`freshdesk-mcp` tool names** can change between versions; step 4.4 checks them. Pin a
  version in `mcp.json` (`"args": ["freshdesk-mcp==<version>"]`) once it works.
- **Residual risk:** the agent's process can see `FRESHDESK_API_KEY` (the MCP needs it). curl,
  wget and WebFetch are denied, and the instructions forbid direct API calls, but a determined
  script could still use it. For stronger isolation later, run the Freshdesk MCP as a separate
  read-only HTTP service under another user so the key never enters the agent's environment.
