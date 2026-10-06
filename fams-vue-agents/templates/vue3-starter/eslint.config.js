import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';

// fams-ui-standards §3: only src/service/apiService.js may talk to the network, and no
// .vue file may import a service. These rules make that a build failure, not a review comment.
const NETWORK_IMPORTS = {
  paths: [{ name: 'axios', message: 'Only src/service/apiService.js may import axios (fams-ui-standards §3).' }],
  patterns: []
};
const NETWORK_GLOBALS = [
  { name: 'fetch', message: 'Use a <Feature>Service.js that calls apiService (fams-ui-standards §3).' },
  { name: 'XMLHttpRequest', message: 'Use a <Feature>Service.js that calls apiService (fams-ui-standards §3).' }
];
// Tailwind default palette utilities are forbidden; only fams-* tokens (fams-ui-standards §1).
const DEFAULT_COLOURS = 'slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose';
const COLOUR_UTILITY = `\\b(bg|text|border|ring|outline|fill|stroke|from|via|to|divide|shadow|accent|caret|decoration)-(${DEFAULT_COLOURS})-\\d{2,3}\\b`;
const HEX = '#[0-9a-fA-F]{3,8}\\b';

export default [
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**', 'tests/fixtures/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser }
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/no-mutating-props': 'error',
      'no-restricted-imports': ['error', NETWORK_IMPORTS],
      'no-restricted-globals': ['error', ...NETWORK_GLOBALS],
      'no-restricted-syntax': ['error',
        { selector: `Literal[value=/${COLOUR_UTILITY}/]`, message: 'Default Tailwind colours are not allowed - use fams-* tokens (fams-ui-standards §1).' },
        { selector: `TemplateElement[value.raw=/${COLOUR_UTILITY}/]`, message: 'Default Tailwind colours are not allowed - use fams-* tokens (fams-ui-standards §1).' },
        { selector: `Literal[value=/${HEX}/]`, message: 'No hex colours outside src/theme - use fams-* tokens (fams-ui-standards §1).' }
      ],
      'vue/no-restricted-class': ['error', `/^(bg|text|border|ring|outline|fill|stroke|from|via|to|divide|shadow|accent|caret|decoration)-(${DEFAULT_COLOURS})-\\d{2,3}$/`],
      'vue/no-restricted-syntax': ['error',
        { selector: `Literal[value=/${HEX}/]`, message: 'No hex colours in components - use fams-* tokens (fams-ui-standards §1).' }
      ]
    }
  },
  // .vue files: no services, no apiService, no axios (data comes via composables/stores)
  {
    files: ['src/**/*.vue'],
    rules: {
      'no-restricted-imports': ['error', {
        paths: NETWORK_IMPORTS.paths,
        patterns: [{
          group: ['@/service/*Service', '@/service/*Service.js', '**/service/*Service', '**/service/*Service.js', '*Service', '*Service.js', '**/*Service', '**/*Service.js'],
          caseSensitive: true,
          message: 'Pages/components must not call the API. Use a composable or Pinia store (fams-ui-standards §3).'
        }]
      }]
    }
  },
  // the ONE place that may use axios and the theme files that define the palette
  {
    files: ['src/service/apiService.js'],
    rules: { 'no-restricted-imports': 'off', 'no-restricted-globals': 'off' }
  },
  {
    files: ['src/theme/**/*.js'],
    rules: { 'no-restricted-syntax': 'off' }
  },
  {
    files: ['tests/**/*.js', 'scripts/**/*.mjs', '*.config.*'],
    languageOptions: { globals: { ...globals.node, ...globals.vitest } },
    rules: { 'no-restricted-imports': 'off', 'no-restricted-globals': 'off', 'no-restricted-syntax': 'off' }
  }
];
