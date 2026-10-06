#!/usr/bin/env node
// FAMS Vue Agents - the ONLY way the Vue agents touch Azure DevOps (fams-ui-standards §6).
//
//   node devops.mjs whoami                                   token check (who am I, which org)
//   node devops.mjs projects                                 list projects the agent user can see
//   node devops.mjs repos [--project P]                      list repos
//   node devops.mjs clone --project P --repo R               clone or update into workspace/repos/R
//   node devops.mjs branch --repo R --name agents_features/<issue>-<slug>             (new feature, from development)
//   node devops.mjs branch --repo R --name agents_bugfixes/<mon><yyyy>/<issue>-<slug> (bug fix, from development)
//   node devops.mjs commit --repo R --message "..." [--all]  commit staged (or all) changes on an agent branch
//   node devops.mjs push --repo R                            push the current agent branch (never forced)
//   node devops.mjs pr-create --repo R --title "..." --body-file F [--draft]   (always into development)
//   node devops.mjs pr-status --repo R --id N                status, reviewer votes, policy results
//   node devops.mjs pr-comments --repo R --id N              read review threads
//   node devops.mjs pr-comment --repo R --id N --body-file F post a comment thread (reviewer findings)
//
// Guard rails, enforced here and in a pre-push hook installed in every clone:
//   - only the agents' own branches (agents_features/..., agents_bugfixes/<mon><yyyy>/...)
//     can be created, committed on or pushed; they always start from development;
//   - protected branches (config git.protected_branches) are never pushed; no force
//     (non-fast-forward) pushes, no deletes, no tags;
//   - no command approves, completes, abandons or merges a pull request;
//   - the token is read from a file by a root-owned askpass script, never printed, never
//     written into .git/config, a remote URL, a commit, a PR or a comment.
// These are seat belts. The real wall is the Azure DevOps permissions + branch policies
// (README section 1).
import { readFileSync, existsSync, mkdirSync, writeFileSync, chmodSync, realpathSync } from 'node:fs';
import { join, dirname, resolve, sep } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
// Environment overrides exist only for the offline tests.
const TEST = process.env.FAMS_VUE_TEST === '1';
const HOME = resolve(HERE, '..');
const CONFIG = JSON.parse(readFileSync(join(HOME, 'config', 'config.json'), 'utf8'));
const TOKEN_FILE = (TEST && process.env.FAMS_DEVOPS_TOKEN_FILE) || CONFIG.devops.token_file;
const WORKSPACE = (TEST && process.env.FAMS_VUE_WORKSPACE) || CONFIG.workspace;

class DevopsError extends Error {}
function fail(msg) { throw new DevopsError(msg); }

// ---------- pure helpers (unit-tested in tests/devops.test.mjs) ----------

