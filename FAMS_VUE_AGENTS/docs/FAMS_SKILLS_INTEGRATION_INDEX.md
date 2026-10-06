---
name: fams-skills-integration-index
description: Master index showing how all FAMS Portal skills integrate together. Maps dependencies, cross-references, and recommended reading order by role/task.
---

# FAMS Portal Skills — Complete Integration Index

## 📋 Skills Ecosystem Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      FAMS PORTAL SKILLS ECOSYSTEM                          │
└───────────────────────────────────────────────────────────────────────────┘

PRIMARY:
  📚 FAMS_PORTAL_MASTER_SKILL.md (11 parts, architecture → deployment)

SUPPLEMENTARY SPECIALIZED SKILLS:
  🎨 FAMS_VUE_CORE_SPECIALIZED.md (frontend Vue 3 + PrimeVue 4)
  🔌 FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md (IoT/serial/Modbus)
  ⚙️  FAMS_TANKS_BUSINESS_SPECIALIZED.md (domain logic/calculations)
  ⛽ FAMS_DISPENSING_SPECIALIZED.md (quick-dispense dialog pattern, balance mutation) 🟡 prototype
  📊 FAMS_QUICK_REPORT_SPECIALIZED.md (10-view reporting menu rebuild, pattern library) 🔵 reference spec

SUPPORTING DOCUMENTS:
  📋 START_HERE.txt (orientation)
  📊 FINAL_SUMMARY.txt (overview)
  📄 FILE_MANIFEST.md (inventory)

REFERENCE DOCUMENTS (Archive):
  🔍 EVALUATION_SUMMARY.md
  🧬 Vue3_FAMS_Portal_Reactive_UPDATED.md
