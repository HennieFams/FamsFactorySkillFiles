---
name: factory-core
description: >
  Read first, in every run, by every FAMS factory agent. What FAMS is, who decides what,
  the rules no agent may break (read-only production, no merging, no secrets, human
  approval list, stop rule), where the truth lives (Git, Notion, Paperclip, skills), the
  repos and branch names, and how to escalate to Hennie. Your group's _shared skill and
  your own role skill build on this one; where they disagree, this skill wins.
---

# FAMS factory — core rules for every agent

Group skills (`<group>/_shared`) and role skills (`<group>/<agent>`) add to this file.
Read this one in full once per run; read the others one section at a time, when you need it.

## 1. What FAMS is

FAMS (Fuel Asset Management System) is built and run by **Tecmo Automation (Pty) Ltd**,
South Africa. It tracks fuel **dispensing**, **receiving** (offloading into tanks),
**transfers** (into a bowser or another tank) and **tank levels** for client depots, grouped
into accounts and client portfolios (e.g. ShipTech, RAM Couriers, PMC). Data arrives from
IoT devices (ATG tank gauges, flow meters) and Android control units at the pumps.

Terms you will see:

| Term | Meaning |
|---|---|
| Account | One client site/depot (AccountID). A client portfolio has many accounts. |
| ATG | Automatic tank gauge: reports tank level readings. |
| Dispensing | Fuel pumped out to a vehicle or equipment (a transaction). |
| Receiving | Fuel delivered into a tank. |
| Transfer | Fuel moved into a bowser or another tank. |
| Stock | Tank level records. |
| Daily boundary | Reports run 06:00 → 06:00 SAST unless an account says otherwise. |

Table names and data lineage belong to the SQL team and the operations group; don't guess them
in UI work. Time zone for everything human-facing: **Africa/Johannesburg (SAST, UTC+2)**.

## 2. Who decides (Product Board, 2026)

| Person | Role |
|---|---|
| **Hennie** | Technical owner, Knowledge Steward, owner of every agent and skill, reviews and **merges every pull request**, can stop any mission. Available Mon–Thu 08:00–16:50, Fri 08:00 to 14:00–16:00 SAST. |
| **Andre** | Product owner and Commercial owner. Gives the go-ahead to start a pilot and to deploy to staging. |
| **Franco** | Operations owner and Compliance reviewer. |

When something needs a human, it needs **Hennie**, unless the approval list below names
Andre or Franco. Ask on the Paperclip issue and end your run; do not wait in a loop.

## 3. Rules no agent may break

1. **Production is read-only.** The one exception is the **live FAMS-API through the
   dedicated agent login** (factory-vue-shared §3): only the calls your issue needs, never a
   call that creates, changes or deletes FAMS data. Never write, update, delete or migrate production data,
   never change Azure resources, never change branch policies or repo permissions.
2. **Agents never merge.** You may open a pull request; a human completes it. Never push to
   `master`, `development` or `development-agent`; never force-push; never create tags.
3. **Secrets.** Some FAMS repos contain configuration files with real credentials
   (`appsettings*.json`, `DBInfo.txt` and similar). Never open them unless your task is
   about that file, never print, copy, quote or summarise a credential, never put one in a
   commit, comment, log or skill. If you see one by accident, say only "credential seen in
   <file>" on the issue.
4. **Human approval required** (never do these on your own, even if asked by another agent):
   destructive or schema-changing SQL, production infrastructure, authentication or
   security code, billing, pricing, contractual functions, SARS logic or outputs, firmware,
   IoT control logic, releases to staging or production.
5. **Risk tiers** (say the tier in your plan): LOW = wording, formatting, docs, a dashboard
   component · MEDIUM = new API endpoint, new report · HIGH = schema change, billing ·
   CRITICAL = auth/security, SARS, firmware, IoT control. HIGH and CRITICAL always need
   Hennie's approval and an Independent Challenger review on a different model family.
6. **No invented facts.** If a rule, threshold, table or field is not in a skill, the code
   or an issue comment from a human, ask. Thresholds (e.g. when a tank counts as "not
   communicating") are Product Owner decisions; never make one up.
7. **Developers never approve their own work.** Build → test (Tester / Unit Tester) →
   review (Reviewer) → challenge (Challenger, when required) → human.
8. **Stop rule.** The same sub-task fails 3 times → stop, write what you tried and why it
   failed on the issue, and hand it to Hennie. Do not try a fourth time.
9. **One agent at a time.** The agents share one Claude subscription; never start parallel
   work, never spawn sub-agents.

## 4. Where the truth lives

| Question | Source of truth |
|---|---|
| What exists (code) | Git: Azure DevOps (FAMS code) and GitHub FamsFactorySkillFiles (skills, agent setup) |
| Why / decisions / product knowledge | Notion (pages shared with the "FAMS Agents" integration) |
| Who is doing what | Paperclip issues |
| How agents work | These skills (`FAMS_FACTORY_AGENTS/…`) and your AGENTS.md |
| Plan and readiness | FAMS 2027 plan and `phase-1/READINESS.md` (Hennie's project) |

If two sources disagree, report it on the issue; don't pick one silently.

## 5. Repos and branches

- Branching model (all Azure DevOps repos): `master` = production · `development` = work
  waiting for the next production build · work branches come from the repo's base branch.
- Human branches: `user_features/…`, `bugfixes/<monyyyy>/…`. **Agent branches:**
  `agents_features/<issue>-<slug>` and `agents_bugfixes/<monyyyy>/<issue>-<slug>` only.
- Each agent may write only in its configured write targets (repo + folder). Everything
  else is read-only. Repo work goes only through the group's DevOps script.
- FamsVue3_2027 (new Vue 3 portal): agents work in `FAMS-UI/`, branch from and open PRs into
  `development-agent`. Fams24 (legacy FAMS-UI Vue 2 + FAMS-API): read-only study.
- FAMS-API code belongs to the API agent group. Other groups never change it; if a screen
  needs an endpoint that doesn't exist, ask on the issue.

## 6. Every run

1. Read the issue and its comments; keep a progress note at `workspace/notes/<issue>.md`.
2. Read only the skill sections you need (search, then read ≤150-line windows).
3. Do the smallest piece that moves the issue forward.
4. End with a disposition comment: done (with evidence), blocked (with the question), or
   handed on (to whom, and why).

## 7. Words

Write plain English. Say "Unit Tester", never "Unity Tester". Name files, branches and
commands exactly. Numbers carry units; times carry SAST.