export function globToRegex(glob) {
  return new RegExp('^' + glob.split('*').map((s) => s.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('.*') + '$');
}

export function isProtected(branch, cfg = CONFIG) {
  return cfg.git.protected_branches.some((g) => globToRegex(g).test(branch));
}

const SLUG = '[a-z0-9][a-z0-9._-]*';
const MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sept|oct|nov|dec';
const BRANCH_RE = new RegExp(`^(agents_features/${SLUG}|agents_bugfixes/(${MONTHS})20\\d{2}/${SLUG})$`);

/** e.g. 2026-10-06 -> "oct2026" (the team writes September as "sept"). */
export function monthFolder(date = new Date()) {
  return MONTHS.split('|')[date.getMonth()] + date.getFullYear();
}

/** Returns null if the branch may be created/pushed by an agent, else the reason. */
export function branchProblem(branch, cfg = CONFIG) {
  if (typeof branch !== 'string' || !branch) return 'no branch name';
  if (BRANCH_RE.test(branch) && !branch.includes('..') && !branch.endsWith('.lock')) return null;
  if (isProtected(branch, cfg)) return `"${branch}" is a protected/team branch - agents only push agents_features/... or agents_bugfixes/...`;
  return `branch must be agents_features/<issue>-<slug> or agents_bugfixes/${monthFolder()}/<issue>-<slug> (lowercase letters, digits, . _ -)`;
}

const ZERO = /^0+$/;

/**
 * Checks the lines git gives a pre-push hook: "<local ref> <local sha> <remote ref> <remote sha>".
 * isAncestor(remoteSha, localSha) -> boolean is injected so this stays testable.
 */
export function prePushProblems(stdinText, cfg = CONFIG, isAncestor = () => true) {
  const problems = [];
  for (const line of stdinText.split('\n').map((l) => l.trim()).filter(Boolean)) {
    const [localRef, localSha, remoteRef, remoteSha] = line.split(/\s+/);
    if (ZERO.test(localSha || '')) { problems.push(`deleting ${remoteRef} is not allowed`); continue; }
    if ((localRef || '').startsWith('refs/tags/') || (remoteRef || '').startsWith('refs/tags/')) { problems.push('pushing tags is not allowed'); continue; }
    if (!remoteRef?.startsWith('refs/heads/')) { problems.push(`only branch pushes are allowed (${remoteRef})`); continue; }
    const p = branchProblem(remoteRef.slice('refs/heads/'.length), cfg);
    if (p) { problems.push(p); continue; }
    if (remoteSha && !ZERO.test(remoteSha) && !isAncestor(remoteSha, localSha)) {
      problems.push(`non-fast-forward (force) push to ${remoteRef} is not allowed`);
    }
  }
  return problems;
}

/** Files not under any of the allowed folder prefixes. Returns the offending paths. */
export function pathProblems(files, paths) {
  return files.filter((f) => f && !paths.some((p) => p && f.startsWith(p)));
}

const same = (r, project, repo) => r.project === project && r.repo === repo;

/** May the agents clone/read this repo? (read_repos + write_targets) */
export function repoAllowed(project, repo, cfg = CONFIG) {
  return [...(cfg.read_repos?.list || []), ...(cfg.write_targets?.list || [])].some((r) => same(r, project, repo));
}

/** The write target for this repo (agents may only change its listed folders), or null = read-only. */
export function writeTarget(project, repo, cfg = CONFIG) {
  const t = (cfg.write_targets?.list || []).find((r) => same(r, project, repo));
  return t && Array.isArray(t.paths) && t.paths.length && t.paths.every((p) => typeof p === 'string' && p.endsWith('/') && !p.startsWith('/') && !p.includes('..')) ? t : null;
}

export function repoUrl(project, repo, cfg = CONFIG) {
  const enc = (s) => encodeURIComponent(s);
  return `${cfg.devops.base_url}/${enc(cfg.devops.organization)}/${enc(project)}/_git/${enc(repo)}`;
}

export function prWebUrl(project, repo, id, cfg = CONFIG) {
  return `${repoUrl(project, repo, cfg)}/pullrequest/${id}`;
}

/** origin URL of a clone -> { project, repo } (only URLs of the configured org). */
export function parseOrigin(url, cfg = CONFIG) {
  const base = `${cfg.devops.base_url}/${encodeURIComponent(cfg.devops.organization)}/`;
  if (!url.startsWith(base)) return null;
  const m = url.slice(base.length).match(/^([^/]+)\/_git\/([^/]+)$/);
  return m ? { project: decodeURIComponent(m[1]), repo: decodeURIComponent(m[2]) } : null;
}

export function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) out[key] = true;
      else { out[key] = next; i++; }
    } else out._.push(a);
  }
  return out;
}

/** A path the agent may read a PR/comment body from: inside the workspace, not a secret. */
export function bodyPathProblem(path, workspace = WORKSPACE, tokenFile = TOKEN_FILE, cwd = process.cwd()) {
  if (typeof path !== 'string' || !path) return '--body-file is required';
  const abs = resolve(cwd, path);
  if (!(abs + sep).startsWith(resolve(workspace) + sep)) return `--body-file must be inside ${workspace}`;
  if (abs === resolve(tokenFile) || abs.includes(`${sep}secrets${sep}`)) return '--body-file may not point at secrets';
  return null;
}

// ---------- side-effecting helpers ----------

function str(args, key, required = true) {
  const v = args[key];
  if (v === undefined || v === true || v === '') {
    if (required) fail(`--${key} <value> is required`);
    return undefined;
  }
  return String(v);
}

