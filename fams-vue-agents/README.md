# FAMS Vue Agents — code pack

Five Paperclip agents that build FAMS Vue 3 user interfaces:
**FAMS Vue Lead**, **FAMS Vue HTML-CSS**, **FAMS Vue JavaScript**, **FAMS Vue Tester**,
**FAMS Vue Reviewer**. Other agents (or people) request UI work by assigning a Paperclip
issue to the FAMS Vue Lead.

```
request issue ──▶ FAMS Vue Lead ── asks questions, plans, creates sub-issues one at a time
                        │
                        ├─▶ FAMS Vue JavaScript   services / composables / stores / router
                        ├─▶ FAMS Vue HTML-CSS     pages / components / styling
                        ├─▶ FAMS Vue Tester       tests + lint + build + speed budget → PASS/FAIL
                        └─▶ FAMS Vue Reviewer     independent review → APPROVE / CHANGES
                        │
                        └─▶ pull request in Azure DevOps ──▶ a human approves and merges
```

| Path | Purpose |
|---|---|
| `../FAMS_VUE_AGENTS/` | The Vue skills, **imported unchanged** (fams-portal-master, fams-vue-core, fams-tanks-business, fams-atg-communications, fams-quick-report, fams-dispensing + `docs/`), plus the new house-rules skill `fams-ui-standards` |
| `agent/COMMON.md` | Rules for all five agents |
| `agent/AGENTS-<role>.md` | Each agent's job (lead, html-css, javascript, tester, reviewer) |
| `agent/PAPERCLIP_INSTRUCTIONS.md` | The five short blocks to paste into Paperclip's Instructions tab |
| `scripts/devops.mjs` | The only way the agents touch Azure DevOps: clone, `agents/…` branches, commit (secret scan), push (never main, never forced), pull requests, PR comments. No approve/merge command exists |
| `config/config.json` | Azure DevOps org, branch rules, legacy repo, agreed projects |
| `templates/vue3-starter/` | Vue 3 + PrimeVue 4 + Tailwind 4 + Pinia starter already wired for fams-ui-standards (palette, fonts, `apiService.js`, lint rules, budgets, tests) |
| `deploy/install.sh` | Installs into the Paperclip container at `/paperclip/fams-vue-agents` |
| `deploy/workspace/claude-settings.json` | Becomes the agents' `.claude/settings.json` (blocks plain `git push/commit`, `curl`, reading secrets, the Notion connector) |
| `tests/devops.test.mjs` | Offline guard-rail tests (branch rules, pre-push hook, secret scan) |

Nothing in the existing skill folders (FAMS_CORE, FAMS_VUE_CORE, FAMS_TANKS, …) was
changed — other agents depend on them.

---

## 1. Azure DevOps user for the agents (one-off, a human with admin rights)

**A. Identity (Microsoft Entra admin centre)**
1. Users → New user → Create new user: `fams-agents@fams.co.za`, display name *FAMS
   Agents*, long random password. No Microsoft 365 licence needed.
2. Sign in once as that user to complete MFA; store the credentials in the password
   manager.

**B. Azure DevOps organisation `TecmoFams`**
1. Organization settings → Users → Add users → `fams-agents@fams.co.za`, access level
   **Basic**, add to project **Fams24** (and any other project the Vue apps will live in).
2. Project settings → Permissions → New group **FAMS Agents**, member: the new user only.
3. Project settings → Repositories → (each repo the agents may use) → Security → FAMS
   Agents:
   - **Allow**: Read, Contribute, Create branch, Contribute to pull requests
   - **Deny**: Force push (rewrite history and delete branches), Create tag, Bypass
     policies when completing pull requests, Bypass policies when pushing, Delete or
     disable repository, Edit policies, Manage permissions, Remove others' locks, Rename
     repository
   - Note: Azure DevOps gives whoever creates a branch extra rights on *that* branch. For
     the agents that only ever means their own `agents/…` branches, which is fine.

**C. Protect `main` (and `develop` / `release/*` if a repo uses them) in every repo the
agents use** (Repos → Branches → the branch → ⋯)
1. Branch security → FAMS Agents → **Contribute: Deny**.
2. Branch policies: Require a minimum number of reviewers = 1; *Allow requestors to
   approve their own changes* **off**; *Prohibit the most recent pusher from approving
   their own changes* **on**; *Reset all approval votes when there are new changes* **on**.
3. For the `Fams24` repo also: Automatically included reviewers → yourself, **Required**,
   path filter `/FAMS-API/*;/FamsAIFunctions/*;/ScheduledFAMSDecoding/*;/Json Decode Function/*;/CoreViewer/*`
   (DevOps can't limit write access by folder, so this stops an agent change outside the
   UI from merging without you).

**D. Token** (signed in as fams-agents) → User settings → Personal access tokens → New
token: organisation `TecmoFams`, expiry 90 days, scopes *Custom defined* → **Code: Read &
write** only. Don't paste it anywhere except the install prompt in step 2.
If token creation is blocked: Organization settings → Policies (PAT creation may be
restricted by an Entra policy).

Put a calendar reminder 1 week before the token expires; renew with
`sudo bash fams-vue-agents/deploy/install.sh --token`.

## 2. Install on the VM

```bash
cd /data/paperclip/github-skills/FamsFactorySkillFiles && git pull
sudo bash fams-vue-agents/deploy/install.sh --token            # paste the PAT (hidden)
sudo bash fams-vue-agents/deploy/install.sh --verify-template  # optional, ~2 min: npm ci + check of the starter
```

Expect: `git/node/npm` versions (Node ≥ 20.19), `# pass 7` / `# fail 0` from the guard-rail
tests, and the `whoami` JSON showing *FAMS Agents*. `--verify-template` ends with
`budget OK`.

