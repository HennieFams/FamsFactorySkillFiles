// node --test tests/   (offline; uses a local bare repo, no Azure DevOps)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, '..', 'scripts', 'devops.mjs');
process.env.FAMS_VUE_TEST = '1';
const { branchProblem, prePushProblems, repoUrl, isProtected, parseArgs, bodyPathProblem, parseOrigin } = await import(SCRIPT);

test('branch names: only agents/<issue>-<slug>', () => {
  assert.equal(branchProblem('agents/tec-12-tank-card'), null);
  assert.equal(branchProblem('agents/tec-12/html'), null);
  for (const bad of ['main', 'master', 'develop', 'release/1.2', 'hotfix/x', 'feature/x', 'agents/', 'agents/Tank', 'agents/a..b', 'agents/x.lock', 'agents/ space']) {
    assert.ok(branchProblem(bad), `should reject ${bad}`);
  }
  assert.ok(isProtected('release/2026-10'));
});

test('pre-push: blocks protected, non-agent, deletes and tags', () => {
  const z = '0'.repeat(40); const s = 'a'.repeat(40);
  assert.deepEqual(prePushProblems(`refs/heads/agents/1-x ${s} refs/heads/agents/1-x ${z}\n`), []);
  assert.ok(prePushProblems(`refs/heads/x ${s} refs/heads/main ${z}`).length);
  assert.ok(prePushProblems(`refs/heads/x ${s} refs/heads/feature/y ${z}`).length);
  assert.ok(prePushProblems(`(delete) ${z} refs/heads/agents/1-x ${s}`).length);
  assert.ok(prePushProblems(`refs/tags/v1 ${s} refs/tags/v1 ${z}`).length);
  // non-fast-forward to an existing agents/ branch = force push
  const b = 'b'.repeat(40);
  assert.ok(prePushProblems(`refs/heads/agents/1-x ${s} refs/heads/agents/1-x ${b}`, undefined, () => false).length);
  assert.deepEqual(prePushProblems(`refs/heads/agents/1-x ${s} refs/heads/agents/1-x ${b}`, undefined, () => true), []);
});

test('body files: workspace only, never secrets', () => {
  assert.equal(bodyPathProblem('pr.md', '/ws', '/home/secrets/devops.pat', '/ws'), null);
  assert.equal(bodyPathProblem('review.md', '/ws', '/x', '/ws/repos/demo'), null);
  assert.ok(bodyPathProblem('/etc/passwd', '/ws', '/x', '/ws'));
  const W = '/paperclip/fams-vue-agents/workspace';
  assert.ok(bodyPathProblem('../secrets/devops.pat', W, '/paperclip/fams-vue-agents/secrets/devops.pat', W));
  assert.ok(bodyPathProblem('a/secrets/x.md', '/ws', '/x', '/ws'));
  assert.ok(bodyPathProblem(true, '/ws', '/x', '/ws'));
});

test('origin parsing only accepts the configured org', () => {
  assert.deepEqual(parseOrigin('https://dev.azure.com/TecmoFams/Fams24/_git/FAMS%20Portal'), { project: 'Fams24', repo: 'FAMS Portal' });
  assert.equal(parseOrigin('https://evil.example/TecmoFams/Fams24/_git/x'), null);
});

test('repo URL is built without credentials', () => {
  const u = repoUrl('Fams24', 'FAMS Portal');
  assert.equal(u, 'https://dev.azure.com/TecmoFams/Fams24/_git/FAMS%20Portal');
  assert.ok(!u.includes('@'));
});

test('arg parsing', () => {
  assert.deepEqual(parseArgs(['pr-create', '--repo', 'R', '--draft', '--title', 'T']), { _: ['pr-create'], repo: 'R', draft: true, title: 'T' });
});

test('end-to-end against a local bare repo: agents/ branch pushes, main is blocked', () => {
  const tmp = mkdtempSync(join(tmpdir(), 'fva-'));
  const run = (cmd, args, cwd, env = {}) => spawnSync(cmd, args, { cwd, encoding: 'utf8', env: { ...process.env, ...env } });
  const bare = join(tmp, 'remote.git');
  run('git', ['init', '--bare', '-b', 'main', bare], tmp);
  const seed = join(tmp, 'seed');
  run('git', ['clone', bare, seed], tmp);
  writeFileSync(join(seed, 'README.md'), 'x\n');
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'init', '--allow-empty'], seed);
  run('git', ['add', '.'], seed);
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'readme'], seed);
  run('git', ['push', '-q', 'origin', 'main'], seed);

  const ws = join(tmp, 'ws'); mkdirSync(join(ws, 'repos'), { recursive: true });
  const tokenFile = join(tmp, 'pat'); writeFileSync(tokenFile, 'dummy');
  const env = { FAMS_VUE_TEST: '1', FAMS_VUE_WORKSPACE: ws, FAMS_DEVOPS_TOKEN_FILE: tokenFile };
  const repo = join(ws, 'repos', 'demo');
  run('git', ['clone', '-q', bare, repo], tmp);

  let r = run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'agents/1-demo'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  writeFileSync(join(repo, 'a.txt'), 'hello\n');
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', '[vue-js] add a', '--all'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  r = run('node', [SCRIPT, 'push', '--repo', 'demo'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  assert.match(run('git', ['branch', '--list', 'agents/1-demo'], bare).stdout, /agents\/1-demo/);

  // a direct `git push` to main from the clone is stopped by the installed hook
  r = run('git', ['push', 'origin', 'HEAD:refs/heads/main'], repo, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /protected branch/);

  // re-running `branch` for an existing local branch keeps its commits
  const before = run('git', ['rev-parse', 'HEAD'], repo).stdout.trim();
  assert.equal(run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'agents/1-demo'], tmp, env).status, 0);
  assert.equal(run('git', ['rev-parse', 'HEAD'], repo).stdout.trim(), before);

  // a force push (rewritten history) to the agents/ branch is blocked by the hook
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--amend', '-m', 'rewritten'], repo);
  r = run('git', ['push', '--force', 'origin', 'HEAD:refs/heads/agents/1-demo'], repo, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /non-fast-forward/);
  run('git', ['reset', '-q', '--hard', 'origin/agents/1-demo'], repo);

  // missing flag values give a clean error, not a stack trace
  r = run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /--name <value> is required/);

  // the script refuses to branch/commit outside agents/
  assert.notEqual(run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'main'], tmp, env).status, 0);
  run('git', ['checkout', '-q', 'main'], repo);
  assert.notEqual(run('node', [SCRIPT, 'push', '--repo', 'demo'], tmp, env).status, 0);

  // secrets are refused at commit time
  run('git', ['checkout', '-q', 'agents/1-demo'], repo);
  const fakeKey = ['AI', 'za', 'Sy', 'D0123456789abcdefghijklmnopqrstu'].join(''); // built at runtime so this file holds no key-shaped literal
  writeFileSync(join(repo, 'b.js'), `const k = { key: '${fakeKey}' };\n`);
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', 'x', '--all'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /secret/);

  // ... including the access token itself
  writeFileSync(join(repo, 'b.js'), "const t = 'dummy-token-value-123';\n");
  writeFileSync(tokenFile, 'dummy-token-value-123');
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', 'x', '--all'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.doesNotMatch(r.stderr, /dummy-token-value-123/);
});