function token() {
  if (!existsSync(TOKEN_FILE)) fail(`token file not found - a human must run deploy/install.sh --token on the VM`);
  const t = readFileSync(TOKEN_FILE, 'utf8').trim();
  if (!t) fail('token file is empty');
  return t;
}

function repoDir(repo) {
  if (typeof repo !== 'string' || !repo || /[\\/]|^\.|\.\./.test(repo)) fail('--repo must be a plain repository name');
  return join(WORKSPACE, 'repos', repo);
}

function askpassPath() {
  if (!TEST) return join(HOME, 'scripts', 'git-askpass.sh'); // root-owned, installed by install.sh
  const p = join(WORKSPACE, '.git-askpass-test.sh');
  writeFileSync(p, `#!/bin/sh\ncase "$1" in Username*) echo test ;; *) cat "${TOKEN_FILE}" ;; esac\n`);
  chmodSync(p, 0o700);
  return p;
}

function git(args, { cwd, allowFail = false, quiet = false, input } = {}) {
  const env = {
    ...process.env,
    GIT_ASKPASS: askpassPath(),
    GIT_TERMINAL_PROMPT: '0',
    GIT_AUTHOR_NAME: CONFIG.git.author_name,
    GIT_AUTHOR_EMAIL: CONFIG.git.author_email,
    GIT_COMMITTER_NAME: CONFIG.git.author_name,
    GIT_COMMITTER_EMAIL: CONFIG.git.author_email
  };
  // never let a credential helper store the token on disk
  const r = spawnSync('git', ['-c', 'credential.helper=', '-c', `credential.username=${CONFIG.devops.git_username}`, ...args], { cwd, env, encoding: 'utf8', input });
  if (!quiet && r.stdout) process.stdout.write(r.stdout);
  if (r.status !== 0 && !allowFail) {
    process.stderr.write(r.stderr || '');
    fail(`git ${args[0]} failed`);
  }
  return r;
}

function currentBranch(cwd) {
  return git(['rev-parse', '--abbrev-ref', 'HEAD'], { cwd, quiet: true }).stdout.trim();
}

export function installPrePushHook(cwd) {
  const hook = join(cwd, '.git', 'hooks', 'pre-push');
  const testEnv = TEST ? `FAMS_VUE_TEST=1 FAMS_VUE_WORKSPACE="${WORKSPACE}" FAMS_DEVOPS_TOKEN_FILE="${TOKEN_FILE}" ` : '';
  const body = `#!/bin/sh\n# Installed by fams-vue-agents/scripts/devops.mjs - blocks pushes outside the agents' own branches, force pushes, deletes and tags\n${testEnv}exec node "${join(HOME, 'scripts', 'devops.mjs')}" hook-pre-push\n`;
  writeFileSync(hook, body);
  chmodSync(hook, 0o755);
}

