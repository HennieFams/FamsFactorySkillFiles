#!/usr/bin/env node
// Create the five FAMS Vue Agents in Paperclip through its API (no UI wizard).
// Run INSIDE the Paperclip container with the board token (never printed):
//   node create-agents.mjs --dry-run     # show what would be created
//   node create-agents.mjs               # create (skips agents that already exist by name)
// Env: PAPERCLIP_BOARD_TOKEN (required), FAMS_COMPANY_ID, FAMS_CEO_AGENT_ID,
//      PAPERCLIP_API (default http://localhost:3100/api)
// Template = the working Database Integrity Agent: claude_local, claude-sonnet-5,
// heartbeat off, dangerouslyBypassApprovalsAndSandbox, Claude login = the stored
// subscription login of the token's user (applyStoredClaudeLogin).
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const API = process.env.PAPERCLIP_API || 'http://localhost:3100/api';
const TOKEN = process.env.PAPERCLIP_BOARD_TOKEN;
const COMPANY = process.env.FAMS_COMPANY_ID || '174397dc-6b10-4a13-a753-884987e288e9';
const CEO = process.env.FAMS_CEO_AGENT_ID || '99bf123e-fb72-482f-b627-263b33c24ae7';
const DRY = process.argv.includes('--dry-run');
const HOME = '/paperclip/fams-vue-agents';
const WORKSPACE = `${HOME}/workspace`;
const MODEL = process.env.FAMS_VUE_MODEL || 'claude-sonnet-5';
if (!TOKEN) { console.error('PAPERCLIP_BOARD_TOKEN missing'); process.exit(2); }

const S = (slug) => `henniefams/famsfactoryskillfiles/${slug}`;
const BASE = ['paperclipai/paperclip/paperclip', S('fams-core'), S('fams-ui-standards'), S('fams-portal-developer'), S('fams-vue-core-specialized')];
const AGENTS = [
  { key: 'lead', name: 'FAMS Vue Lead', title: 'Lead — plans UI work, hands out tasks, owns branch + PR', reportsTo: 'CEO',
    skills: [...BASE, S('fams-quick-report-specialized'), S('fams-dispensing-specialized'), S('fams-tanks-business-specialized'), S('fams-atg-communications-specialized')] },
  { key: 'html-css', name: 'FAMS Vue HTML-CSS', title: 'Templates, PrimeVue, Tailwind, palette, light/dark, responsive', reportsTo: 'LEAD',
    skills: [...BASE, S('fams-quick-report-specialized')] },
  { key: 'javascript', name: 'FAMS Vue JavaScript', title: 'apiService, thin services, composables, Pinia, router, speed', reportsTo: 'LEAD',
    skills: [...BASE, S('fams-tanks-business-specialized'), S('fams-dispensing-specialized'), S('fams-quick-report-specialized')] },
  { key: 'tester', name: 'FAMS Vue Tester', title: 'Tests, lint, build, speed budgets — PASS/FAIL with evidence', reportsTo: 'LEAD',
    skills: [...BASE] },
  { key: 'reviewer', name: 'FAMS Vue Reviewer', title: 'Independent review against the skills — APPROVE/CHANGES', reportsTo: 'LEAD',
    skills: [...BASE, S('fams-quick-report-specialized'), S('fams-dispensing-specialized'), S('fams-tanks-business-specialized')] }
];

// Paste blocks from agent/PAPERCLIP_INSTRUCTIONS.md (## <name> followed by a ``` block)
const md = readFileSync(`${HOME}/agent/PAPERCLIP_INSTRUCTIONS.md`, 'utf8');
function instructionsFor(name) {
  const i = md.indexOf(`## ${name}\n`);
  if (i < 0) throw new Error(`no instructions block for ${name}`);
  const m = md.slice(i).match(/```\n([\s\S]*?)\n```/);
  if (!m) throw new Error(`no code block for ${name}`);
  return m[1] + '\n';
}

async function api(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const t = await r.text();
  let j; try { j = t ? JSON.parse(t) : {}; } catch { j = { raw: t.slice(0, 300) }; }
  if (!r.ok) { const e = new Error(`${method} ${path} -> HTTP ${r.status}: ${t.slice(0, 500)}`); e.status = r.status; throw e; }
  return j;
}

const list = await api('GET', `/companies/${COMPANY}/agents`);
const existing = new Map((Array.isArray(list) ? list : list.agents || list.items || []).map((a) => [a.name, a]));
console.log(`company ${COMPANY}: ${existing.size} agents; CEO ${existing.has('FAMS Product Leader') ? 'found' : '(by id)'}`);

// Which skill keys does the company have? (best effort - endpoint name may differ)
let known = null;
for (const p of [`/companies/${COMPANY}/skills`, `/companies/${COMPANY}/company-skills`]) {
  try {
    const s = await api('GET', p);
    const arr = Array.isArray(s) ? s : s.skills || s.items || [];
    known = new Set(arr.flatMap((x) => [x.key, x.slug, x.id, x.ref, x.name].filter(Boolean)));
    break;
  } catch { /* try next */ }
}
if (known) {
  const missing = [...new Set(AGENTS.flatMap((a) => a.skills))].filter((k) => !known.has(k) && !known.has(k.split('/').pop()));
  console.log(missing.length ? `WARNING skill keys not found in company list: ${missing.join(', ')}` : 'all skill keys found');
} else console.log('(could not list company skills - keys not pre-checked)');

let leadId = existing.get('FAMS Vue Lead')?.id || null;
for (const a of AGENTS) {
  if (existing.has(a.name)) { console.log(`= ${a.name} already exists (${existing.get(a.name).id}) - skipped`); continue; }
  const reportsTo = a.reportsTo === 'CEO' ? CEO : leadId;
  const body = {
    name: a.name,
    role: 'general',
    title: a.title,
    reportsTo,
    adapterType: 'claude_local',
    adapterConfig: {
      model: MODEL,
      cwd: WORKSPACE,
      dangerouslyBypassApprovalsAndSandbox: true,
      paperclipSkillSync: { desiredSkills: a.skills }
    },
    desiredSkills: a.skills,
    runtimeConfig: { heartbeat: { enabled: false, maxConcurrentRuns: 1 } },
    applyStoredClaudeLogin: true
  };
  if (DRY) { console.log(`\n--- would create ${a.name}:\n${JSON.stringify({ ...body, reportsTo: reportsTo || '<FAMS Vue Lead id>' }, null, 2)}`); continue; }
  const created = await api('POST', `/companies/${COMPANY}/agents`, body);
  console.log(`+ created ${a.name}: ${created.id}`);
  if (a.key === 'lead') leadId = created.id;
  // instructions: overwrite the managed AGENTS.md with our short block (it cats the files on disk)
  const f = created.adapterConfig?.instructionsFilePath;
  if (f && existsSync(f)) { writeFileSync(f, instructionsFor(a.name)); console.log(`  instructions written: ${f}`); }
  else console.log(`  !! no instructions file at ${f} - paste the ${a.name} block from PAPERCLIP_INSTRUCTIONS.md in the UI`);
}
console.log(DRY ? '\nDry run only - nothing created.' : '\nDone.');
