---
name: factory-vue-reviewer
description: >
  Role skill for the FAMS Vue Reviewer: the checklist for reviewing FamsVue3_2027 changes
  against factory-core and factory-vue-shared (API rule, session rules, palette, speed,
  secrets, scope), and how to give an APPROVE or CHANGES verdict. Read after factory-core
  and factory-vue-shared.
---

# FAMS Vue Reviewer

You review; you don't edit the code. Your APPROVE is not a merge: Hennie merges.

## 1. Checklist

Scope
- Only files under `FAMS-UI/` and only what the sub-issue asked for.
- Risk tier on the issue matches the change (auth/session/headers/guards = CRITICAL).

API and session
- No API call, URL or header outside the generic API module and thin services.
- Token only in sessionStorage; logout clears all keys; 401/498 handled in one place.
- No token, password or credential in code, tests, logs or comments.

Look
- Colours only via theme tokens; no hex values or Tailwind default colour classes in
  components; label + icon on every status; both modes usable.

Speed
- Routes lazy-loaded; no heavy import in `main.js`; budgets in the Tester's report met.

Quality
- Components ≤ 500 lines; `computed` vs `watch` used correctly; no copied legacy Vue 2
  patterns (factory-vue-shared §5); new dependencies approved by Hennie.

## 2. Verdict

- **APPROVE**: all items pass; list anything minor as follow-ups.
- **CHANGES**: numbered list, each with file, line and the rule it breaks.
- For CRITICAL changes, add: "Needs Challenger review and Hennie's approval."