Then in Paperclip: **re-import skills** from the FamsFactorySkillFiles repo so the seven
skills under `FAMS_VUE_AGENTS/` appear: `fams-ui-standards`, `fams-portal-developer`,
`fams-vue-core-specialized`, `fams-tanks-business-specialized`,
`fams-atg-communications-specialized`, `fams-quick-report-specialized`,
`fams-dispensing-specialized`. (If the importer only looks one folder deep and they don't
appear, tell Claude — the folders can be moved up a level without changing the files.
If it rejects `fams-dispensing` because of its `reference/` files, skip it for now; the
agents still read it from `/paperclip/fams-vue-agents/skills/`.)

## 3. Create the five agents in Paperclip

Agents → New Agent, once per row. For all five:

| Field | Value |
|---|---|
| Adapter | **Claude Code** (claude_local), same dedicated subscription as the other agents |
| Model | same Sonnet model as the CEO agent |
| Working directory (cwd) | `/paperclip/fams-vue-agents/workspace` |
| Heartbeat | **off** (they wake on assigned issues) |
| Instructions | the matching block from `agent/PAPERCLIP_INSTRUCTIONS.md` |

| Name | Role | Reports to | Skills to attach |
|---|---|---|---|
| FAMS Vue Lead | general (manager) | FAMS Product Leader | FAMS Core, fams-ui-standards, fams-portal-developer, fams-vue-core-specialized, fams-quick-report-specialized, fams-dispensing-specialized, fams-tanks-business-specialized, fams-atg-communications-specialized |
| FAMS Vue HTML-CSS | engineer | FAMS Vue Lead | FAMS Core, fams-ui-standards, fams-portal-developer, fams-vue-core-specialized, fams-quick-report-specialized |
| FAMS Vue JavaScript | engineer | FAMS Vue Lead | FAMS Core, fams-ui-standards, fams-portal-developer, fams-vue-core-specialized, fams-tanks-business-specialized, fams-dispensing-specialized, fams-quick-report-specialized |
| FAMS Vue Tester | qa | FAMS Vue Lead | FAMS Core, fams-ui-standards, fams-portal-developer, fams-vue-core-specialized |
| FAMS Vue Reviewer | qa | FAMS Vue Lead | FAMS Core, fams-ui-standards, fams-portal-developer, fams-vue-core-specialized, fams-quick-report-specialized, fams-dispensing-specialized, fams-tanks-business-specialized |

Use whatever Paperclip role names exist if these don't; what matters is *Reports to*.

## 4. Supervised first runs (create these issues in order)

**a) Lockdown check — assign to each of the five agents (one issue each):**
> Lockdown check: follow your instructions files. Then run
> `node /paperclip/fams-vue-agents/scripts/devops.mjs whoami` and
> `ls /paperclip/fams-vue-agents/skills`, and try `git push --help` once to confirm
> plain git push is blocked for you. Report: the whoami result, your skill names as you
> see them attached, the skill folders on disk, and whether git push was blocked. Do not
> clone, branch, commit or push anything.

Expected: whoami = FAMS Agents; seven Vue skill folders + `docs`; `git push` denied.

**b) Legacy study — assign to FAMS Vue Lead:**
> Study the legacy FAMS-UI portal (Azure DevOps TecmoFams / Fams24 / Fams24, folder
> FAMS-UI) as described in section 6 of your instructions file. Produce the knowledge
> files (legacy-screens, legacy-api, legacy-auth-session, legacy-components,
> legacy-anti-patterns, INDEX) with file + line evidence, attach them, and list open
> questions. You may split the work into sub-issues for the JavaScript and HTML-CSS
> agents. Read only: no branches, commits or pushes. Never copy any key or token.

Review the knowledge files yourself before the agents rely on them. Good ones can be
committed to this repo later (e.g. `FAMS_VUE_AGENTS/docs/legacy-study/`).

**c) First build — assign to FAMS Vue Lead** (after the study, when you have a repo for
it): a small, real screen, e.g. *"Rebuild the Quick ATG tank-levels grid
(fams-quick-report § 3.5) as a new Vue 3 project in repo <name>"*. The Lead should come
back with questions before writing code — that's expected.

## 5. Day-to-day

- Change instructions, config, template or skills in git → push → on the VM:
  `git pull && sudo bash fams-vue-agents/deploy/install.sh`.
- New agreed project: add it to `config/config.json → projects` (optional; the Lead asks
  anyway).
- Clones live in `/paperclip/fams-vue-agents/workspace/repos` (on the VM:
  `/data/docker/volumes/docker_paperclip-data/_data/fams-vue-agents/workspace/repos`).
  Safe to delete a clone; the next task re-clones it.
- Run the guard-rail tests locally: `node --test fams-vue-agents/tests/*.test.mjs`.
- Run the starter's checks locally: `cd fams-vue-agents/templates/vue3-starter && npm ci --include=dev && npm run check`.

## Known limits

- Five agents share one Claude subscription and one clone per repo, so work runs one task
  at a time. That's deliberate.
- Automated visual (browser) tests need Playwright + a browser in the Paperclip container;
  until that's added, the Tester reports "visual check not automated" and the human
  reviewer looks at the screens.
- `.claude/settings.json` deny rules stop the obvious commands, `devops.mjs` + the
  pre-push hook enforce the branch rules, and the code/config/instructions are root-owned
  so the agents can't edit their own guard rails. But the agents must be able to *use*
  the token, so a determined agent could read it. **The hard wall is the Azure DevOps
  permissions and branch policies in section 1** — set those up before the first build,
  and keep the token at Code (Read & write) only.