async function api(path, { method = 'GET', body, project, apiVersion = CONFIG.devops.api_version } = {}) {
  const org = encodeURIComponent(CONFIG.devops.organization);
  const scope = project ? `/${encodeURIComponent(project)}` : '';
  const q = path.includes('?') ? '&' : '?';
  const url = `${CONFIG.devops.base_url}/${org}${scope}/_apis/${path}${q}api-version=${apiVersion}`;
  const res = await fetch(url, {
    method,
    headers: {
      Authorization: 'Basic ' + Buffer.from(':' + token()).toString('base64'),
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: body ? JSON.stringify(body) : undefined,
    redirect: 'manual'
  });
  const text = await res.text();
  if (res.status >= 300 && res.status < 400) fail('Azure DevOps redirected to sign-in - the token is invalid or expired');
  if (!res.ok) fail(`Azure DevOps ${method} ${path.split('?')[0]} -> HTTP ${res.status}: ${text.slice(0, 300)}`);
  if (text.trimStart().startsWith('<')) fail('Azure DevOps returned an HTML sign-in page - the token is invalid or expired');
  return text ? JSON.parse(text) : {};
}

function originOf(cwd) {
  if (!existsSync(join(cwd, '.git'))) fail(`no clone at ${cwd} - run: devops.mjs clone --project <P> --repo <R>`);
  const url = git(['remote', 'get-url', 'origin'], { cwd, quiet: true }).stdout.trim();
  const o = parseOrigin(url);
  if (!o) fail(`origin of ${cwd} is not a ${CONFIG.devops.organization} Azure DevOps repo`);
  if (!repoAllowed(o.project, o.repo)) fail(`${o.project}/${o.repo} is not an allowed repo (config.json read_repos / write_targets)`);
  return o;
}

/** Folders the agents may change in this clone; fails for read-only repos (e.g. Fams24). */
function writePathsFor(cwd) {
  if (TEST) return (process.env.FAMS_VUE_TEST_WRITE_PATHS || 'FAMS-UI/').split(',');
  const o = originOf(cwd);
  const t = writeTarget(o.project, o.repo);
  if (!t) fail(`${o.project}/${o.repo} is READ-ONLY for the agents. Changes are only allowed in a repo + folder Hennie has added to config.json write_targets - ask the Lead`);
  return t.paths;
}

function readBody(args) {
  const p = str(args, 'body-file');
  const problem = bodyPathProblem(p);
  if (problem) fail(problem);
  const text = readFileSync(resolve(p), 'utf8');
  if (existsSync(TOKEN_FILE) && text.includes(readFileSync(TOKEN_FILE, 'utf8').trim())) fail('body contains the access token - refusing');
  return text;
}

const SECRET_RE = /(AIza[0-9A-Za-z_-]{30,}|ntn_[0-9A-Za-z]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(password|secret|apikey|api_key|accountkey|clientkey|licen[cs]e(key)?)\b\s*[:=]\s*['"][^'"]{8,}['"])/i;

// ---------- commands ----------

const commands = {
  async whoami() {
    const d = await api('connectionData', { apiVersion: '7.1-preview.1' });
    console.log(JSON.stringify({ organization: CONFIG.devops.organization, user: d.authenticatedUser?.providerDisplayName, id: d.authenticatedUser?.id }, null, 2));
  },

  async projects() {
    const d = await api('projects');
    for (const p of d.value || []) console.log(p.name);
  },

  async repos(args) {
    const d = await api('git/repositories', { project: str(args, 'project', false) });
    for (const r of d.value || []) console.log(`${r.project?.name}\t${r.name}\tdefault=${(r.defaultBranch || '').replace('refs/heads/', '')}`);
  },

  async clone(args) {
    const project = str(args, 'project');
    const dir = repoDir(str(args, 'repo'));
    if (!repoAllowed(project, args.repo)) fail(`${project}/${args.repo} is not an allowed repo (config.json read_repos / write_targets) - ask the Lead`);
    if (existsSync(join(dir, '.git'))) {
      git(['fetch', '--prune', 'origin'], { cwd: dir });
      console.log(`updated ${dir}`);
    } else {
      mkdirSync(dirname(dir), { recursive: true });
      git(['clone', repoUrl(project, args.repo), dir]);
      console.log(`cloned into ${dir}`);
    }
    installPrePushHook(dir);
  },

  async branch(args) {
    const dir = repoDir(str(args, 'repo'));
    const writePaths = writePathsFor(dir);  // read-only repos stop here
    const name = str(args, 'name');
    const p = branchProblem(name);
    if (p) fail(p);
    const from = CONFIG.git.base_branch;  // always development (Tecmo branching model)
    if (args.from && args.from !== from) fail(`agent branches always start from ${from}`);
    const dirty = git(['status', '--porcelain'], { cwd: dir, quiet: true }).stdout.trim();
    if (dirty) fail('working tree has uncommitted changes - commit them or ask the Lead before switching branches');
    git(['fetch', 'origin'], { cwd: dir });
    const has = (ref) => git(['rev-parse', '--verify', '--quiet', ref], { cwd: dir, allowFail: true, quiet: true }).status === 0;
    if (has(`refs/heads/${name}`)) {
      git(['checkout', name], { cwd: dir });                                  // keep local commits
    } else if (has(`refs/remotes/origin/${name}`)) {
      git(['checkout', '-b', name, '--track', `origin/${name}`], { cwd: dir }); // continue a pushed branch
    } else {
      if (!has(`refs/remotes/origin/${from}`)) fail(`origin/${from} not found - this repo has no ${from} branch; ask the Lead (a human must create it)`);
      git(['checkout', '--no-track', '-b', name, `origin/${from}`], { cwd: dir });
    }
    installPrePushHook(dir);
    console.log(`on ${name}`);
  },

  async commit(args) {
    const dir = repoDir(str(args, 'repo'));
    const writePaths = writePathsFor(dir);  // read-only repos stop here
    const message = str(args, 'message');
    const b = currentBranch(dir);
    const p = branchProblem(b);
    if (p) fail(`refusing to commit on ${b}: ${p}`);
    if (args.all) git(['add', '--all'], { cwd: dir });
    const staged = git(['diff', '--cached', '--name-only', '--no-renames'], { cwd: dir, quiet: true }).stdout.trim();
    if (!staged) fail('nothing staged to commit');
    const outside = pathProblems(staged.split('\n'), writePaths);
    if (outside.length) fail(`agents may only change files under ${writePaths.join(', ')} - unstage these (git restore --staged <file>):\n${outside.slice(0, 10).join('\n')}`);
    const tok = existsSync(TOKEN_FILE) ? readFileSync(TOKEN_FILE, 'utf8').trim() : '';
    const added = git(['diff', '--cached', '-U0'], { cwd: dir, quiet: true }).stdout.split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++'));
    const hits = added.filter((l) => SECRET_RE.test(l) || (tok && l.includes(tok)));
    if (hits.length) fail(`staged changes look like they contain a secret/key - remove it (fams-ui-standards §5):\n${hits.slice(0, 3).map((l) => l.slice(0, 120).replace(tok || '\u0000', '<TOKEN>')).join('\n')}`);
    git(['commit', '-m', message], { cwd: dir });
  },

  async push(args) {
    const dir = repoDir(str(args, 'repo'));
    const writePaths = writePathsFor(dir);  // read-only repos stop here
    const b = currentBranch(dir);
    const p = branchProblem(b);
    if (p) fail(`refusing to push ${b}: ${p}`);
    installPrePushHook(dir);
    git(['push', 'origin', `refs/heads/${b}:refs/heads/${b}`], { cwd: dir });
    console.log(`pushed ${b}`);
  },

  async 'pr-create'(args) {
    const dir = repoDir(str(args, 'repo'));
    writePathsFor(dir);  // no PRs on read-only repos
    const { project, repo } = originOf(dir);
    const title = str(args, 'title');
    const source = currentBranch(dir);
    const p = branchProblem(source);
    if (p) fail(`source branch ${source}: ${p}`);
    const target = str(args, 'target', false) || CONFIG.git.base_branch;
    if (!CONFIG.git.allowed_pr_targets.includes(target)) fail(`pull requests may only target: ${CONFIG.git.allowed_pr_targets.join(', ')}`);
    git(['fetch', 'origin'], { cwd: dir, quiet: true });
    const local = git(['rev-parse', 'HEAD'], { cwd: dir, quiet: true }).stdout.trim();
    const remote = git(['rev-parse', '--verify', '--quiet', `refs/remotes/origin/${source}`], { cwd: dir, quiet: true, allowFail: true }).stdout.trim();
    if (remote !== local) fail(`origin/${source} is not up to date with your branch - run devops.mjs push first`);
    const body = {
      sourceRefName: `refs/heads/${source}`,
      targetRefName: `refs/heads/${target}`,
      title,
      description: readBody(args).slice(0, 3900),
      isDraft: !!args.draft
    };
    const pr = await api(`git/repositories/${encodeURIComponent(repo)}/pullrequests`, { method: 'POST', body, project });
    console.log(JSON.stringify({ id: pr.pullRequestId, url: prWebUrl(project, repo, pr.pullRequestId), source, target, draft: body.isDraft }, null, 2));
  },

  async 'pr-status'(args) {
    const dir = repoDir(str(args, 'repo'));
    const { project, repo } = originOf(dir);
    const id = str(args, 'id');
    const pr = await api(`git/repositories/${encodeURIComponent(repo)}/pullrequests/${encodeURIComponent(id)}`, { project });
    let policies = [];
    try {
      const artifact = `vstfs:///CodeReview/CodeReviewId/${pr.repository?.project?.id}/${pr.pullRequestId}`;
      const ev = await api(`policy/evaluations?artifactId=${encodeURIComponent(artifact)}`, { project, apiVersion: '7.1-preview.1' });
      policies = (ev.value || []).map((e) => ({ policy: e.configuration?.type?.displayName, status: e.status }));
    } catch (e) {
      policies = [{ note: `policy status unavailable: ${e.message}` }];
    }
    console.log(JSON.stringify({
      id: pr.pullRequestId, status: pr.status, mergeStatus: pr.mergeStatus, isDraft: pr.isDraft,
      reviewers: (pr.reviewers || []).map((r) => ({ name: r.displayName, vote: r.vote, required: !!r.isRequired })),
      policies,
      url: prWebUrl(project, repo, pr.pullRequestId)
    }, null, 2));
  },

  async 'pr-comments'(args) {
    const dir = repoDir(str(args, 'repo'));
    const { project, repo } = originOf(dir);
    const id = str(args, 'id');
    const d = await api(`git/repositories/${encodeURIComponent(repo)}/pullRequests/${encodeURIComponent(id)}/threads`, { project });
    for (const t of d.value || []) {
      for (const c of t.comments || []) {
        if (c.commentType === 'system') continue;
        console.log(`[thread ${t.id} ${t.status || ''}] ${c.author?.displayName}: ${c.content}`);
      }
    }
  },

  async 'pr-comment'(args) {
    const dir = repoDir(str(args, 'repo'));
    const { project, repo } = originOf(dir);
    const id = str(args, 'id');
    const body = { comments: [{ parentCommentId: 0, content: readBody(args), commentType: 1 }], status: 1 };
    const t = await api(`git/repositories/${encodeURIComponent(repo)}/pullRequests/${encodeURIComponent(id)}/threads`, { method: 'POST', body, project });
    console.log(`posted thread ${t.id}`);
  },

  // Called by the pre-push hook git runs inside each clone (cwd = the clone).
  async 'hook-pre-push'() {
    const input = readFileSync(0, 'utf8');
    const isAncestor = (a, b) => spawnSync('git', ['merge-base', '--is-ancestor', a, b], { encoding: 'utf8' }).status === 0;
    const problems = prePushProblems(input, CONFIG, isAncestor);
    // every file changed by the pushed commits must be under the write target's folders
    let writePaths;
    try { writePaths = writePathsFor(process.cwd()); } catch (e) { problems.push(e.message); writePaths = []; }
    for (const line of input.split('\n').map((l) => l.trim()).filter(Boolean)) {
      const [, localSha, , remoteSha] = line.split(/\s+/);
      if (!localSha || ZERO.test(localSha)) continue;
      const base = remoteSha && !ZERO.test(remoteSha)
        ? remoteSha
        : spawnSync('git', ['merge-base', localSha, `origin/${CONFIG.git.base_branch}`], { encoding: 'utf8' }).stdout.trim();
      if (!base) { problems.push(`cannot find origin/${CONFIG.git.base_branch} to check changed paths`); continue; }
      const files = spawnSync('git', ['diff', '--name-only', '--no-renames', base, localSha], { encoding: 'utf8' }).stdout.split('\n');
      const outside = pathProblems(files, writePaths);
      if (outside.length && writePaths.length) problems.push(`changes outside ${writePaths.join(', ')}: ${outside.slice(0, 5).join(', ')}`);
    }
    if (problems.length) {
      console.error('pre-push blocked by fams-vue-agents:\n - ' + problems.join('\n - '));
      process.exit(1);
    }
  }
};

function isEntryPoint() {
  try { return !!process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url)); }
  catch { return false; }
}

if (isEntryPoint()) {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  if (!cmd || !Object.hasOwn(commands, cmd)) {
    console.log(readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 15).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
    process.exit(cmd ? 2 : 1);
  }
  try {
    await commands[cmd](args);
  } catch (e) {
    console.error(`devops: ${e instanceof DevopsError ? e.message : (e?.message || e)}`);
    process.exit(2);
  }
}
