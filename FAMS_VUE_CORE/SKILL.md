---
name: FAMS Vue Core
slug: fams-vue-core
description: >
  Use when building or reviewing FAMS Vue 3 frontend work — pages, components,
  dashboards, forms, state and API integration. Covers the FAMS component vocabulary
  and the display rules that keep operational data honest. Don't use for API or SQL
  work.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS Vue Core

Vue 3.

## Component vocabulary

The existing FAMS component set is the vocabulary — extend it rather than inventing
parallel components:

TankCard · DeviceStatus · VehicleCard · AssetCard · FuelTransaction · StockReceipt ·
AlarmCard · ExceptionCard · ATGGraph · SiteSelector · OperatorSelector ·
AssetSelector · DateFilter · ReportViewer · SARSEligibilityIndicator

Before building a new component, check whether one of these already covers it. A second
component that does what TankCard does is a maintenance liability.

## Display rules

- **Never show an operational value without its age.** Volume, level and device status
  all carry a timestamp. Stale data displayed as current is the failure mode this
  product cannot afford (see FAMS_TANKS).
- **Distinguish "no data" from "zero".** An empty tank and a tank that has not reported
  are different states and must look different.
- **Depot conditions.** Users are on handhelds, in sunlight, sometimes with gloves.
  Contrast, touch target size and legibility are functional requirements, not polish.

## Boundaries

Consume the API contract. Do not call the database. Do not reimplement business rules
in the component — if a calculation is missing from the API, raise it with
Architecture rather than computing it in the frontend, or FAMS ends up with two
answers to the same question.

> TO CONFIRM (Hennie): current Vue version and tooling, state management approach,
> design system / component library in use, and where the existing component catalogue
> lives.
