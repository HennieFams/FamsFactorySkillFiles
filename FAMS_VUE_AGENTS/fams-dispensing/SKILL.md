---
name: fams-dispensing-specialized
description: Use when building or extending the FAMS Quick Dispensing feature (Dispensing.vue, DispensingDialog.vue), any dialog-based "quick action" modal (as opposed to a full Drawer create/edit form), or validating a field against another live entity's current balance (e.g. dispensed volume vs. tank level). Working reference implementation is bundled in this skill's reference/ folder. Load alongside fams-portal-master and fams-tanks-business.
---

# FAMS Dispensing Feature — Specialized Skill

## 📋 Metadata
| Field | Value |
|-------|-------|
| **VERSION** | 1.0.0 (initial capture from Pilot dispensing prototype) |
| **STATUS** | 🟡 Prototype — mock data, no service layer wired yet |
| **DEPENDENCIES** | fams-portal-master skill (Parts 2, 3, 6, 8), FAMS_fams-vue-core/SKILL.md, FAMS_TANKS_BUSINESS_SPECIALIZED |
| **NEXT REVIEW** | 2026-11-01 |

---

## Quick Reference

**When to Use This Skill:**
- Building or extending the Quick Dispensing page/dialog
- Any feature that mutates tank or equipment balances as a side effect of a transaction
- Modeling a "dialog-based quick action" instead of a full Drawer create/edit form

**Don't Use This For:**
- Tank volume math from raw sensor depth (see `fams-tanks-business/SKILL.md`)
- Generic PrimeVue component reference (see `fams-vue-core/SKILL.md`)
- Full CRUD feature scaffolding for a new entity (see fams-portal-master skill Part 8, which uses the Drawer pattern this feature intentionally deviates from)

---

## 0. Bundled Reference Implementation

This skill folder includes the actual working (bug-fixed) source files under `reference/`:
- `reference/Dispensing.vue`
- `reference/DispensingDialog.vue`
- `reference/useDispensingForm.js`
- `reference/useDispensingLookups.js`

Read these directly rather than only the code blocks below when you need the exact current implementation to copy from or diff against.

## 1. Feature Shape

This feature uses a **3-file variant** of the standard feature-module split — a page, a *Dialog* (not Sidebar/Drawer), and two composables:

```
src/views/fams/dispensing/
├── Dispensing.vue              # Page: tank widgets + equipment cards + transaction log
├── DispensingDialog.vue        # Modal: quick-dispense / manual-dispense form
├── useDispensingForm.js        # Form state, validation, submit + balance mutation
└── useDispensingLookups.js     # Mock equipment/tank/transaction data + status list
```

**Why a Dialog instead of a Drawer:** the fams-portal-master skill's Part 8 blueprint uses a Drawer/Sidebar for full entity create/edit. Dispensing is a short, single-purpose action triggered from a card ("Quick Dispense") or a top-level button ("Log Manual Dispense") — a modal fits that interaction better than a persistent side panel. Treat this as the sanctioned pattern for **quick-action forms**, distinct from **entity editors**.

**Why no `useDispensingPayloads.js`:** the transaction DTO is small and built once, inline, inside `submitForm()`. Only promote payload-building into its own composable if the DTO shape grows or is reused elsewhere (e.g., if a bulk-dispense feature needs the same builder).

---

## 2. Data Model (Mock Lookups)

```javascript
// useDispensingLookups.js — reference shape
equipments: [{ id, name, type, limitLiters, currentLevel, status, lastFuelDate }]
tanks:      [{ id, name, capacity, currentLiters, product }]
transactions: [{ id, timestamp, equipmentId, equipmentName, tankId, volume, operator, status }]
statuses:   [{ label, value }]   // Completed | Pending | Voided
```

This is static mock data standing in for what will eventually be `EquipmentService`, `TankService`, and `DispensingTransactionService` calls (see §5, Known Gaps).

---

## 3. Composable: `useDispensingLookups.js`