```

---

## 📚 Skill Descriptions

### 1. FAMS_PORTAL_MASTER_SKILL.md ⭐⭐⭐

**Scope:** Core frontend architecture, Vue 3 patterns, routing, state management, deployment

**11 Parts:**
- Part 1: Architecture & Tech Stack (directory structure)
- Part 2: Vue 3 Reactivity (ref, reactive, computed, watch)
- Part 3: PrimeVue 4 & Tailwind (components & styling)
- Part 4: Pinia State Management (stores, composables)
- Part 5: Routing & Authentication (routes, guards)
- Part 6: Service Layer & API (axios, entity services)
- Part 7: Styling & Design Tokens (dark mode, themes)
- Part 8: Feature Implementation Blueprint (6-step guide)
- Part 9: Code Quality & Anti-Patterns (review checklist)
- Part 10: Deployment & Release (build, env, phases)
- Part 11: Quick Reference (templates, checklists)

**When to Use:**
- ALL frontend development
- Architectural decisions
- Routing/auth patterns
- Code review

**Size:** 1,800+ lines, 50+ examples

---

### 2. FAMS_VUE_CORE_SPECIALIZED.md 🎨

**Scope:** Frontend component standards, PrimeVue 4 usage, Pilot #1 UI implementation

**Topics:**
- Vue 3 reactivity essentials (ref vs reactive)
- PrimeVue 4 component reference
- Tailwind CSS + PassThrough styling
- TankCard.vue (Pilot #1)
- DeviceStatus.vue (Pilot #1)
- Pinia store patterns
- Anti-patterns to reject

**When to Use:**
- Building Vue components
- Using PrimeVue elements
- Styling with Tailwind
- Implementing Pilot #1 cards

**Size:** ~600 lines, 10+ examples

**Cross-References:**
- Master Skill Part 2 (Vue 3 reactivity)
- Master Skill Part 3 (PrimeVue components)
- Master Skill Part 4 (Pinia stores)

---

### 3. FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md 🔌

**Scope:** IoT/edge layer, serial/TCP protocols, Veeder-Root telemetry parsing

**Topics:**
- RS-232 serial configuration (9600 8N1)
- TCP/IP socket connections (retry, timeout)
- Veeder-Root VR-S90 protocol
  - Frame structure (<SOH>, <ETX>, checksum)
  - Command set (i20100 inventory)
  - Response parsing (fixed-width columns)
- Checksum validation (XOR algorithm)
- Parse pipeline (framing → validation → tokenization)
- Fault shielding & logging
- Communication watchdog (offline detection)
- Test scenarios & load testing

**When to Use:**
- Parsing ATG telemetry frames
- Validating serial/socket connections
- Implementing error handling
- Writing tests for protocol handling

**Size:** ~650 lines, 8+ code examples

**Cross-References:**
- FAMS_TANKS_BUSINESS_SPECIALIZED.md (parsed data consumption)
- FAMS_API_CORE-v2.md (API envelope format)

---

### 4. FAMS_TANKS_BUSINESS_SPECIALIZED.md ⚙️

**Scope:** Domain logic, volume calculations, capacity rules, status classification

**Topics:**
- Horizontal cylinder volume calculations
  - Geometric segment formula (theta, area, volume)
  - Non-linear depth → volume relationship
  - C# implementation with validation
  - Example calculation walkthrough
- Strapping table interpolation (fallback method)
- Capacity percentage (95% safe fill rule)
- Threshold alert matrix (5 status levels)
  - Critical overfill (≥95%)
  - Warning high fill (85-95%)
  - Healthy (15-85%)
  - Warning low fill (5-15%)
  - Critical run-out (≤5%)
- Telemetry status logic
  - Offline boundary (10-minute threshold)
  - Simulated data annotation ("[EMULATED]")
- Validation pipeline
- Domain models (Tank, TankStatus, TelemetrySnapshot)

**When to Use:**
- Implementing volume calculations
- Building capacity warning systems
- Validating tank data
- Creating tank domain models

**Size:** ~700 lines, 10+ code examples

**Cross-References:**
- FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md (sensor input)
- FAMS_VUE_CORE_SPECIALIZED.md (UI display)
- Master Skill Part 6 (API layer)

---

### 5. FAMS_DISPENSING_SPECIALIZED.md ⛽

**Scope:** Quick Dispensing feature — dialog-based quick-action form pattern, cross-field validation against live tank balance, local balance mutation on submit

**Topics:**
- Dialog vs. Drawer pattern (quick-action vs. entity editor)
- `useDispensingForm.js` / `useDispensingLookups.js` composable pair
- Volume validation cross-checked against selected tank's current level
- Equipment lockout pattern (Maintenance status blocks Quick Dispense)
- Known prototype→production gaps (no service layer yet, local-only balance mutation, void-transaction doesn't reverse balances)

**When to Use:**
- Building or extending the Dispensing page/dialog
- Modeling any other "quick action" modal (as opposed to a full Drawer create/edit form)
- Wiring dispensing onto the real API (see its Known Gaps checklist)

**Status:** 🟡 Prototype (mock data, no service layer wired yet)

**Size:** ~250 lines, 2 composables + 2 components documented

**Cross-References:**
- Master Skill Part 6 (Service Layer — not yet wired in this feature)
- Master Skill Part 8 (Feature Blueprint — this feature intentionally deviates: Dialog not Drawer)
- FAMS_TANKS_BUSINESS_SPECIALIZED.md (tank capacity thresholds — note: dispensing uses different equipment fuel-level cutoffs, don't conflate)
- FAMS_VUE_CORE_SPECIALIZED.md (PrimeVue component/anti-pattern reference)

---

### 6. FAMS_QUICK_REPORT_SPECIALIZED.md 📊

**Scope:** Rebuild reference for the legacy "Quick Report" menu — 10 sub-views and 8 reusable reporting UI patterns (Filter Panel, KPI Row, Data Grid, Pivot Table, Live Monitor Grid, Calendar Heatmap, Chart View, Map View)

**⚠️ Naming Collision:** Contains "QuickDisp/QuickDispenseNew" — a **reporting** view over historical transactions. This is a different feature from `fams-dispensing`'s **transactional** Quick Dispensing dialog. Read the warning at the top of this skill before working on anything "dispensing"-named.

**Topics:**
- Legacy sub-view inventory + suggested new route names
- Reusable pattern library mapped to shared Vue components
- Real legacy backend contract (`api24.fams.co.za`) and an auth-hardening recommendation (move `clientKey`/`accountkey` out of the query string)
- Directory placement reconciled with Master Skill conventions (the source doc's suggested layout didn't match `src/views/fams/<feature>/`)

**When to Use:**
- Rebuilding any Quick Report sub-view
- Building a shared report component (grid, filter panel, pivot builder, etc.)
- Wiring report views to the legacy API
- Before touching anything with "dispensing" in the name — check the collision warning first

**Status:** 🔵 Reference spec (describes the legacy system to rebuild, not existing Vue 3 code)

**Size:** ~350 lines

**Cross-References:**
- Master Skill Part 5/6 (routing, service layer)
- FAMS_VUE_CORE_SPECIALIZED.md (PrimeVue DataTable, styling tokens)
- FAMS_TANKS_BUSINESS_SPECIALIZED.md (tank math feeding the Live Monitoring Grid)
- FAMS_DISPENSING_SPECIALIZED.md (naming collision — read before starting)

---

## 🗺️ Reading Order by Role

### Frontend Developer (New to Vue 3)

**Path 1: Learning (First Week)**
1. ✅ START_HERE.txt (5 min)
2. ✅ Master Skill Part 1 (Architecture) (10 min)
3. ✅ Master Skill Part 2 (Vue 3 Reactivity) (30 min)
4. ✅ Master Skill Part 3 (PrimeVue 4) (20 min)
5. ✅ FAMS_VUE_CORE_SPECIALIZED.md (30 min)

**Path 2: Implementation (First Feature)**
6. ✅ Master Skill Part 8 (Feature Blueprint) (30 min)
7. ✅ Follow Part 8.1 step-by-step (2-3 hours)
8. ✅ Check Master Skill Part 9.2 (Pre-Commit Checklist)

**Path 3: Advanced**
9. ✅ Master Skill Part 4 (Pinia)
10. ✅ Master Skill Part 5 (Routing)

**Estimated Time:** ~8-10 hours for productivity

---

### Backend/IoT Developer (Tank Communications & Logic)

**Path 1: Understanding (First Day)**
1. ✅ START_HERE.txt (5 min)
2. ✅ FAMS_TANKS_BUSINESS_SPECIALIZED.md (40 min)
3. ✅ FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md (50 min)

**Path 2: Implementation (Tank Parsing)**
4. ✅ FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md Section 3 (Parsing Logic)
5. ✅ FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md Section 4 (Validation)
6. ✅ Implement parser + validators (3-4 hours)

**Path 3: Business Logic Integration**
7. ✅ FAMS_TANKS_BUSINESS_SPECIALIZED.md Section 3-6
8. ✅ Build tank domain models + calculations (2-3 hours)

**Path 4: API Contract**
9. ✅ Master Skill Part 6 (Service Layer)

**Estimated Time:** ~6-8 hours for end-to-end

---

### Full-Stack Integrator (Sensor → UI → API)

**Path 1: Complete Picture (First Day)**
1. ✅ START_HERE.txt (5 min)
2. ✅ Master Skill Part 1 (Architecture) (10 min)
3. ✅ FAMS_ATG_COMMUNICATIONS_SPECIALIZED.md Section 1-2 (20 min)
4. ✅ FAMS_TANKS_BUSINESS_SPECIALIZED.md Section 1-3 (30 min)
5. ✅ FAMS_VUE_CORE_SPECIALIZED.md (UI components) (20 min)
6. ✅ Master Skill Part 8 (Feature patterns) (20 min)

**Path 2: Implementation (Data Flow)**
7. ✅ Parse telemetry (FAMS_ATG_COMMUNICATIONS)
8. ✅ Calculate volume (FAMS_TANKS_BUSINESS)
9. ✅ Persist via API (Master Skill Part 6)
10. ✅ Display in UI (FAMS_VUE_CORE)

**Estimated Time:** ~10-12 hours for complete integration

---

### Code Reviewer / QA

**Path 1: Review Guidelines (30 minutes)**
1. ✅ Master Skill Part 9 (Anti-Patterns & Checklist)
2. ✅ FAMS_VUE_CORE_SPECIALIZED.md Section 7 (Frontend anti-patterns)

**Path 2: Specific Component Review**
- If reviewing frontend → Use Master Skill Part 3 + FAMS_VUE_CORE
- If reviewing ATG parser → Use FAMS_ATG_COMMUNICATIONS Section 3-4
- If reviewing tank logic → Use FAMS_TANKS_BUSINESS Section 3-6

**Estimated Time:** ~1-2 hours for checklist mastery

---

## 🔗 Cross-Skill Dependencies

### Frontend → Backend Flow

```
FAMS_VUE_CORE (TankCard.vue)
  │
  ├─ Displays: currentVolume, capacityPercentage, status
  │
  └─→ FAMS_TANKS_BUSINESS (CapacityPercentage calculation)
       │
       └─→ FAMS_ATG_COMMUNICATIONS (CurrentVolume from telemetry)
            │
            └─→ Master Skill Part 6 (API integration)
                 │
                 └─→ Master Skill Part 5 (Route handler)
