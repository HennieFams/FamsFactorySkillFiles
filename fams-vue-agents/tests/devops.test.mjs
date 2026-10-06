// node --test tests/   (offline; uses a local bare repo, no Azure DevOps)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, '..', 'scripts', 'devops.mjs');
process.env.FAMS_VUE_TEST = '1';
const { branchProblem, prePushProblems, repoUrl, isProtected, parseArgs, bodyPathProblem, parseOrigin, monthFolder, repoAllowed, pathProblems, writeTarget } = await import(SCRIPT);

test('branch names: only the agents\' own feature/bugfix branches', () => {
  assert.equal(branchProblem('agents_features/tec-12-tank-card'), null);
  assert.equal(branchProblem('agents_bugfixes/oct2026/tec-13-grid-totals'), null);
  assert.equal(branchProblem('agents_bugfixes/sept2026/tec-14'), null);
  for (const bad of ['master', 'master_dev', 'main', 'development', 'develop', 'release/1.2', 'hotfix/x',
    'feature/x', 'bugfixes/oct2026', 'hennie_features/x', 'Hennie_feature/x', 'agents/x', 'agents_features/',
    'agents_features/Tank', 'agents_features/a/b', 'agents_features/a..b', 'agents_features/x.lock',
    'agents_bugfixes/x', 'agents_bugfixes/october2026/x', 'agents_bugfixes/oct26/x', 'agents_features/ space']) {
    assert.ok(branchProblem(bad), `should reject ${bad}`);
  }
  assert.ok(isProtected('release/2026-10'));
  assert.equal(monthFolder(new Date(2026, 8, 1)), 'sept2026');
  assert.equal(monthFolder(new Date(2026, 9, 6)), 'oct2026');
});

