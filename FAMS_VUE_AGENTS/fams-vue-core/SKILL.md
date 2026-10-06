---
name: fams-vue-core-specialized
description: Use when writing or reviewing a specific FAMS Vue 3 component — picking a PrimeVue 4 component (DataTable, Select, Drawer, ProgressBar, Tag, etc.), styling with Tailwind + PassThrough props, implementing dark mode, or building Pilot #1 dashboard cards (TankCard.vue, DeviceStatus.vue). Load alongside fams-portal-master for architecture context.
---

# FAMS Vue 3 Frontend Core Standards — Specialized Skill

## 📋 Metadata
| Field | Value |
|-------|-------|
| **VERSION** | 1.2.0 (PrimeVue 4 & Plain JavaScript) |
| **OWNER** | Product/UX Leader (Team 02), Frontend Leader (Team 03) |
| **STATUS** | ✅ VALID |
| **VALIDATED** | 2026-09-07 |
| **DEPENDENCIES** | fams-portal-master skill (Parts 1-4), `/src/FAMS.Web/`, PrimeVue 4, Tailwind CSS 4 |
| **TESTED** | Gemini Challenger Verified |
| **NEXT REVIEW** | 2026-11-01 |

---

## Quick Reference

**When to Use This Skill:**
- Building or refactoring Vue 3 components
- Implementing PrimeVue 4 UI elements
- Creating Pilot #1 dashboard cards (TankCard, DeviceStatus)
- Reviewing frontend code for anti-patterns
- Styling with Tailwind CSS + PrimeVue design tokens

**Don't Use This For:**
- Architecture/routing decisions (see fams-portal-master skill Part 5)
- State management patterns (see fams-portal-master skill Part 4)
- Backend API design (see FAMS_API_CORE-v2.md)

---

## 1. Framework & Technical Baseline

### Plain JavaScript Mandate
```
✅ Vue 3.4 Composition API with <script setup>
✅ PrimeVue 4 (styled mode, Lara preset)
✅ Tailwind CSS 4 (utility-first)
✅ Pinia 3 (global state)
✅ Axios (centralized client via apiService.js)

❌ NO TypeScript
❌ NO custom CSS scoping
❌ NO component wrappers
```

### Key Technologies
- **Vue 3.4**: Composition API, `<script setup>`, `defineModel()`
- **PrimeVue 4**: Design-token based theming, auto-import via unplugin-vue-components
- **Tailwind CSS 4**: CSS @layer integration, responsive utilities
- **Pinia 3**: Setup stores (recommended over options-style)
- **Axios**: Wrapped in centralized `apiService.js` with interceptors

---

## 2. Directory Structure & Feature Splitting

### Required Layout
```
src/
├── assets/              # styles.scss, tailwind.css, design tokens
├── components/          # Reusable UI elements
│   ├── dashboard/       # Dashboard-specific components
│   ├── shared/          # Tables, filters, inputs
│   └── pilot1/          # Pilot #1 components (TankCard, DeviceStatus)
├── composables/         # Global composables
├── layout/              # AppLayout, AppSidebar, AppTopbar
├── router/index.js      # ALL routes (children under /main)
├── service/
│   ├── apiService.js    # Centralized axios client
│   └── TankService.js   # Entity services
├── stores/              # Pinia stores
│   ├── authStore.js
│   └── tankStore.js
└── views/
    └── fams/
        └── <feature>/   # Each feature: main view + sidebar + composables
            ├── <Feature>.vue
            ├── <Feature>Sidebar.vue
            ├── use<Feature>Form.js
            ├── use<Feature>Lookups.js
            └── use<Feature>Payloads.js
```

### Feature-Module Split Rule (Critical)
1. **Never exceed 500 lines** in a single `.vue` file
2. **Keep markup focused** on layout/structure only
3. **Delegate logic** to composables (form state, validation, payload building)
4. **One feature folder** = complete domain responsibility

---

## 3. Vue 3 Reactivity Essentials

### ref() vs reactive() Decision

```javascript
// ✅ USE ref() FOR:
const count = ref(0);                    // Primitives
const items = ref([]);                   // Arrays
const user = ref({ id: 1, name: '' });   // Single objects

// ✅ USE reactive() FOR:
const formState = reactive({              // Complex nested objects
  user: { name: '', email: '' },
  address: { street: '', city: '' }
});

// ✅ USE computed() FOR:
const isFormValid = computed(() => {
  return formState.user.name && formState.user.email;
});

// ✅ USE shallowRef() FOR:
const hugeReadOnlyArray = shallowRef(veryLargeArray);
```

### Reactivity Preservation
```javascript
// ❌ WRONG: Destructuring breaks reactivity
const { name } = reactive({ name: 'John' });

// ✅ RIGHT: Use toRefs()
const { name } = toRefs(reactive({ name: 'John' }));
```