```

### Data Transform Pipeline

```
1. PHYSICAL SENSOR (ATG Device)
   └─ RS-232 Stream: <SOH>I20100...VOLUME=14250.5<ETX>{CHECKSUM}

2. FAMS_ATG_COMMUNICATIONS_SPECIALIZED
   └─ Parser: Validates checksum → Extracts depth (1425mm)

3. FAMS_TANKS_BUSINESS_SPECIALIZED
   └─ Calculator: depth (1425mm) → volume (14250L) → capacity (75%)

4. Master Skill Part 6 (API Layer)
   └─ Service: POST /tanks/{id}/telemetry → Database

5. Master Skill Part 4 (State Management)
   └─ Pinia: useTankStore.updateTank()

6. FAMS_VUE_CORE_SPECIALIZED
   └─ Component: TankCard displays volume + percentage + status

7. Master Skill Part 11 (Quick Ref)
   └─ User sees real-time dashboard update
```

---

## 📍 Skill Matrix: Which Skill for Which Task?

| Task | Primary Skill | Secondary Skills |
|------|--------------|------------------|
| Create new Vue component | Master Part 8 | VUE_CORE |
| Build DataTable | VUE_CORE Section 4 | Master Part 3 |
| Implement form with validation | Master Part 2 | VUE_CORE Section 3 |
| Parse ATG telemetry frame | ATG_COMM Sections 3-4 | TANKS_BUSINESS Section 5 |
| Calculate tank volume | TANKS_BUSINESS Section 2 | (none) |
| Show capacity warning | VUE_CORE + TANKS_BUSINESS | Master Part 9 |
| Implement Pinia store | Master Part 4 | VUE_CORE Section 6 |
| Setup route with auth | Master Part 5 | (none) |
| Call backend API | Master Part 6 | (none) |
| Review code | Master Part 9 | VUE_CORE Section 7 |
| Deploy to production | Master Part 10 | (none) |
| Build a quick-action dialog (not full CRUD) | DISPENSING_SPECIALIZED | Master Part 8 |
| Validate a field against another live entity | DISPENSING_SPECIALIZED Section 4 | Master Part 2 |
| Build a filter-panel + data-grid report view | QUICK_REPORT_SPECIALIZED Section 3.1/3.3 | VUE_CORE |
| Build a pivot table / KPI card row / live monitor grid | QUICK_REPORT_SPECIALIZED Section 3 | Master Part 3 |
| Wire up the legacy api24.fams.co.za backend | QUICK_REPORT_SPECIALIZED Section 4 | Master Part 6 |
| Am I building "Dispensing" the transaction or the report? | ⚠️ QUICK_REPORT_SPECIALIZED collision warning | DISPENSING_SPECIALIZED |

---

## ✅ Dependency Checklist

**Before using FAMS_VUE_CORE_SPECIALIZED:**
- [x] Understand Master Skill Part 2 (Vue 3 reactivity)
- [x] Know Master Skill Part 3 (PrimeVue 4)
- [x] Understand Master Skill Part 4 (Pinia stores)

**Before using FAMS_ATG_COMMUNICATIONS_SPECIALIZED:**
- [x] Understand FAMS_TANKS_BUSINESS_SPECIALIZED (data consumption)
- [x] Know Master Skill Part 6 (API contracts)
- [x] Familiar with serial/socket programming concepts

**Before using FAMS_TANKS_BUSINESS_SPECIALIZED:**
- [x] Understand FAMS_ATG_COMMUNICATIONS_SPECIALIZED (sensor input)
- [x] Know FAMS_VUE_CORE_SPECIALIZED (UI display)
- [x] Familiar with decimal math & domain models

**Before using Master Skill Part 8 (Feature Blueprint):**
- [x] Understand Parts 1-6 (architecture basics)
- [x] Familiar with FAMS_VUE_CORE_SPECIALIZED (if frontend)
- [x] Know the relevant specialized skills (ATG/Tanks if needed)

---

## 📊 Pilot #1 Specific References

**Pilot #1:** Tank Communication & Health Card

### Required Skills for Pilot #1:

**Frontend:**
- Master Skill Part 1 (where to put files)
- Master Skill Part 2 (Vue 3 patterns)
- Master Skill Part 3 (PrimeVue DataTable)
- FAMS_VUE_CORE_SPECIALIZED (TankCard.vue, DeviceStatus.vue)
- Master Skill Part 8.1 (6-step blueprint)

**Backend:**
- FAMS_ATG_COMMUNICATIONS_SPECIALIZED (parse telemetry)
- FAMS_TANKS_BUSINESS_SPECIALIZED (volume calculations)
- Master Skill Part 6 (API service layer)

**Integration:**
- Master Skill Part 5 (routes)
- Master Skill Part 4 (Pinia stores)

---

## 🔍 Quick Lookup Table

**Question** | **Skill & Section**
---|---
"Where should I put my component file?" | Master Part 1.2 (Directory Structure)
"Should I use ref or reactive?" | Master Part 2.1 + VUE_CORE Section 3
"How do I use DataTable?" | Master Part 3.1 + VUE_CORE Section 4
"How do I bind a DatePicker?" | VUE_CORE Section 4 (Component Reference)
"How do I create a Pinia store?" | Master Part 4.1
"How do I add a route?" | Master Part 5.1
"How do I call an API?" | Master Part 6 (Service Layer)
"How do I parse ATG telemetry?" | ATG_COMM Section 3 (Parsing Pipeline)
"How do I calculate tank volume?" | TANKS_BUSINESS Section 2 (Calculations)
"How do I get capacity percentage?" | TANKS_BUSINESS Section 3 + VUE_CORE
"What's the 10-min offline rule?" | TANKS_BUSINESS Section 5 (Telemetry Status)
"What are the capacity thresholds?" | TANKS_BUSINESS Section 4 (Alert Matrix)
"Build TankCard component?" | VUE_CORE Section 5.1
"Build DeviceStatus component?" | VUE_CORE Section 5.2
"What anti-patterns should I avoid?" | Master Part 9.1 + VUE_CORE Section 7
"What's the pre-commit checklist?" | Master Part 9.2
"How do I build a quick-dispense style modal?" | DISPENSING_SPECIALIZED Section 1
"Why is getTankById broken / what got fixed?" | DISPENSING_SPECIALIZED Section 3

---

## 🚀 Getting Started

### For Your First Feature (30 min → 3 hours)

**Step 1: Choose Your Role**
- [ ] Frontend developer? → Start with Frontend path above
- [ ] Backend/IoT developer? → Start with Backend path above
- [ ] Full-stack? → Start with Full-Stack path above

**Step 2: Read START_HERE.txt (5 min)**
- Orients you to all available skills
- Shows what files you have

**Step 3: Read Primary Skill (15-30 min)**
- For frontend: Master Skill Part 1 & 8
- For backend: FAMS_ATG + FAMS_TANKS
- For full-stack: All intro sections

**Step 4: Implement (1-3 hours)**
- Follow specific section of chosen skill
- Use code examples as templates
- Check Pre-Commit Checklist before finishing

**Step 5: Code Review (15 min)**
- Use Master Skill Part 9.2 checklist
- Reference anti-patterns in Master Part 9.1

---

## 📝 Summary

**The Complete FAMS Skills Ecosystem provides:**
- ✅ 1 master skill (1,800+ lines)
- ✅ 5 specialized skills (domain-specific; 1 prototype-status, 1 reference-spec-status)
- ✅ 50+ code examples
- ✅ 6-step feature blueprint (plus 1 documented deviation: dialog-based quick actions)
- ✅ 8 reusable reporting UI patterns mapped to shared components
- ✅ Pre-commit checklists
- ✅ Anti-pattern guidelines
- ✅ 1 explicit naming-collision warning (Dispensing feature vs. Dispensing report)
- ✅ Clear reading paths by role

**Total Content:** 3,100+ lines, 100% coverage of Pilot #1 development + Dispensing prototype + Quick Report rebuild spec

**Status:** ✅ Production Ready

---

**Next Review Date:** 2026-11-01