test('pre-push: blocks protected, non-agent, deletes and tags', () => {
  const z = '0'.repeat(40); const s = 'a'.repeat(40);
  assert.deepEqual(prePushProblems(`refs/heads/agents_features/1-x ${s} refs/heads/agents_features/1-x ${z}\n`), []);
  assert.ok(prePushProblems(`refs/heads/x ${s} refs/heads/development ${z}`).length);
  assert.ok(prePushProblems(`refs/heads/x ${s} refs/heads/feature/y ${z}`).length);
  assert.ok(prePushProblems(`(delete) ${z} refs/heads/agents_features/1-x ${s}`).length);
  assert.ok(prePushProblems(`refs/tags/v1 ${s} refs/tags/v1 ${z}`).length);
  // non-fast-forward to an existing agent branch = force push
  const b = 'b'.repeat(40);
  assert.ok(prePushProblems(`refs/heads/agents_features/1-x ${s} refs/heads/agents_features/1-x ${b}`, undefined, () => false).length);
  assert.deepEqual(prePushProblems(`refs/heads/agents_features/1-x ${s} refs/heads/agents_features/1-x ${b}`, undefined, () => true), []);
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

test('Fams24 is readable but read-only; nothing is writable until Hennie adds a write target', () => {
  assert.ok(repoAllowed('Fams24', 'Fams24'));
  assert.equal(writeTarget('Fams24', 'Fams24'), null);
  for (const [p, r] of [['Fams24', 'Fams24.zinet.oosthuizen'], ['Fams24MobileVue', 'Fams24MobileVue'], ['Fams25NewApp', 'Fams25NewApp'], ['fams24', 'fams24']]) {
    assert.ok(!repoAllowed(p, r), `${p}/${r} must not be allowed`);
  }
  const cfg = { write_targets: { list: [
    { project: 'P', repo: 'R', paths: ['portal/'] },
    { project: 'P', repo: 'Bad1', paths: [] },
    { project: 'P', repo: 'Bad2', paths: ['../x/'] },
    { project: 'P', repo: 'Bad3', paths: ['no-slash'] }
  ] } };
  assert.deepEqual(writeTarget('P', 'R', cfg).paths, ['portal/']);
  for (const r of ['Bad1', 'Bad2', 'Bad3', 'Other']) assert.equal(writeTarget('P', r, cfg), null);
});

test('only files under the write target folder may change', () => {
  const W = ['FAMS-UI/'];
  assert.deepEqual(pathProblems(['FAMS-UI/src/main.js', 'FAMS-UI/package.json'], W), []);
  assert.deepEqual(pathProblems(['FAMS-API/Controllers/X.cs', 'azure-pipelines.yml', 'FAMS-UIx/a', 'docs/a.md'], W),
    ['FAMS-API/Controllers/X.cs', 'azure-pipelines.yml', 'FAMS-UIx/a', 'docs/a.md']);
});

test('repo URL is built without credentials', () => {
  const u = repoUrl('Fams24', 'FAMS Portal');
  assert.equal(u, 'https://dev.azure.com/TecmoFams/Fams24/_git/FAMS%20Portal');
  assert.ok(!u.includes('@'));
});

test('arg parsing', () => {
  assert.deepEqual(parseArgs(['pr-create', '--repo', 'R', '--draft', '--title', 'T']), { _: ['pr-create'], repo: 'R', draft: true, title: 'T' });
});

test('end-to-end against a local bare repo: agent branch from development pushes, master/development blocked', () => {
  const tmp = mkdtempSync(join(tmpdir(), 'fva-'));
  const run = (cmd, args, cwd, env = {}) => spawnSync(cmd, args, { cwd, encoding: 'utf8', env: { ...process.env, ...env } });
  const bare = join(tmp, 'remote.git');
  run('git', ['init', '--bare', '-b', 'master', bare], tmp);  // Fams24's default branch is master
  const seed = join(tmp, 'seed');
  run('git', ['clone', bare, seed], tmp);
  writeFileSync(join(seed, 'README.md'), 'x\n');
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'init', '--allow-empty'], seed);
  run('git', ['add', '.'], seed);
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'readme'], seed);
  run('git', ['push', '-q', 'origin', 'master'], seed);
  run('git', ['checkout', '-q', '-b', 'development'], seed);
  writeFileSync(join(seed, 'dev.txt'), 'dev only\n');
  run('git', ['add', '.'], seed);
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'dev'], seed);
  run('git', ['push', '-q', 'origin', 'development'], seed);

  const ws = join(tmp, 'ws'); mkdirSync(join(ws, 'repos'), { recursive: true });
  const tokenFile = join(tmp, 'pat'); writeFileSync(tokenFile, 'dummy');
  const env = { FAMS_VUE_TEST: '1', FAMS_VUE_WORKSPACE: ws, FAMS_DEVOPS_TOKEN_FILE: tokenFile };
  const repo = join(ws, 'repos', 'demo');
  run('git', ['clone', '-q', bare, repo], tmp);

  let r = run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'agents_features/1-demo'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(existsSync(join(repo, 'dev.txt')), 'agent branch must start from development, not master');
  // --from anything else is refused
  assert.notEqual(run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'agents_features/2-x', '--from', 'master'], tmp, env).status, 0);
  mkdirSync(join(repo, 'FAMS-UI'), { recursive: true });
  writeFileSync(join(repo, 'FAMS-UI', 'a.txt'), 'hello\n');
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', '[vue-js] add a', '--all'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  r = run('node', [SCRIPT, 'push', '--repo', 'demo'], tmp, env);
  assert.equal(r.status, 0, r.stderr);
  assert.match(run('git', ['branch', '--list', 'agents_features/1-demo'], bare).stdout, /agents_features\/1-demo/);

  // a direct `git push` to master or development is stopped by the installed hook
  for (const target of ['master', 'development']) {
    r = run('git', ['push', 'origin', `HEAD:refs/heads/${target}`], repo, env);
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /protected/);
  }

  // re-running `branch` for an existing local branch keeps its commits
  const before = run('git', ['rev-parse', 'HEAD'], repo).stdout.trim();
  assert.equal(run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'agents_features/1-demo'], tmp, env).status, 0);
  assert.equal(run('git', ['rev-parse', 'HEAD'], repo).stdout.trim(), before);

  // a force push (rewritten history) to the agent branch is blocked by the hook
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--amend', '-m', 'rewritten'], repo);
  r = run('git', ['push', '--force', 'origin', 'HEAD:refs/heads/agents_features/1-demo'], repo, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /non-fast-forward/);
  run('git', ['reset', '-q', '--hard', 'origin/agents_features/1-demo'], repo);

  // missing flag values give a clean error, not a stack trace
  r = run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /--name <value> is required/);

  // the script refuses to branch/commit outside the agent branches
  assert.notEqual(run('node', [SCRIPT, 'branch', '--repo', 'demo', '--name', 'main'], tmp, env).status, 0);
  run('git', ['checkout', '-q', 'master'], repo);
  assert.notEqual(run('node', [SCRIPT, 'push', '--repo', 'demo'], tmp, env).status, 0);

  // secrets are refused at commit time
  run('git', ['checkout', '-q', 'agents_features/1-demo'], repo);
  const fakeKey = ['AI', 'za', 'Sy', 'D0123456789abcdefghijklmnopqrstu'].join(''); // built at runtime so this file holds no key-shaped literal
  writeFileSync(join(repo, 'FAMS-UI', 'b.js'), `const k = { key: '${fakeKey}' };\n`);
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', 'x', '--all'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /secret/);

  // ... including the access token itself
  writeFileSync(join(repo, 'FAMS-UI', 'b.js'), "const t = 'dummy-token-value-123';\n");
  writeFileSync(tokenFile, 'dummy-token-value-123');
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', 'x', '--all'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.doesNotMatch(r.stderr, /dummy-token-value-123/);
  run('git', ['checkout', '-q', '--', '.'], repo);
  run('git', ['clean', '-qfd'], repo);
  writeFileSync(tokenFile, 'dummy');

  // FAMS-API (and anything outside FAMS-UI/) can't be committed through the script ...
  mkdirSync(join(repo, 'FAMS-API'), { recursive: true });
  writeFileSync(join(repo, 'FAMS-API', 'Api.cs'), '// change\n');
  r = run('node', [SCRIPT, 'commit', '--repo', 'demo', '--message', 'x', '--all'], tmp, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /only change files under FAMS-UI\//);
  // ... and if committed with plain git anyway, the pre-push hook stops it
  run('git', ['add', '--all'], repo);
  run('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'sneaky api change'], repo);
  r = run('git', ['push', 'origin', 'HEAD:refs/heads/agents_features/1-demo'], repo, env);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /changes outside FAMS-UI\//);
});
