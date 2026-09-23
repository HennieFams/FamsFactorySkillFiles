---
name: FAMS Tanks
slug: fams-tanks
description: >
  Use when working on tank volume, capacity, tank health or tank communication status —
  including the Tank Communication & Health card (Pilot #1). Covers what a tank record
  means, what "communicating" actually means, and why a stale reading is not the same
  as an empty tank. Don't use for dispensing-transaction work; that's
  FAMS_DATABASE_CORE.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS Tanks

## The distinction that matters most

**No recent reading ≠ empty tank.** A tank whose last ATG update is four hours old is
a *communication* problem, not a *volume* problem. Displaying a stale volume as if it
were current is the single most damaging mistake this area can make — a depot manager
who trusts a stale figure orders fuel he does not need, or fails to order fuel he does.

Every tank figure shown to a user carries its timestamp. No exceptions.

## Pilot #1 — Tank Communication & Health card (§77)

Initial output, and nothing more:

- Tank name
- Current volume
- Capacity %
- Last ATG update
- Communication status
- Last transaction
- Simple warning

**Do not include predictive run-out.** The purpose of Pilot #1 is to validate the
factory across SQL → API → Vue → test → document, not to do data science.

## Definitions to pin down before building

> TO CONFIRM (Hennie):
> - What threshold makes communication status healthy / degraded / lost?
> - Is capacity % against nominal capacity or safe working capacity?
> - Which table is canonical for current volume, and what is the fallback order?
> - What triggers the "simple warning", and what does it say?

An agent must not invent these thresholds. Ask, then record the answer here and move
the skill from DRAFT to VALID.

## Related

Tank level data arrives via ATG — see FAMS_ATG for how the readings are produced and
what can go wrong upstream.
