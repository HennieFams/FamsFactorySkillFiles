// fams-ui-standards §4 budgets, checked after `vite build`:
//   initial JS (entry + chunks it imports statically) <= 250 KB gzip
//   any other (lazy) JS chunk <= 150 KB gzip
//   no .vue file under src/ > 500 lines
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { gzipSync } from 'node:zlib';

const ROOT = process.cwd();
const DIST = join(ROOT, 'dist');
const INITIAL_LIMIT = Number(process.env.FAMS_BUDGET_INITIAL_KB || 250) * 1024;
const CHUNK_LIMIT = Number(process.env.FAMS_BUDGET_CHUNK_KB || 150) * 1024;
const MAX_VUE_LINES = 500;

const html = readFileSync(join(DIST, 'index.html'), 'utf8');
const initial = new Set([...html.matchAll(/(?:src|href)="\/?(assets\/[^"]+\.js)"/g)].map((m) => m[1]));
const gz = (p) => gzipSync(readFileSync(join(DIST, p))).length;
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;

const failures = [];
const jsFiles = readdirSync(join(DIST, 'assets')).filter((f) => f.endsWith('.js')).map((f) => `assets/${f}`);
let initialTotal = 0;
for (const f of jsFiles) {
  const size = gz(f);
  if (initial.has(f)) initialTotal += size;
  else if (size > CHUNK_LIMIT) failures.push(`lazy chunk ${f} is ${kb(size)} gzip (limit ${kb(CHUNK_LIMIT)})`);
}
if (initialTotal > INITIAL_LIMIT) failures.push(`initial JS is ${kb(initialTotal)} gzip (limit ${kb(INITIAL_LIMIT)})`);

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (p.endsWith('.vue')) {
      const lines = readFileSync(p, 'utf8').split('\n').length;
      if (lines > MAX_VUE_LINES) failures.push(`${relative(ROOT, p)} has ${lines} lines (limit ${MAX_VUE_LINES})`);
    }
  }
}
walk(join(ROOT, 'src'));

console.log(`initial JS: ${kb(initialTotal)} gzip (${[...initial].join(', ')})`);
if (failures.length) {
  console.error('BUDGET FAILED:\n - ' + failures.join('\n - '));
  process.exit(1);
}
console.log('budget OK');
