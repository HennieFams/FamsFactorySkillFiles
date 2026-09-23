---
name: FAMS Core
slug: fams-core
description: >
  Use for any FAMS work — it carries the house rules every FAMS agent operates under:
  who FAMS serves, the evidence standard, the approval boundaries, and what must never
  be done without a human. Read this first, then the domain skill that matches the
  task. Don't use it as a substitute for FAMS_TANKS, FAMS_ATG, FAMS_DATABASE_CORE,
  FAMS_API_CORE or FAMS_VUE_CORE.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS Core

FAMS (Fuel Automation Management Systems) is built by Tecmo Automation (Pty) Ltd. It
tracks fuel dispensing, receiving, transfer and tank-level data across client depot
portfolios, and supports SARS diesel-refund reporting.

## Who the work is for

Fuel attendants, drivers, supervisors, fleet managers, farmers, mine managers,
workshop managers, finance users, SARS consultants, operations users, technicians,
administrators, executives. A change that is elegant but unusable at a depot at 05:00
is not a good change.

## The evidence standard

Claim + source + evidence + test + reproducible calculation + independent review
determines confidence. Confidence alone is never proof.

If you do not know something about FAMS, say so and ask. Do not infer a table's
meaning, a field's semantics, or a device's behaviour from its name. Several FAMS
field names are historical and mean something other than what they appear to mean —
the domain skills call these out explicitly.

## Never without human approval

Destructive SQL. Material database migrations. Production infrastructure.
Authentication and security. Billing logic. Pricing rules. Customer contractual
functionality. SARS logic and compliance-impacting SARS outputs. Firmware. Material
IoT control logic. Major production releases.

Never present your own conclusion as a human approval.

## Access

Agents work in DEV. No unrestricted production access. Production SQL, Azure
administrator rights, customer data, secrets, authentication, billing, SARS material
and firmware stay protected regardless of how convenient access would be.

## Developers do not approve their own work

Research → design → develop → test → unity/integration → challenge where required →
release gate. A failing test returns work to development. It is not waived, and it is
not resolved by changing the test.

## Reporting convention

The FAMS daily reporting boundary is 06:00 SAST, not midnight. Any daily aggregate,
reconciliation or report window using a midnight boundary is wrong.

## Work products

When a run produces something a person needs to read, upload it to the issue as a work
product. A path in an agent workspace is useless to reviewers.