```javascript
// src/views/fams/dispensing/useDispensingLookups.js
import { ref } from 'vue';

export function useDispensingLookups() {
  const equipments = ref([
    { id: 'EQ-001', name: 'CAT Excavator 320', type: 'Heavy Machinery', limitLiters: 400, currentLevel: 120, status: 'Active', lastFuelDate: '2026-09-06' },
    { id: 'EQ-002', name: 'Volvo Hauler A40G', type: 'Fleet Vehicle', limitLiters: 500, currentLevel: 380, status: 'Active', lastFuelDate: '2026-09-05' },
    { id: 'EQ-003', name: 'Cummins Generator 250kVA', type: 'Generator', limitLiters: 800, currentLevel: 75, status: 'Maintenance', lastFuelDate: '2026-09-01' },
    { id: 'EQ-004', name: 'John Deere Tractor 8R', type: 'Heavy Machinery', limitLiters: 350, currentLevel: 290, status: 'Active', lastFuelDate: '2026-09-07' },
    { id: 'EQ-005', name: 'Toyota Hilux Service Truck', type: 'Support Fleet', limitLiters: 80, currentLevel: 15, status: 'Active', lastFuelDate: '2026-09-04' }
  ]);

  const tanks = ref([
    { id: 'Tank-01', name: 'Main Diesel Tank 01', capacity: 20000, currentLiters: 14250, product: 'Diesel' },
    { id: 'Tank-02', name: 'Auxiliary Diesel Tank 02', capacity: 10000, currentLiters: 8400, product: 'Diesel' }
  ]);

  const transactions = ref([
    { id: 'TXN-98421', timestamp: '2026-09-07 10:15:30', equipmentId: 'EQ-001', equipmentName: 'CAT Excavator 320', tankId: 'Tank-01', volume: 150.5, operator: 'John Doe', status: 'Completed' },
    { id: 'TXN-98422', timestamp: '2026-09-07 11:20:12', equipmentId: 'EQ-004', equipmentName: 'John Deere Tractor 8R', tankId: 'Tank-01', volume: 60.0, operator: 'Sarah Jenkins', status: 'Completed' },
    { id: 'TXN-98423', timestamp: '2026-09-07 12:05:45', equipmentId: 'EQ-005', equipmentName: 'Toyota Hilux Service Truck', tankId: 'Tank-02', volume: 65.2, operator: 'Michael Corleone', status: 'Completed' },
    { id: 'TXN-98424', timestamp: '2026-09-07 12:45:00', equipmentId: 'EQ-003', equipmentName: 'Cummins Generator 250kVA', tankId: 'Tank-02', volume: 420.0, operator: 'Sarah Jenkins', status: 'Completed' }
  ]);

  const statuses = ref([
    { label: 'Completed', value: 'Completed' },
    { label: 'Pending', value: 'Pending' },
    { label: 'Voided', value: 'Voided' }
  ]);

  function getEquipmentById(id) {
    return equipments.value.find(e => e.id === id);
  }

  function getTankById(id) {
    return tanks.value.find(t => t.id === id); // ✅ fixed: was `e.id === id` (undefined var, ReferenceError)
  }

  return {
    equipments,
    tanks,
    transactions,
    statuses,
    getEquipmentById,
    getTankById
  };
}
```

> **Fixed bug:** the original `getTankById` referenced an undefined variable `e` instead of the loop parameter `t`. It wasn't caught because nothing in the current view/dialog actually calls `getTankById` or `getEquipmentById` — both components use inline `.find()` instead. Either call the helpers (to avoid duplicated lookup logic) or drop them until they're used, but don't leave broken dead code checked in.

---

## 4. Composable: `useDispensingForm.js`