### Compiler Macros (Auto-Available)
```vue
<script setup>
// ✅ Automatically available (no import!)
const props = defineProps({ tank: Object });
const emit = defineEmits(['update', 'delete']);
const model = defineModel(); // Vue 3.4+

// ✅ Never use inside conditionals/loops/functions
// ✅ Only at top level of <script setup>
</script>
```

---

## 4. PrimeVue 4 & Tailwind CSS 4 Styling

### Core Rules
1. **Tailwind First**: Use utilities for layout, spacing, grid, flex
2. **No Custom CSS**: Never write scoped CSS or use `:deep()` selectors
3. **No !important**: Use PassThrough or design tokens instead
4. **Dark Mode**: Append `.app-dark` to root HTML element
5. **Icons**: Use PrimeIcons (`pi pi-check`) only

### PassThrough Styling
```vue
<template>
  <!-- Target internal PrimeVue elements -->
  <Button 
    label="Save" 
    pt:root:class="bg-blue-600 hover:bg-blue-700 rounded-lg px-6 py-3"
  />
  
  <!-- DataTable header styling -->
  <DataTable 
    :value="items" 
    pt:header:class="bg-blue-50 dark:bg-blue-900"
  >
    <Column field="name" header="Name" />
  </DataTable>
</template>
```

### Component Reference

| Need | Component | Example |
|------|-----------|---------|
| List with pagination | `DataTable` `:lazy="true"` | Server-side filtering |
| Text input | `InputText` | Form field |
| Date picker | `DatePicker` | Acquisition date |
| Dropdown | `Select` | Status selection |
| Boolean toggle | `ToggleSwitch` | Active/Inactive |
| Side panel form | `Drawer` | Create/Edit entity |
| Error display | `Message severity="error"` | Validation errors |
| Success notification | `Toast` via `useToast()` | Save confirmation |
| Confirmation dialog | `ConfirmDialog` via `useConfirm()` | Delete confirmation |

---

## 5. Pilot #1 Dashboard Components

### TankCard.vue (PrimeVue 4 + Plain JS)

**Purpose**: Visualize single tank volume, capacity bar, and status

```vue
<script setup>
import { computed } from 'vue';
import Card from 'primevue/card';
import ProgressBar from 'primevue/progressbar';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import Skeleton from 'primevue/skeleton';

const props = defineProps({
  tank: { type: Object, required: true },
  loading: { type: Boolean, default: false }
});

// Computed severity for visual feedback
const capacitySeverity = computed(() => {
  const pct = props.tank?.capacityPercentage || 0;
  if (pct >= 85) return 'warn';      // High fill
  if (pct <= 15) return 'danger';    // Low run-out
  return 'success';                   // Healthy
});

const communicationSeverity = computed(() => {
  switch (props.tank?.communicationStatus) {
    case 'Healthy': return 'success';
    case 'Warning': return 'warn';
    case 'Offline': return 'danger';
    default: return 'info';
  }
});
</script>

<template>
  <Card class="shadow-sm border border-slate-200 dark:border-slate-700">
    <!-- Header with Title & Status Badge -->
    <template #header>
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-800">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
          {{ tank.name || `Tank ${tank.id}` }}
        </h3>
        <Tag 
          :value="tank.communicationStatus || 'Unknown'" 
          :severity="communicationSeverity" 
        />
      </div>
    </template>

    <!-- Body: Volume & Progress Bar -->
    <template #content>
      <div v-if="loading" class="space-y-2">
        <Skeleton width="100%" height="0.5rem" />
      </div>
      <div v-else class="space-y-4">
        <!-- Volume Display -->
        <div class="flex items-baseline space-x-1">
          <span class="text-3xl font-extrabold text-slate-900 dark:text-white">
            {{ tank.currentVolume?.toLocaleString(undefined, { 
              minimumFractionDigits: 1, 
              maximumFractionDigits: 1 
            }) }}
          </span>
          <span class="text-sm font-semibold text-slate-500 dark:text-slate-400">Liters</span>
        </div>

        <!-- Capacity Progress Bar -->
        <ProgressBar 
          :value="tank.capacityPercentage" 
          class="h-2 rounded-full"
          :class="[
            capacitySeverity === 'danger' ? 'bg-red-100' :
            capacitySeverity === 'warn' ? 'bg-amber-100' : 
            'bg-emerald-100'
          ]"
        />

        <!-- Capacity Percentage -->
        <div class="text-right text-sm font-medium text-slate-600 dark:text-slate-400">
          {{ tank.capacityPercentage?.toFixed(1) || 0 }}%
        </div>
      </div>
    </template>

    <!-- Footer: Warnings -->
    <template #footer>
      <div v-if="loading" class="pt-2">
        <Skeleton width="100%" height="2rem" />
      </div>
      <div v-else-if="tank.simpleWarning" class="pt-2">
        <Message 
          severity="error" 
          :closable="false" 
          class="m-0 text-xs font-medium"
        >
          <span class="font-bold">⚠️</span> {{ tank.simpleWarning }}
        </Message>
      </div>
    </template>
  </Card>
</template>
```

