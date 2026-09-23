---
name: FAMS API Core
slug: fams-api-core
description: >
  Use when developing or reviewing FAMS ASP.NET Core services and APIs — endpoints,
  DTOs, application services, domain logic placement and API contracts. Don't use for
  SQL internals (FAMS_DATABASE_CORE) or Vue components (FAMS_VUE_CORE).
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS API Core

ASP.NET Core.

## Layering

UI → API → application services → domain → data.

Business rules live in the domain layer. They do not get scattered across Vue, SQL and
API controllers. If a rule exists in two of those three places, that is a defect to
raise, not a pattern to copy.

## The contract is the boundary

The OpenAPI specification, the DTOs, the shared enumerations and the event schemas are
owned by Architecture (acting as Contract Guardian). You build against the contract.

If the contract is wrong or insufficient, say so and send it back — do not quietly
implement something different. A backend that disagrees with the contract produces a
frontend that disagrees with the backend, and the disagreement surfaces in production.

## Every response carries its provenance

Where a value is derived from telemetry, the response includes when that telemetry was
read. A volume without a timestamp is not a usable volume (see FAMS_TANKS).

## Errors

Return an error a depot supervisor can act on. "An error occurred" is not an error
message. Distinguish "the device has not reported" from "the query failed" — they lead
to entirely different actions.

## Requires human approval

Anything touching authentication, identity, billing, pricing, SARS logic or
customer-contractual behaviour.

> TO CONFIRM (Hennie): existing FAMS API conventions — auth scheme, versioning
> approach, error envelope shape, naming standards. Record them here before this skill
> moves to VALID, otherwise agents will invent their own.
