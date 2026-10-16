#!/usr/bin/env node
// Write each Vue agent's Paperclip instructions file from agent/PAPERCLIP_INSTRUCTIONS.md
// WITHOUT the Paperclip API (no board token). Same text create-agents.mjs --update-instructions
// writes. Run INSIDE the Paperclip container as the agent user (keeps file ownership):
//   docker exec -u node docker-server-1 node /paperclip/fams-vue-agents/scripts/write-instructions.mjs --dry-run
//   docker exec -u node docker-server-1 node /paperclip/fams-vue-agents/scripts/write-instructions.mjs
// Backups go to /tmp/vue-instr-bak/<agent-id>.<timestamp>.md inside the container.
import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync } from 'node:fs';

const DRY = process.argv.includes('--dry-run');
const HOME = '/paperclip/fams-vue-agents';
const COMPANY = process.env.FAMS_COMPANY_ID || '174397dc-6b10-4a13-a753-884987e288e9';
const ROOT = process.env.PAPERCLIP_INSTANCE_DIR || '/paperclip/instances/default';
// Agent IDs from vue-agents/STATUS.md (created 6 Oct 2026).
const AGENTS = {
  'FAMS Vue Lead': '0ba0a560-9d40-4a1e-8cc3-6a7ea83a96b1',
  'FAMS Vue HTML-CSS': '5cb30fde-bb9e-4ec0-bbe8-0d262de9553f',
  'FAMS Vue JavaScript': '377bd1db-bf45-4d52-9493-ca963c81e815',
  'FAMS Vue Tester': '4e802b71-515e-46da-8506-9f3c7ae9da1b',
  'FAMS Vue Reviewer': '05aa6915-bbd6-4d43-8bbe-d0d0798d5016',
};

const md = readFileSync(`${HOME}/agent/PAPERCLIP_INSTRUCTIONS.md`, 'utf8');
function instructionsFor(name) {
  const i = md.indexOf(`## ${name}\n`);
  if (i < 0) throw new Error(`no instructions block for ${name}`);
  const m = md.slice(i).match(/```\n([\s\S]*?)\n```/);
  if (!m) throw new Error(`no code block for ${name}`);
  return m[1] + '\n';
}

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
let failed = 0;
for (const [name, id] of Object.entries(AGENTS)) {
  const f = `${ROOT}/companies/${COMPANY}/agents/${id}/instructions/AGENTS.md`;
  if (!existsSync(f)) { console.log(`!! ${name}: ${f} not found - paste its block in the Paperclip UI`); failed++; continue; }
  const oldText = readFileSync(f, 'utf8');
  const newText = instructionsFor(name);
  if (oldText === newText) { console.log(`= ${name}: already up to date`); continue; }
  const a = oldText.split('\n'), b = newText.split('\n');
  const changed = Math.max(a.length, b.length) - a.filter((l, k) => l === b[k]).length;
  if (DRY) { console.log(`~ ${name}: would rewrite ${f} (${changed} line(s) differ)`); continue; }
  mkdirSync('/tmp/vue-instr-bak', { recursive: true });
  copyFileSync(f, `/tmp/vue-instr-bak/${id}.${stamp}.md`);
  writeFileSync(f, newText);
  console.log(`~ ${name}: rewritten (${changed} line(s) changed; backup /tmp/vue-instr-bak/${id}.${stamp}.md)`);
}
process.exit(failed ? 1 : 0);
