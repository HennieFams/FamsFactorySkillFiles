// @vitest-environment node
// (lint tests run in Node: with NODE_ENV=production a jsdom environment resolves node:fs to a browser stub)
import { describe, it, expect } from 'vitest';
import { ESLint } from 'eslint';
import { readFileSync } from 'node:fs';

// The fams-ui-standards §1/§3 rules must actually fire - otherwise the Tester's
// "npm run lint" would pass code that breaks the API rule or the palette.
const eslint = new ESLint({ ignore: false });

async function lint(fixture, asPath) {
  const [res] = await eslint.lintText(readFileSync(`tests/fixtures/${fixture}`, 'utf8'), { filePath: asPath });
  return res.messages.map((m) => m.ruleId);
}

describe('fams lint rules', () => {
  it('rejects axios, service imports and default colours in a .vue page', async () => {
    const rules = await lint('BadPage.vue', 'src/views/fams/x/BadPage.vue');
    expect(rules).toContain('no-restricted-imports');
    expect(rules.filter((r) => r === 'no-restricted-imports').length).toBe(2);
    expect(rules).toContain('vue/no-restricted-class');
  });

  it('rejects fetch and default colours in a composable', async () => {
    const rules = await lint('badComposable.js', 'src/views/fams/x/useX.js');
    expect(rules).toContain('no-restricted-globals');
    expect(rules).toContain('no-restricted-syntax');
  });

  it('accepts a page that gets data from a composable and uses fams tokens', async () => {
    const rules = await lint('GoodPage.vue', 'src/views/fams/x/GoodPage.vue');
    expect(rules).toEqual([]);
  });

  it('allows axios only in src/service/apiService.js', async () => {
    const [res] = await eslint.lintText("import axios from 'axios';\nexport default axios;\n", { filePath: 'src/service/apiService.js' });
    expect(res.messages.map((m) => m.ruleId)).not.toContain('no-restricted-imports');
    const [res2] = await eslint.lintText("import axios from 'axios';\nexport default axios;\n", { filePath: 'src/service/OtherService.js' });
    expect(res2.messages.map((m) => m.ruleId)).toContain('no-restricted-imports');
  });
});
