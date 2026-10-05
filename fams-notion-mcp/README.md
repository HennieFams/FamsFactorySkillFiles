# Notion MCP for the Paperclip agents

Gives the Claude agents in Paperclip (CEO, Database Integrity, …) Notion tools so they can
**read and edit pages**. They see **only the pages you share with the integration**.

## Why not the hosted Notion MCP (`https://mcp.notion.com/mcp`)?
The hosted server only accepts a browser OAuth login and Notion says unattended agents aren't
supported yet. Paperclip agents run unattended on the VM, so they use Notion's open-source server
(`@notionhq/notion-mcp-server`, pinned to 2.5.2) with an internal integration token instead.
Use the hosted server for things *you* drive interactively (Claude Desktop, Hermes on the laptop).

Note: Notion now only actively supports the hosted server; the open-source one still works
against the normal Notion API but may be retired one day. If that happens, re-check the
hosted server's unattended support.

## 1. Create the integration (Notion)
1. notion.so/profile/integrations → **New integration** → **Internal**
   - Name: `FAMS Agents` · Workspace: FAMS
2. **Configuration → Capabilities:** Read content, Update content, Insert content
   (+ Read/Insert comments if agents should comment). Leave user information off unless needed.
3. Copy the **Internal integration secret** (`ntn_…`).
4. **Share pages with it:** open each top-level page the agents may work in (e.g. *FAMS Workspace
   Portal*) → `•••` → **Connections** → add `FAMS Agents`. Sub-pages are included.
   Anything not shared is invisible to the agents.

Keep this separate from the read-only `FAMS Support Agent` integration used by `notion_sync.py`.

## 2. Install on the VM
```bash
cd /data/paperclip/github-skills/FamsFactorySkillFiles && git pull
cd fams-notion-mcp && sudo bash install.sh
```
It installs the server into `/paperclip/notion-mcp` (Paperclip's data volume, survives restarts),
asks for the secret (hidden), stores it in `/paperclip/notion-mcp/token` (chmod 600 — not in git,
not in `.claude.json`), checks it with Notion, and registers an MCP server called **`notion`** at
user scope for the user that runs the agents.

The check line should show `"object":"user","type":"bot"` with the integration's name.
`401 unauthorized` = wrong secret.

Change the secret later: run `install.sh` again. Remove from the agents: `sudo bash install.sh --remove`.

## 3. Test with an agent
Create a Paperclip issue for the CEO agent:
> List the Notion tools you have (names starting with `mcp__notion__`), then search Notion for
> "FAMS Support" and give me the page title and URL. Don't change anything.

If it says it has no Notion tools, Paperclip starts that agent with a different Claude config
folder. Check where with:
```bash
docker exec docker-server-1 sh -c 'ls -d /root/.claude* /home/*/.claude* /paperclip/*/.claude* 2>/dev/null'
```
and tell Claude what it shows.

## Which agents get it
Every Claude agent that shares that config gets the tools. To keep one agent out, add
`"mcp__notion"` to `permissions.deny` in that agent's `.claude/settings.json` — the FAMS Support
Agent already has this (it reads Notion read-only through `notion_sync.py`).

Tell agents in their `AGENTS.md` what they may edit, e.g. *"You may create and update pages under
FAMS Workspace Portal. Never delete pages or blocks; never move pages without approval."*
Deleting is technically possible with Update content, so put this rule in writing.