```javascript
// src/views/fams/dispensing/useDispensingForm.js
import { ref, reactive } from 'vue';

export function useDispensingForm(lookups, onSuccessCallback) {
  const initialForm = {
    equipmentId: '',
    tankId: '',
    volume: null,
    operator: '',
    notes: ''
  };

  const form = reactive({ ...initialForm });
  const errors = ref({});
  const isSubmitting = ref(false);

  function validate() {
    const errs = {};
    if (!form.equipmentId) errs.equipmentId = 'Equipment selection is required.';
    if (!form.tankId) errs.tankId = 'Fuel Source Tank is required.';

    if (form.volume === null || form.volume === undefined) {
      errs.volume = 'Dispensed volume is required.';
    } else if (isNaN(form.volume) || form.volume <= 0) {
      errs.volume = 'Volume must be a positive number.';
    } else if (form.tankId) {
      const selectedTank = lookups.tanks.value.find(t => t.id === form.tankId);
      if (selectedTank && form.volume > selectedTank.currentLiters) {
        errs.volume = `Requested volume exceeds available tank level (${selectedTank.currentLiters} L).`;
      }
    }

    if (!form.operator || !form.operator.trim()) {
      errs.operator = 'Operator signature name is required.';
    }

    errors.value = errs;
    return Object.keys(errs).length === 0;
  }

  function resetForm() {
    Object.assign(form, initialForm);
    errors.value = {};
  }

  async function submitForm() {
    if (!validate()) return false;

    isSubmitting.value = true;
    try {
      // ⚠️ Mock delay — replace with DispensingService.create(payload) (see §5)
      await new Promise(resolve => setTimeout(resolve, 800));

      const newTxn = {
        id: `TXN-${Math.floor(10000 + Math.random() * 90000)}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        equipmentId: form.equipmentId,
        equipmentName: lookups.equipments.value.find(e => e.id === form.equipmentId)?.name || 'Unknown Equipment',
        tankId: form.tankId,
        volume: Number(form.volume),
        operator: form.operator.trim(),
        status: 'Completed'
      };

      // Local optimistic state mutation (stand-in for server-driven refresh)
      lookups.transactions.value.unshift(newTxn);

      const selectedTank = lookups.tanks.value.find(t => t.id === form.tankId);
      if (selectedTank) {
        selectedTank.currentLiters -= Number(form.volume);
      }

      const selectedEquipment = lookups.equipments.value.find(e => e.id === form.equipmentId);
      if (selectedEquipment) {
        selectedEquipment.currentLevel = Math.min(
          selectedEquipment.limitLiters,
          selectedEquipment.currentLevel + Number(form.volume)
        );
        selectedEquipment.lastFuelDate = newTxn.timestamp.substring(0, 10);
      }

      resetForm();
      if (onSuccessCallback) onSuccessCallback(newTxn);
      return true;
    } catch (err) {
      console.error('Dispensing submission failed:', err);
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  return { form, errors, isSubmitting, submitForm, resetForm };
}
```

**Validation pattern worth reusing:** the volume field has a three-tier check — presence, numeric/positive, then a *cross-field* check against the currently selected tank's live balance. This is the right place for business-rule validation that depends on more than one field (compare to fams-portal-master skill Part 2.5, which only covers single-field mistakes).

---

## 5. Known Gaps (Prototype → Production Checklist)

| Gap | Current State | Needed for Production |
|---|---|---|
| **Service layer** | `setTimeout` mock in `submitForm()` | Route through `DispensingService.create(payload)` per fams-portal-master skill Part 6 |
| **Data source** | Static `ref([...])` arrays | `EquipmentService.getAll()`, `TankService.getAll()` on mount |
| **Balance mutation** | Local optimistic mutation only | Server should own tank/equipment balance truth; refetch or reconcile after submit, don't just trust the local subtraction |
| **Dead code** | `getTankById`/`getEquipmentById` unused, one was broken | Either wire them in or remove until needed |
| **Void transaction** | `handleVoidTransaction` in `Dispensing.vue` mutates local array directly, no undo of tank/equipment balances | Voiding should reverse the balance mutation (add volume back to tank, subtract from equipment) or be handled server-side |
| **Overfill guard** | Equipment level is clamped with `Math.min(limitLiters, ...)` silently | Consider surfacing a warning/toast when a dispense is clamped, so the operator knows the full requested volume wasn't applied |

---

## 6. UI Pattern Notes (`Dispensing.vue`, `DispensingDialog.vev`)

- **Tank widgets** and **equipment cards** both compute their own percentage-based severity (`danger`/`warn`/`success`) inline in the template rather than via a shared composable — compare to `fams-tanks-business/SKILL.md`'s threshold matrix (95%/85%/15%/5%). This feature uses different, simpler cutoffs (20%/50%) for *equipment* fuel level, which is a distinct concept from *tank capacity* — don't conflate the two threshold sets when reusing code.
- **Equipment lockout**: clicking "Quick Dispense" on a `Maintenance`-status equipment is blocked client-side with a toast, not disabled entirely (the button stays visible but relabels to "Under Maintenance" and is `:disabled`). This is a reasonable UX pattern for status-gated actions — keep it, but remember client-side lockout is not a substitute for a server-side check.
- **Dialog visibility** uses the standard `computed({ get, set })` two-way binding against a boolean prop (`v-model:visible`) — this is the correct way to sync a prop without mutating it directly, consistent with the anti-mutation rule in fams-portal-master skill Part 9.1 / FAMS_fams-vue-core/SKILL.md Section 7.
- **Form reset on equipment change** uses a `watch(() => props.equipment, ..., { immediate: true })` to reset and pre-fill the form when a different equipment card triggers the dialog. This is the right tool here (side effect tied to a prop change, not a derived value) — a `computed` would be the wrong choice.

---

## Summary

**This skill covers:**
- ✅ Dialog-based quick-action form pattern (vs. Drawer-based entity editor)
- ✅ Cross-field validation tying dispensed volume to live tank balance
- ✅ Local balance-mutation-on-submit pattern (and its production gaps)
- ✅ A fixed bug (`getTankById`) and a checklist for mock-to-production hardening

**Reference with:**
- fams-portal-master skill Part 6 (Service Layer) — for wiring the real API calls
- fams-portal-master skill Part 8 (Feature Blueprint) — for how this deviates (Dialog vs Drawer)
- fams-tanks-business/SKILL.md — for tank capacity threshold conventions
- fams-vue-core/SKILL.md — for PrimeVue component and anti-pattern reference

**Next Review:** 2026-11-01