### DeviceStatus.vue (PrimeVue 4 + Plain JS)

**Purpose**: Display hardware telemetry metadata (device ID, protocol, latency)

```vue
<script setup>
import { computed } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';

const props = defineProps({
  metadata: { type: Object, required: true },
  status: { type: String, required: true }
});

const statusBorderClass = computed(() => {
  const classes = {
    'Healthy': 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/50',
    'Warning': 'border-amber-200 dark:border-amber-800 bg-amber-50/50',
    'Critical': 'border-red-200 dark:border-red-800 bg-red-50/50',
    'Offline': 'border-red-200 dark:border-red-800 bg-red-50/50'
  };
  return classes[props.status] || 'border-slate-200 dark:border-slate-800 bg-slate-50/50';
});
</script>

<template>
  <div class="border rounded-xl p-4 shadow-sm space-y-3 font-mono text-xs" :class="statusBorderClass">
    <!-- Header -->
    <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
      <span class="font-bold text-slate-700 dark:text-slate-300">Device Telemetry</span>
      <Tag 
        :value="metadata.isSimulated ? 'EMULATED' : 'HARDWARE'" 
        :severity="metadata.isSimulated ? 'warn' : 'info'" 
        class="text-[10px]"
      />
    </div>

    <!-- Diagnostic Grid -->
    <div class="grid grid-cols-2 gap-3 text-slate-600 dark:text-slate-400">
      <div>
        <div class="text-[11px]">Device ID</div>
        <div class="font-semibold text-slate-900 dark:text-white">{{ metadata.deviceId }}</div>
      </div>
      <div>
        <div class="text-[11px]">Protocol</div>
        <div class="font-semibold text-slate-900 dark:text-white">{{ metadata.protocol }}</div>
      </div>
      <div>
        <div class="text-[11px]">Sensor Type</div>
        <div class="font-semibold text-slate-900 dark:text-white">{{ metadata.sensorType }}</div>
      </div>
      <div>
        <div class="text-[11px]">Read Latency</div>
        <div 
          class="font-semibold"
          :class="metadata.readLatencyMs > 500 ? 'text-amber-500' : 'text-slate-900 dark:text-white'"
        >
          {{ metadata.readLatencyMs }}ms
        </div>
      </div>
    </div>
  </div>
</template>
```

---

## 6. State Management & Pinia Stores

### Tank Store Example

```javascript
// src/stores/tankStore.js
import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { TankService } from '@/service/TankService';

export const useTankStore = defineStore('tank', () => {
  // State
  const tanks = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  // Computed
  const healthyTanks = computed(() =>
    tanks.value.filter(t => t.communicationStatus === 'Healthy')
  );

  const warningTanks = computed(() =>
    tanks.value.filter(t => 
      t.communicationStatus === 'Warning' || 
      t.capacityPercentage >= 85 || 
      t.capacityPercentage <= 15
    )
  );

  // Actions
  async function fetchTanks() {
    isLoading.value = true;
    try {
      const response = await TankService.getAll();
      tanks.value = response.data || [];
    } catch (err) {
      error.value = err.message;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateTank(id, payload) {
    try {
      const response = await TankService.update(id, payload);
      const idx = tanks.value.findIndex(t => t.id === id);
      if (idx !== -1) tanks.value[idx] = response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  }

  return {
    tanks, isLoading, error, healthyTanks, warningTanks,
    fetchTanks, updateTank
  };
});
```

---

## 7. Code Review Anti-Patterns (PR Rejection Checklist)

| Anti-Pattern | Why Bad | Fix |
|--------------|---------|-----|
| TypeScript usage | Plain JS mandate | Remove all `.ts` files |
| Prop mutation | Breaks one-way data flow | Use `defineModel()` or emit events |
| Ad-hoc axios | Bypasses error handling | Route through `apiService.js` |
| Monolithic components | Hard to maintain & test | Split per feature-module rule |
| Watcher abuse | Performance issues | Convert to `computed()` |
| Direct DOM manipulation | Breaks reactivity | Use Vue refs + templates |
| Custom scoped CSS | Conflicts with Tailwind | Use PassThrough props |
| Missing error handling | Poor UX | Wrap async calls in try/catch |

---

## Summary

**This skill covers:**
- ✅ Vue 3 Composition API patterns
- ✅ PrimeVue 4 component usage
- ✅ Tailwind CSS integration
- ✅ Pilot #1 dashboard components (TankCard, DeviceStatus)
- ✅ Pinia state management
- ✅ Code review anti-patterns

**Reference with:**
- fams-portal-master skill Part 2 (Vue 3 Reactivity)
- fams-portal-master skill Part 3 (PrimeVue Components)
- fams-portal-master skill Part 4 (Pinia Stores)

**Next Review:** 2026-11-01
