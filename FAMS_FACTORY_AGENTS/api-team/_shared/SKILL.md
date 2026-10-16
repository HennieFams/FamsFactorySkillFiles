---
name: factory-api-shared
description: >
  NOT READY — do not assign to any agent yet. Placeholder for the API team (API Architect, API Developer, API Tester) role skill in the
  new FAMS factory skill set. Will be written fresh from the code and Hennie's decisions.
---

# API team (API Architect, API Developer, API Tester) — not written yet

Status: not started (see ../../REGISTRY.md). Agents must not load this skill.

## Sections planned
- FAMS-API structure from the code: .NET 10, 127 controllers, services, EF context (FAMS2018Context), JWT Bearer, rate limiter, routes api/<Controller> (+ <Controller> on 32)
- Which repo is the API's home (FamsVue3_2027/FAMS-API vs Fams24/FAMS-API) and which branch the agents work from — ask Hennie
- The live FAMS-API and the dedicated agent account: who may call what
- Credentials: appsettings*.json and DBInfo.txt hold real secrets — never open, print or edit them
- Contract rule: OpenAPI + DTO owned by the API Architect; Vue consumes the contract, not the SQL

## Write it from
- FamsVue3_2027 FAMS-API (Program.cs, Controllers, Services, DTOs, FAMS.API.Tests)
- Hennie's decisions (15 Oct: API has its own agent group; dedicated live-API account)
