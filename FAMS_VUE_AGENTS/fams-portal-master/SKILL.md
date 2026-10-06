---
name: fams-portal-developer
description: Use for ANY FAMS Portal frontend work — creating a new feature/view/route, deciding file structure, ref vs reactive vs computed vs watch questions, Pinia store setup, Vue Router registration, API service layer/apiService.js calls, PrimeVue+Tailwind styling, or code review against the anti-patterns and pre-commit checklist. This is the default skill to load first for FAMS-UI (Vue 3 + PrimeVue 4 + Pinia 3 + Tailwind CSS 4) tasks; load the specialized skills (fams-vue-core, fams-tanks-business, fams-atg-communications, fams-dispensing) alongside it for domain-specific depth.
---

# FAMS Portal — Master Developer Skill

## Executive Summary

The FAMS Portal is a **modern, secure, highly responsive Single Page Application (SPA)** designed to serve internal and external stakeholders tracking asset utilization, managing lifecycle states, running depreciation schedules, and configuring system workflows.

This skill consolidates all development standards, reactive patterns, component architecture, and implementation blueprints for the FAMS Portal ecosystem.

---

# PART 1: CORE ARCHITECTURE & TECH STACK

## 1.1 Technology Stack

All frontend development must strictly adhere to these parameters:

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| **Core Framework** | Vue 3 | 3.4 | Composition API + `<script setup>` |
| **Language** | JavaScript (Plain) | ES2022 | No TypeScript — configured via `jsconfig.json` |
| **Build Tooling** | Vite | 5.x | Lightning-fast HMR + optimized Rollup builds |
| **UI Component Library** | PrimeVue | 4.x | Styled mode, Lara preset, `@primeuix/themes` design tokens |
| **Styling & Utilities** | Tailwind CSS | 4.x | Utility-first, CSS layer integration with PrimeVue |
| **State Management** | Pinia | 3.x | Setup stores for cross-feature global state |
| **Routing** | Vue Router | 4.x | Client-side navigation, nested routes under `/main` |
| **HTTP Client** | Axios | Latest | Centralized via `apiService.js` with auto-error toasts |

**Key Principles:**
- **Production-Ready Velocity**: Clean, low-ceremony Composition API
- **Accessibility First**: WCAG-compliant design via PrimeVue components
- **Performance at Scale**: Route-level lazy loading, efficient DataTable rendering
- **Cohesive Design System**: Design tokens + Tailwind utilities + PrimeVue styling

---

## 1.2 Directory Structure

Organize all code strictly by domain. No monolithic god components.

```
FAMS-UI/
├── src/
│   ├── assets/
│   │   ├── styles.scss            # Global styles and variables
│   │   ├── tailwind.css           # Tailwind directives
│   │   └── layout/
│   │       ├── theme/
│   │       │   ├── light.scss     # Light mode tokens
│   │       │   ├── dark.scss      # Dark mode tokens
│   │       │   └── primary.scss   # Primary color overrides
│   │       └── _fams_sidebar_theme.scss # Custom sidebar styling
│   │
│   ├── components/
│   │   ├── dashboard/             # Dashboard widgets
│   │   ├── landing/               # Landing page components
│   │   └── shared/                # Reusable UI bits (ColumnFilterBar.vue)
│   │
│   ├── composables/
│   │   ├── useColumnFilters.js    # Cross-feature filter logic
│   │   ├── useSearch.js           # Debounced search patterns
│   │   └── ... (other global composables)
│   │
│   ├── layout/
│   │   ├── AppLayout.vue          # Main shell (sidebar + topbar + content)
│   │   ├── AppSidebar.vue         # Left navigation
│   │   ├── AppTopbar.vue          # Header bar
│   │   ├── AppMenu.vue            # Menu items
│   │   ├── AppBreadcrumb.vue      # Breadcrumb navigation
│   │   ├── AppFooter.vue          # Footer
│   │   └── AppConfig.vue          # Theme/language settings
│   │
│   ├── router/
│   │   └── index.js               # ✅ SINGLE router file (ALL routes here)
│   │
│   ├── service/
│   │   ├── apiService.js          # Centralized Axios client + error toasts
│   │   ├── AssetService.js        # Entity-specific services
│   │   ├── OperatorService.js
│   │   ├── EquipmentService.js
│   │   └── ... (one service per entity)
│   │
│   ├── stores/
│   │   ├── authStore.js           # Auth session, roles, portals (Pinia)
│   │   ├── portalStore.js         # Multi-tenant portal context
│   │   ├── roleAccess.js          # Pure helper functions for role logic
│   │   └── ... (other feature stores)
│   │
│   ├── views/
│   │   ├── pages/
│   │   │   └── auth/
│   │   │       ├── Login.vue
│   │   │       ├── Register.vue
│   │   │       ├── ForgotPassword.vue
│   │   │       ├── LockScreen.vue
│   │   │       ├── AccessDenied.vue
│   │   │       ├── Error.vue
│   │   │       └── ... (auth pages)
│   │   │
│   │   ├── dashboards/            # Dashboard views
│   │   │
│   │   ├── apps/
│   │   │   ├── cms/
│   │   │   ├── chat/
│   │   │   ├── mail/
│   │   │   └── tasklist/
│   │   │
│   │   └── fams/                  # ✅ FAMS DOMAIN FEATURES (Main business logic)
│   │       ├── dashboard/
│   │       │   ├── Dashboard.vue
│   │       │   └── useDashboardData.js
│   │       │
│   │       ├── assets/            # Example feature module
│   │       │   ├── Assets.vue                  # Main list/page
│   │       │   ├── AssetsSidebar.vue          # Create/edit drawer
│   │       │   ├── useAssetsForm.js           # Form state + methods
│   │       │   ├── useAssetsLookups.js        # Dropdown/select data
│   │       │   └── useAssetsPayloads.js       # Build API DTOs
│   │       │
│   │       ├── operators/         # Another feature module
│   │       │   ├── Operators.vue
│   │       │   ├── OperatorsSidebar.vue
│   │       │   ├── useOperatorsForm.js
│   │       │   ├── useOperatorsLookups.js
│   │       │   └── useOperatorsPayloads.js
│   │       │
│   │       ├── equipment/
│   │       │   ├── Equipment.vue
│   │       │   ├── EquipmentSidebar.vue
│   │       │   ├── useEquipmentForm.js
│   │       │   ├── useEquipmentLookups.js
│   │       │   └── useEquipmentPayloads.js
│   │       │
│   │       ├── workflows/         # Lifecycle diagrams
│   │       │   ├── Workflows.vue
│   │       │   └── useWorkflowNodes.js
│   │       │
│   │       └── reports/           # Reporting & analytics
│   │           ├── Reports.vue
│   │           └── useReportData.js
│   │
│   ├── App.vue
│   └── main.js                    # Bootstrap: Vite, Vue, PrimeVue, Pinia, Router
│
├── index.html                     # Vite entry point
├── vite.config.mjs                # Vite configuration + auto-import resolvers
├── jsconfig.json                  # JS path aliases (@/ → ./src/)
├── .eslintrc.cjs                  # ESLint rules for Vue 3
├── .env.development               # Dev env: VITE_ROOT_API
├── .env.production                # Prod env: VITE_ROOT_API
├── tailwind.config.js             # Tailwind configuration
└── package.json
```

---

## 1.3 The Feature-Module Split Principle

**Every FAMS feature under `src/views/fams/<feature>/` must follow this pattern:**

### Structure
```
assets/
├── Assets.vue                  # Main page: list view, pagination, filtering
├── AssetsSidebar.vue          # Form drawer: create/edit/view
├── useAssetsForm.js           # Reactive form state + validation + submit
├── useAssetsLookups.js        # Dropdown options (departments, categories)
└── useAssetsPayloads.js       # Transform form state → API request DTOs
```

### Rules
1. **Never merge components** — each file has a single responsibility
2. **Page handles**: List view, filters, pagination, data binding
3. **Sidebar handles**: Form UI, input bindings, submit/cancel buttons
4. **Composables handle**: State, validation, payload building (100% reusable)
5. **Service handles**: API calls only (via centralized `apiClient`)

---

# PART 2: VUE 3 REACTIVITY PATTERNS

## 2.1 Reactivity Fundamentals: `ref()` vs `reactive()`

**Decision Tree:**

| Scenario | Use `ref()` | Use `reactive()` | Why |
|----------|-----------|-----------------|-----|
| Single primitive (string, number, boolean) | ✅ | ❌ | ref handles `.value` proxy automatically |
| Single object | ✅ preferred | ✅ ok | Both work; ref allows reassignment |
| Form data (fields mutated individually) | ✅ preferred | ✅ ok | ref: clearer tracking per field |
| Deep nested structure (frequent mutations) | ❌ | ✅ | reactive: direct property mutation |
| Need to reassign entire value | ✅ | ❌ | reactive() breaks on wholesale reassign |
| Array of objects | ✅ | ✅ | Either works; ref for clarity |
| Pinia store state | ✅ preferred | ✅ | Both valid; setup stores prefer ref |

### Example: FAMS Form State

```javascript
// ✅ RECOMMENDED: Per-field reactivity with ref/reactive
const formData = reactive({
  name: '',
  serialNumber: '',
  purchasePrice: null,
  status: 'ACTIVE',
  tags: [],
  parameters: {}
});

const formErrors = reactive({
  name: '',
  serialNumber: '',
  purchasePrice: ''
});

// Alternate: Individual refs
const name = ref('');
const serialNumber = ref('');
const purchasePrice = ref(null);

// ❌ AVOID: Reassigning reactive() object
let state = reactive({ count: 0 });
state = { count: 1 }; // ❌ BREAKS REACTIVITY — this is now a plain object
```

### Vue 3 Reactivity Gotchas (Now FIXED)

**Vue 3 automatically handles what Vue 2 needed `Vue.set()` for:**

```javascript
// ✅ Vue 3: Direct assignment works (no $set needed)
const equipment = reactive({ name: 'Tank 1' });
equipment.newProperty = 'value'; // Reactive!

// ✅ Array mutations work directly
const items = ref([]);
items.value[0] = newItem; // Reactive!
items.value.length = 5;   // Reactive!

// ❌ Never needed in Vue 3:
// Vue.set(obj, key, value)  — just use direct assignment
// this.$set(obj, key, value) — gone in Vue 3
```

---

## 2.2 Compiler Macros in `<script setup>`

Three compiler macros are **automatically available** (do not import them):

```javascript
// ✅ defineProps — declare input props
const props = defineProps({
  modelValue: String,
  disabled: Boolean
});

// ✅ defineEmits — declare output events
const emit = defineEmits(['update:modelValue', 'submit']);

// ✅ defineModel (Vue 3.4+) — two-way binding helper
const model = defineModel(); // Creates modelValue prop + update:modelValue emit
```

**Rules:**
- Never call them inside conditionals, loops, or functions
- Always at the top level of `<script setup>`
- No explicit import needed

---

## 2.3 ref vs reactive vs computed vs watch

### When to Use Each

```javascript
import { ref, reactive, computed, watch, watchEffect } from 'vue';

// ✅ ref: Single values or objects with potential reassignment
const count = ref(0);
const items = ref([]);

// ✅ reactive: Complex nested objects (mutate in place)
const formData = reactive({
  user: { name: '', email: '' },
  settings: { theme: 'light', lang: 'en' }
});

// ✅ computed: Derived, read-only values (auto-cached)
const activeItems = computed(() =>
  items.value.filter(i => i.active)
);

// ✅ watch: Side effects (API calls, localStorage, emits)
watch(
  () => formData.status,
  async (newStatus) => {
    await saveStatus(newStatus);
  }
);

// ✅ watchEffect: Simple side effects (track deps automatically)
watchEffect(() => {
  localStorage.setItem('filters', JSON.stringify(filters.value));
});
```

### The Golden Rule

| Need | Tool | Example |
|------|------|---------|
| Display value | `computed()` | Filter, format, sum array |
| Side effect (save, emit, API) | `watch()` or `watchEffect()` | Debounce search, track changes |
| Local state | `ref()` | Form field, loading flag |
| Cross-component state | `ref()` in Pinia store | Auth session, portal config |

---

## 2.4 Advanced Reactivity Patterns for Forms

### Pattern 1: Form Composable with Validation

```javascript
// src/views/fams/assets/useAssetForm.js
import { ref, reactive, computed } from 'vue';
import { AssetService } from '@/service/AssetService';

export function useAssetForm() {
  // Reactive form state
  const formData = reactive({
    id: null,
    name: '',
    serialNumber: '',
    purchasePrice: null,
    purchaseDate: null,
    categoryId: null
  });

  const formErrors = reactive({
    name: '',
    serialNumber: '',
    purchasePrice: ''
  });

  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const isSidebarOpen = ref(false);

  // Computed validity
  const isFormValid = computed(() => {
    return formData.name.trim() && 
           formData.serialNumber.trim() && 
           formData.purchasePrice > 0;
  });

  // Validation method
  function validateForm() {
    let valid = true;

    if (!formData.name.trim()) {
      formErrors.name = 'Asset Name is required.';
      valid = false;
    } else {
      formErrors.name = '';
    }

    if (!formData.serialNumber.trim()) {
      formErrors.serialNumber = 'Serial Number is required.';
      valid = false;
    } else {
      formErrors.serialNumber = '';
    }

    if (formData.purchasePrice === null || formData.purchasePrice <= 0) {
      formErrors.purchasePrice = 'Purchase price must be > 0.';
      valid = false;
    } else {
      formErrors.purchasePrice = '';
    }

    return valid;
  }

  // Reset form
  function resetForm() {
    Object.assign(formData, {
      id: null,
      name: '',
      serialNumber: '',
      purchasePrice: null,
      purchaseDate: null,
      categoryId: null
    });
    Object.assign(formErrors, {
      name: '', serialNumber: '', purchasePrice: ''
    });
  }

  // Load existing asset for edit
  async function loadAsset(assetId) {
    isLoading.value = true;
    try {
      const asset = await AssetService.getById(assetId);
      Object.assign(formData, asset);
    } catch (error) {
      formErrors.name = 'Failed to load asset.';
    } finally {
      isLoading.value = false;
    }
  }

  // Submit (create or update)
  async function submitForm() {
    if (!validateForm()) return;

    isSubmitting.value = true;
    try {
      const payload = buildAssetPayload(formData); // From useAssetPayloads
      
      if (formData.id) {
        await AssetService.updateAsset(formData.id, payload);
      } else {
        await AssetService.createAsset(payload);
      }

      resetForm();
      isSidebarOpen.value = false;
    } catch (error) {
      formErrors.name = error.message || 'Submission failed.';
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    formData,
    formErrors,
    isLoading,
    isSubmitting,
    isSidebarOpen,
    isFormValid,
    validateForm,
    resetForm,
    loadAsset,
    submitForm
  };
}
```

### Pattern 2: Filtered & Paginated List (Composable or Pinia)

```javascript
// In component setup or Pinia store
const items = ref([]);
const filters = reactive({
  search: '',
  status: null,
  categoryId: null
});
const page = ref(1);
const pageSize = ref(10);
const totalCount = ref(0);

// ✅ Derived state with computed (auto-cached)
const filteredItems = computed(() => {
  return items.value.filter(item => {
    if (filters.search && !item.name.includes(filters.search)) return false;
    if (filters.status && item.status !== filters.status) return false;
    if (filters.categoryId && item.categoryId !== filters.categoryId) return false;
    return true;
  });
});

// Paginated results
const paginatedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filteredItems.value.slice(start, start + pageSize.value);
});

// Total pages
const totalPages = computed(() => {
  return Math.ceil(filteredItems.value.length / pageSize.value);
});

// When filter changes, reset to page 1
watch(() => [filters.search, filters.status, filters.categoryId], () => {
  page.value = 1;
});
```

---

## 2.5 Common Reactive Mistakes & Fixes

| Mistake | Problem | Fix |
|---------|---------|-----|
| `const state = reactive({...}); state = {...}` | Breaks reactivity on reassign | Use `ref` or `Object.assign(state, newVal)` |
| `const { item } = reactive({ item: {} })` | Destructuring loses reactivity | Use `toRefs(state)` or access via state.item |
| `watch(obj, fn, { deep: false })` | Nested changes don't trigger | Add `{ deep: true }` |
| `computed(() => { apiCall() })` | Side effects in computed | Move to `watch()` or `watchEffect()` |
| `v-model on computed` | Double-binding issues | Use `defineModel()` or getter/setter computed |
| Mutating props directly | Violates one-way flow | Emit update event or use `defineModel()` |

---

# PART 3: PRIMEVUE 4 & TAILWIND INTEGRATION

## 3.1 PrimeVue 4 Component Mapping

### DataTable (Grid/List Display)

```vue
<DataTable
  :value="items"
  :loading="isLoading"
  :lazy="true"
  :paginator="true"
  :first="(page - 1) * pageSize"
  :rows="pageSize"
  :totalRecords="totalItems"
  stripedRows
  rowHover
  responsiveLayout="scroll"
  @page="onPage"
  @sort="onSort"
  @filter="onFilter"
>
  <Column field="name" header="Name" sortable filter />
  <Column field="status" header="Status" sortable filter />
  <Column header="Actions">
    <template #body="{ data }">
      <Button icon="pi pi-pencil" @click="onEdit(data)" />
      <Button icon="pi pi-trash" @click="onDelete(data.id)" />
    </template>
  </Column>
</DataTable>
```

**Key Attributes:**
- `:lazy="true"` — server-side pagination (emit events instead of loading all data)
- `:stripedRows="true"` — alternating row colors
- `:rowHover="true"` — highlight row on hover
- `sortable` on Column — enable sorting
- `filter` on Column — enable filtering

### Form Inputs

```vue
<!-- Text -->
<InputText
  v-model="formData.name"
  placeholder="Enter name"
  :class="{ 'ng-invalid': formErrors.name }"
/>

<!-- Textarea -->
<Textarea v-model="formData.description" />

<!-- Number -->
<InputNumber
  v-model="formData.purchasePrice"
  mode="currency"
  currency="USD"
/>

<!-- Date -->
<DatePicker
  v-model="formData.purchaseDate"
  dateFormat="yy-mm-dd"
  placeholder="Select date"
/>

<!-- Select (Dropdown) -->
<Select
  v-model="formData.categoryId"
  :options="categories"
  optionLabel="name"
  optionValue="id"
  placeholder="Choose category"
/>

<!-- MultiSelect -->
<MultiSelect
  v-model="formData.tags"
  :options="availableTags"
  optionLabel="name"
  optionValue="id"
  placeholder="Select tags"
  filter
/>

<!-- Toggle (Boolean) -->
<ToggleSwitch
  v-model="formData.isActive"
/>

<!-- Checkbox -->
<Checkbox
  v-model="formData.agreed"
  binary
/>

<!-- RadioButton -->
<div class="flex gap-4">
  <RadioButton v-model="formData.status" value="ACTIVE" />
  <RadioButton v-model="formData.status" value="INACTIVE" />
</div>
```

### Overlays & Dialogs

```vue
<!-- Drawer (Sidebar) for forms -->
<Drawer
  v-model:visible="isSidebarOpen"
  header="Create Asset"
  :modal="true"
  :blockScroll="true"
  @hide="onClose"
>
  <!-- Form content here -->
</Drawer>

<!-- Dialog (Modal) -->
<Dialog
  v-model:visible="isDialogOpen"
  header="Confirm Delete"
  modal
>
  <p>Are you sure?</p>
  <template #footer>
    <Button label="Cancel" @click="isDialogOpen = false" />
    <Button label="Delete" severity="danger" @click="confirmDelete" />
  </template>
</Dialog>

<!-- Confirmation Service -->
<script setup>
import { useConfirm } from 'primevue/useconfirm';

const confirm = useConfirm();

const onDelete = (id) => {
  confirm.require({
    message: 'Are you sure you want to delete this asset?',
    header: 'Confirm',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      await deleteAsset(id);
    }
  });
};
</script>
```

### Messages & Feedback

```vue
<!-- Error Message -->
<Message
  v-if="formErrors.name"
  severity="error"
  :text="formErrors.name"
/>

<!-- Success Toast -->
<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const onSuccess = () => {
  toast.add({
    severity: 'success',
    summary: 'Success',
    detail: 'Asset created successfully',
    life: 3000
  });
};
</script>

<!-- Loading Spinner -->
<ProgressSpinner v-if="isLoading" />
```

### Navigation

```vue
<!-- Breadcrumb -->
<Breadcrumb :model="breadcrumbItems" />

<!-- Tabs -->
<Tabs value="tab1">
  <TabList>
    <Tab value="tab1">Active</Tab>
    <Tab value="tab2">Archived</Tab>
  </TabList>
  <TabPanel value="tab1">
    <!-- Content for Active tab -->
  </TabPanel>
  <TabPanel value="tab2">
    <!-- Content for Archived tab -->
  </TabPanel>
</Tabs>

<!-- Accordion -->
<Accordion>
  <AccordionTab header="Section 1">
    Content here
  </AccordionTab>
  <AccordionTab header="Section 2">
    Content here
  </AccordionTab>
</Accordion>
```

---

## 3.2 Styling with Tailwind & PassThrough

### Tailwind Utility Classes

```vue
<div class="p-6 space-y-4">
  <div class="mb-4 flex items-center justify-between">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Assets</h1>
    <Button label="Add Asset" />
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <Card v-for="asset in assets" :key="asset.id" class="shadow-md">
      <template #title>{{ asset.name }}</template>
      <p class="text-sm text-gray-600">{{ asset.status }}</p>
    </Card>
  </div>
</div>
```

**Common Tailwind Classes:**
- **Spacing**: `p-4` (padding), `m-2` (margin), `gap-4` (gap)
- **Typography**: `text-lg`, `font-bold`, `text-gray-900`
- **Flexbox**: `flex`, `items-center`, `justify-between`
- **Grid**: `grid`, `grid-cols-3`, `gap-4`
- **Colors**: `bg-blue-600`, `text-white`, `border-gray-300`
- **Responsive**: `md:`, `lg:`, `xl:` prefixes

### PrimeVue PassThrough (pt Prop)

```vue
<!-- Target internal elements of PrimeVue components -->
<Button
  label="Save"
  pt:root:class="bg-green-600 hover:bg-green-700 text-white rounded-lg px-6 py-3"
/>

<!-- Data Table header styling -->
<DataTable
  :value="items"
  pt:header:class="bg-blue-50 dark:bg-blue-900"
  pt:column:header:class="font-semibold text-blue-900"
>
  <Column field="name" header="Name" />
</DataTable>

<!-- Form input error state -->
<InputText
  v-model="formData.name"
  :pt="{
    root: {
      class: formErrors.name ? 'border-red-500 focus:border-red-500' : ''
    }
  }"
/>
```

---

## 3.3 Dark Mode

Dark mode is controlled via the `.app-dark` class on the root HTML element:

```javascript
// In main.js or a theme composable
const toggleDarkMode = () => {
  const html = document.documentElement;
  html.classList.toggle('app-dark');
  localStorage.setItem('theme', html.classList.contains('app-dark') ? 'dark' : 'light');
};
```

PrimeVue automatically responds to the `.app-dark` class (configured during setup via `darkModeSelector`).

---

# PART 4: PINIA STATE MANAGEMENT

## 4.1 Setup Store Pattern

```javascript
// src/stores/portalStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const usePortalStore = defineStore('portal', () => {
  // ─────────────────────────────────────
  // State
  // ─────────────────────────────────────
  const currentPortal = ref(null); // { id, name, type, features }
  const currentUser = ref(null);
  const isLoading = ref(false);

  // ─────────────────────────────────────
  // Computed (derived state)
  // ─────────────────────────────────────
  const isPortalLoaded = computed(() => !!currentPortal.value);

  const userPermissions = computed(() => {
    return currentUser.value?.permissions || [];
  });

  const hasFeature = (featureName) => {
    return currentPortal.value?.features?.includes(featureName) || false;
  };

  const hasPermission = (permission) => {
    return userPermissions.value.includes(permission);
  };

  // ─────────────────────────────────────
  // Actions (mutations + side effects)
  // ─────────────────────────────────────
  function setPortal(portal) {
    currentPortal.value = portal;
  }

  function setCurrentUser(user) {
    currentUser.value = user;
  }

  async function loadPortalContext(portalId) {
    isLoading.value = true;
    try {
      const response = await PortalService.getContext(portalId);
      setPortal(response.portal);
      setCurrentUser(response.user);
    } finally {
      isLoading.value = false;
    }
  }

  function logout() {
    currentPortal.value = null;
    currentUser.value = null;
  }

  // ─────────────────────────────────────
  // Return public API
  // ─────────────────────────────────────
  return {
    // State
    currentPortal,
    currentUser,
    isLoading,
    
    // Computed
    isPortalLoaded,
    userPermissions,
    
    // Methods
    setPortal,
    setCurrentUser,
    loadPortalContext,
    logout,
    hasFeature,
    hasPermission
  };
});
```

## 4.2 Using the Store in Components

```vue
<script setup>
import { onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { usePortalStore } from '@/stores/portalStore';

const portalStore = usePortalStore();

// Destructure with storeToRefs to maintain reactivity
const { currentPortal, isLoading } = storeToRefs(portalStore);

// Methods don't need storeToRefs
const { loadPortalContext } = portalStore;

onMounted(() => {
  loadPortalContext('fams-main');
});
</script>

<template>
  <div v-if="isLoading" class="p-4">Loading...</div>
  <div v-else-if="currentPortal">
    <h1>{{ currentPortal.name }}</h1>
  </div>
</template>
```

---

## 4.3 Entity Store Pattern

```javascript
// src/stores/assetStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { AssetService } from '@/service/AssetService';

export const useAssetStore = defineStore('asset', () => {
  // State
  const items = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  const filters = reactive({
    status: null,
    categoryId: null,
    search: ''
  });

  const pagination = reactive({
    page: 1,
    pageSize: 10,
    total: 0
  });

  // Computed
  const filteredItems = computed(() => {
    return items.value.filter(item => {
      if (filters.status && item.status !== filters.status) return false;
      if (filters.categoryId && item.categoryId !== filters.categoryId) return false;
      if (filters.search && !item.name.includes(filters.search)) return false;
      return true;
    });
  });

  const paginatedItems = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize;
    return filteredItems.value.slice(start, start + pagination.pageSize);
  });

  const totalPages = computed(() => {
    return Math.ceil(filteredItems.value.length / pagination.pageSize);
  });

  // Actions
  async function fetchAssets() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await AssetService.getAssets();
      items.value = response.data || [];
      pagination.total = items.value.length;
    } catch (err) {
      error.value = err.message;
    } finally {
      isLoading.value = false;
    }
  }

  async function createAsset(payload) {
    try {
      const response = await AssetService.createAsset(payload);
      items.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  }

  async function updateAsset(id, payload) {
    try {
      const response = await AssetService.updateAsset(id, payload);
      const idx = items.value.findIndex(i => i.id === id);
      if (idx !== -1) {
        items.value[idx] = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  }

  async function deleteAsset(id) {
    try {
      await AssetService.deleteAsset(id);
      items.value = items.value.filter(i => i.id !== id);
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  }

  function setFilter(key, value) {
    filters[key] = value;
    pagination.page = 1; // Reset on filter change
  }

  function setPage(newPage) {
    pagination.page = newPage;
  }

  return {
    items, isLoading, error, filters, pagination,
    filteredItems, paginatedItems, totalPages,
    fetchAssets, createAsset, updateAsset, deleteAsset,
    setFilter, setPage
  };
});
```

---

## 4.4 Store Best Practices

| Practice | Reason |
|----------|--------|
| Keep stores focused on ONE domain concern | Avoid one giant store with everything |
| Use `setup()` function syntax for new stores | More modern, composable-friendly |
| Extract complex logic to sibling utilities (roleAccess.js) | Keep store thin, logic testable |
| Use `storeToRefs()` when destructuring | Maintains reactivity |
| Don't store local UI state (sidebar open) | Use component `ref` instead |
| Actions mutate state directly (no mutations object) | Simpler than Vuex |

---

# PART 5: ROUTING & AUTHENTICATION

## 5.1 Route Registration

**All routes must nest under `/main` parent to inherit layouts and auth guard:**

```javascript
// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import AppLayout from '@/layout/AppLayout.vue';

const routes = [
  {
    path: '/',
    redirect: '/main/dashboard'
  },

  // Auth routes (outside /main)
  {
    path: '/login',
    component: () => import('@/views/pages/auth/Login.vue'),
    meta: { requiresAuth: false }
  },

  // Main app routes (under /main parent)
  {
    path: '/main',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/fams/dashboard/Dashboard.vue'),
        meta: {
          breadcrumb: [{ label: 'Dashboard' }],
          roles: ['ADMIN', 'USER'],
          portal: 'ALL'
        }
      },

      {
        path: 'assets',
        name: 'assets',
        component: () => import('@/views/fams/assets/Assets.vue'),
        meta: {
          breadcrumb: [{ label: 'FAMS' }, { label: 'Asset Register' }],
          roles: ['ADMIN', 'ASSET_MANAGER'],
          portal: 'fams-main',
          requiresAuth: true
        }
      },

      {
        path: 'operators',
        name: 'operators',
        component: () => import('@/views/fams/operators/Operators.vue'),
        meta: {
          breadcrumb: [{ label: 'FAMS' }, { label: 'Operators' }],
          roles: ['ADMIN', 'OPERATOR_MANAGER'],
          portal: 'fams-main',
          requiresAuth: true
        }
      },

      {
        path: 'workflows',
        name: 'workflows',
        component: () => import('@/views/fams/workflows/Workflows.vue'),
        meta: {
          breadcrumb: [{ label: 'FAMS' }, { label: 'Workflows' }],
          roles: ['ADMIN'],
          portal: 'fams-main'
        }
      }
    ]
  },

  // Catch-all (404)
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/pages/Error.vue')
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

// Global navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  const portalStore = usePortalStore();

  // Check auth
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next('/login');
  }

  // Check roles
  if (to.meta.roles && !authStore.hasRole(to.meta.roles)) {
    return next('/access-denied');
  }

  // Check portal access
  if (to.meta.portal && to.meta.portal !== 'ALL') {
    if (!portalStore.hasAccess(to.meta.portal)) {
      return next('/access-denied');
    }
  }

  next();
});

export default router;
```

---

# PART 6: SERVICE LAYER & API INTEGRATION

## 6.1 Centralized API Client

```javascript
// src/service/apiService.js
import axios from 'axios';
import { useToast } from 'primevue/usetoast';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_ROOT_API,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Response interceptor (auto error toasts)
apiClient.interceptors.response.use(
  response => response,
  error => {
    const toast = useToast();
    const message = error.response?.data?.message || error.message;

    toast.add({
      severity: 'error',
      summary: 'API Error',
      detail: message,
      life: 3000
    });

    return Promise.reject(error);
  }
);

export { apiClient };
```

## 6.2 Entity Service Classes

```javascript
// src/service/AssetService.js
import { apiClient } from './apiService';

export const AssetService = {
  async getAssets(params = {}) {
    return apiClient.get('/assets', { params });
  },

  async getAssetById(id) {
    return apiClient.get(`/assets/${id}`);
  },

  async createAsset(payload) {
    return apiClient.post('/assets', payload);
  },

  async updateAsset(id, payload) {
    return apiClient.put(`/assets/${id}`, payload);
  },

  async deleteAsset(id) {
    return apiClient.delete(`/assets/${id}`);
  },

  async searchAssets(query) {
    return apiClient.get('/assets/search', { params: { q: query } });
  },

  async getAssetsByCategory(categoryId) {
    return apiClient.get(`/assets/category/${categoryId}`);
  }
};
```

---

# PART 7: STYLING & DESIGN TOKENS

## 7.1 PrimeVue 4 Design Tokens

```javascript
// In main.js
import { definePreset } from '@primeuix/themes';
import Lara from '@primeuix/themes/lara';
import PrimeVue from 'primevue/config';

const MyFamsPreset = definePreset(Lara, {
  semantic: {
    primary: {
      50: '{indigo.50}',
      100: '{indigo.100}',
      500: '{indigo.500}',
      600: '{indigo.600}',
      900: '{indigo.900}'
    },
    formField: {
      paddingY: '0.5rem',
      paddingX: '0.75rem'
    }
  }
});

app.use(PrimeVue, {
  theme: {
    preset: MyFamsPreset,
    options: {
      darkModeSelector: '.app-dark',
      cssLayer: false
    }
  }
});
```

## 7.2 Dark Mode

```vue
<script setup>
import { ref } from 'vue';

const isDarkMode = ref(false);

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value;
  const html = document.documentElement;
  
  if (isDarkMode.value) {
    html.classList.add('app-dark');
  } else {
    html.classList.remove('app-dark');
  }

  localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light');
};

// Load theme from localStorage on mount
onMounted(() => {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    isDarkMode.value = true;
    document.documentElement.classList.add('app-dark');
  }
});
</script>

<template>
  <Button
    icon="pi pi-sun"
    rounded
    text
    @click="toggleDarkMode"
  />
</template>
```

---

# PART 8: FEATURE IMPLEMENTATION BLUEPRINT

## 8.1 Step-by-Step Feature Creation

### Step 1: Create Service Class

```javascript
// src/service/OperatorService.js
import { apiClient } from './apiService';

export const OperatorService = {
  async getAll(params = {}) {
    return apiClient.get('/operators', { params });
  },
  async getById(id) {
    return apiClient.get(`/operators/${id}`);
  },
  async create(payload) {
    return apiClient.post('/operators', payload);
  },
  async update(id, payload) {
    return apiClient.put(`/operators/${id}`, payload);
  },
  async delete(id) {
    return apiClient.delete(`/operators/${id}`);
  }
};
```

### Step 2: Create Form Composable

```javascript
// src/views/fams/operators/useOperatorForm.js
import { ref, reactive } from 'vue';
import { OperatorService } from '@/service/OperatorService';

export function useOperatorForm() {
  const formData = reactive({
    id: null,
    name: '',
    email: '',
    phone: '',
    department: null,
    active: true
  });

  const formErrors = reactive({
    name: '', email: '', phone: ''
  });

  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const isSidebarOpen = ref(false);

  function validateForm() {
    let valid = true;
    if (!formData.name.trim()) {
      formErrors.name = 'Name is required';
      valid = false;
    }
    if (!formData.email.includes('@')) {
      formErrors.email = 'Valid email required';
      valid = false;
    }
    return valid;
  }

  function resetForm() {
    Object.assign(formData, {
      id: null, name: '', email: '', phone: '', department: null, active: true
    });
    Object.assign(formErrors, { name: '', email: '', phone: '' });
  }

  async function submitForm() {
    if (!validateForm()) return;
    isSubmitting.value = true;
    try {
      if (formData.id) {
        await OperatorService.update(formData.id, formData);
      } else {
        await OperatorService.create(formData);
      }
      resetForm();
      isSidebarOpen.value = false;
    } finally {
      isSubmitting.value = false;
    }
  }

  return { formData, formErrors, isLoading, isSubmitting, isSidebarOpen, validateForm, resetForm, submitForm };
}
```

### Step 3: Create Lookups Composable

```javascript
// src/views/fams/operators/useOperatorLookups.js
import { ref, onMounted } from 'vue';

export function useOperatorLookups() {
  const departments = ref([
    { id: 1, name: 'Engineering' },
    { id: 2, name: 'Operations' },
    { id: 3, name: 'Finance' }
  ]);

  const statuses = ref([
    { id: 'ACTIVE', name: 'Active' },
    { id: 'INACTIVE', name: 'Inactive' }
  ]);

  return { departments, statuses };
}
```

### Step 4: Create Page Component

```vue
<!-- src/views/fams/operators/Operators.vue -->
<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useOperatorForm } from './useOperatorForm';
import { OperatorService } from '@/service/OperatorService';
import OperatorsSidebar from './OperatorsSidebar.vue';

const operatorList = ref([]);
const isLoading = ref(false);
const toast = useToast();
const form = useOperatorForm();

onMounted(() => loadList());

const loadList = async () => {
  isLoading.value = true;
  try {
    const response = await OperatorService.getAll();
    operatorList.value = response.data || [];
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load operators' });
  } finally {
    isLoading.value = false;
  }
};

const onAddNew = () => {
  form.resetForm();
  form.isSidebarOpen.value = true;
};

const onEdit = (row) => {
  form.formData.id = row.id;
  form.formData.name = row.name;
  form.formData.email = row.email;
  form.formData.phone = row.phone;
  form.formData.department = row.department;
  form.isSidebarOpen.value = true;
};

const onSidebarClose = () => {
  form.isSidebarOpen.value = false;
  loadList();
};

const onDelete = async (id) => {
  try {
    await OperatorService.delete(id);
    toast.add({ severity: 'success', summary: 'Deleted', detail: 'Operator deleted' });
    loadList();
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message });
  }
};
</script>

<template>
  <div class="p-6">
    <div class="mb-4 flex justify-between">
      <h1 class="text-2xl font-bold">Operators</h1>
      <Button label="Add Operator" @click="onAddNew" />
    </div>

    <DataTable :value="operatorList" :loading="isLoading" paginator :rows="10">
      <Column field="name" header="Name" />
      <Column field="email" header="Email" />
      <Column field="department" header="Department" />
      <Column header="Actions">
        <template #body="{ data }">
          <Button icon="pi pi-pencil" @click="onEdit(data)" />
          <Button icon="pi pi-trash" severity="danger" @click="onDelete(data.id)" />
        </template>
      </Column>
    </DataTable>

    <OperatorsSidebar
      v-if="form.isSidebarOpen.value"
      :form="form"
      @close="onSidebarClose"
    />
  </div>
</template>
```

### Step 5: Create Sidebar Component

```vue
<!-- src/views/fams/operators/OperatorsSidebar.vue -->
<script setup>
import { computed } from 'vue';
import { useOperatorLookups } from './useOperatorLookups';

const props = defineProps({
  form: Object
});

const emit = defineEmits(['close']);

const lookups = useOperatorLookups();

const name = computed({
  get: () => props.form.formData.name,
  set: (val) => { props.form.formData.name = val; }
});
</script>

<template>
  <Drawer
    v-model:visible="form.isSidebarOpen.value"
    header="Operator"
    :modal="true"
    @hide="emit('close')"
  >
    <form @submit.prevent="form.submitForm" class="space-y-4">
      <div>
        <label>Name</label>
        <InputText v-model="name" />
        <Message v-if="form.formErrors.name" severity="error" :text="form.formErrors.name" />
      </div>

      <div>
        <label>Email</label>
        <InputText v-model="form.formData.email" type="email" />
        <Message v-if="form.formErrors.email" severity="error" :text="form.formErrors.email" />
      </div>

      <div>
        <label>Department</label>
        <Select
          v-model="form.formData.department"
          :options="lookups.departments"
          optionLabel="name"
          optionValue="id"
        />
      </div>

      <div class="flex gap-2 justify-end">
        <Button label="Cancel" severity="secondary" @click="emit('close')" />
        <Button label="Save" :loading="form.isSubmitting.value" @click="form.submitForm" />
      </div>
    </form>
  </Drawer>
</template>
```

### Step 6: Register Route

```javascript
// In src/router/index.js, add to children:
{
  path: 'operators',
  name: 'operators',
  component: () => import('@/views/fams/operators/Operators.vue'),
  meta: {
    breadcrumb: [{ label: 'FAMS' }, { label: 'Operators' }],
    roles: ['ADMIN', 'OPERATOR_MANAGER'],
    portal: 'fams-main',
    requiresAuth: true
  }
}
```

---

# PART 9: COMMON ANTI-PATTERNS & CODE REVIEW CHECKLIST

## 9.1 Anti-Patterns to Reject in PR Review

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Ad-hoc axios instances | Bypasses centralized error handling | Use `apiClient` from `apiService.js` |
| Monolithic `.vue` files (2000+ lines) | Unmaintainable, hard to test | Split into page + sidebar + composables |
| Direct prop mutation | Breaks Vue's one-way data flow | Use `defineModel()` or emit events |
| Deep `reactive()` reassignment | Breaks reactivity entirely | Use `ref` or `Object.assign()` |
| TypeScript syntax in JS project | Build will fail | Use plain JS only |
| Side effects in `computed()` | Violates pure function principle | Move to `watch()` or `watchEffect()` |
| No validation before submit | Allows invalid data to API | Implement validation before submit |
| Manual DOM manipulation | Bypasses Vue's reactivity | Use `ref` and templates |
| Event handler logic in templates | Unreadable, hard to test | Extract to methods in setup |
| Storing local UI state in Pinia | Pollutes global store | Use local component `ref` |

## 9.2 Pre-Commit Checklist

- [ ] Feature follows page + sidebar + composables split
- [ ] Form validation works (required fields, min/max, email format)
- [ ] Sidebar opens/closes reactively
- [ ] Add/Edit/Delete operations work
- [ ] DataTable updates after save
- [ ] Error messages display (via `<Message>`)
- [ ] Success toast appears on save
- [ ] No console errors
- [ ] Component names follow pattern: `Feature.vue`, `FeatureSidebar.vue`
- [ ] Composables named: `useFeatureForm.js`, `useFeatureLookups.js`
- [ ] Service class created: `FeatureService.js`
- [ ] Route added to `router/index.js` with meta data
- [ ] Using `storeToRefs()` when accessing Pinia store
- [ ] No manual `$forceUpdate()` calls
- [ ] No TypeScript syntax
- [ ] Using Tailwind utilities for spacing/layout
- [ ] Using PrimeVue components (not custom HTML)
- [ ] No `!important` in CSS
- [ ] Responsive design (mobile/tablet/desktop)
- [ ] Dark mode compatible

---

# PART 10: DEPLOYMENT & RELEASE ROADMAP

## 10.1 Build & Deploy Commands

```bash
# Install dependencies
npm install

# Development server (with HMR)
npm run dev        # Serves on http://localhost:5173

# Production build
npm run build       # Creates ./dist directory

# Preview production build locally
npm run preview     # Serves built dist for testing

# Linting
npm run lint       # ESLint check (configured via .eslintrc.cjs)
```

## 10.2 Environment Variables

```bash
# .env.development
VITE_ROOT_API=http://localhost:3000/api

# .env.production
VITE_ROOT_API=https://api.fams-portal.com/api
```

## 10.3 Release Phases

```
Phase 1: PREPARE (2 weeks)
├─ Setup Vite, ESLint, auto-import resolvers
├─ Configure PrimeVue themes and dark mode
└─ Create base layouts (AppLayout, AppSidebar, AppTopbar)

Phase 2: FEATURE DEVELOPMENT (4 weeks)
├─ Implement core FAMS features (Assets, Operators, Equipment, Workflows)
├─ Build form composables with validation
├─ Integrate PrimeVue DataTable with lazy loading
└─ Setup Pinia stores for cross-feature state

Phase 3: BUG BASH & QA (2 weeks)
├─ Manual testing of all workflows
├─ Console debugging for PrimeVue warnings
├─ Performance profiling (lazy loading, bundle size)
└─ Accessibility testing (keyboard, screen reader)

Phase 4: PRODUCTION DEPLOYMENT
├─ Compile production bundle (npm run build)
├─ Configure global router guards & auth
├─ Setup canary deployment with rollback plan
└─ Monitor errors and performance metrics
```

---

# PART 11: QUICK REFERENCE

## 11.1 File Creation Checklist

When adding a new feature named `<Feature>`:

1. **Service**: `src/service/<Feature>Service.js`
2. **Composables**: 
   - `use<Feature>Form.js`
   - `use<Feature>Lookups.js`
   - `use<Feature>Payloads.js` (if needed)
3. **Components**:
   - `src/views/fams/<feature>/<Feature>.vue` (page)
   - `src/views/fams/<feature>/<Feature>Sidebar.vue` (form drawer)
4. **Store** (if needed): `src/stores/<feature>Store.js`
5. **Route**: Add to `src/router/index.js` under `/main` children

## 11.2 Component Template Skeleton

```vue
<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { use<Feature>Form } from './use<Feature>Form';
import { <Feature>Service } from '@/service/<Feature>Service';
import <Feature>Sidebar from './<Feature>Sidebar.vue';

const toast = useToast();
const form = use<Feature>Form();
const itemList = ref([]);
const isLoading = ref(false);

onMounted(() => loadList());

const loadList = async () => {
  isLoading.value = true;
  try {
    const response = await <Feature>Service.getAll();
    itemList.value = response.data || [];
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message });
  } finally {
    isLoading.value = false;
  }
};

const onAddNew = () => {
  form.resetForm();
  form.isSidebarOpen.value = true;
};

const onEdit = (row) => {
  form.loadFormData(row.id);
  form.isSidebarOpen.value = true;
};

const onSidebarClose = () => {
  form.isSidebarOpen.value = false;
  loadList();
};
</script>

<template>
  <div class="p-6">
    <div class="mb-4 flex justify-between">
      <h1 class="text-2xl font-bold"><Feature> List</h1>
      <Button label="Add" @click="onAddNew" />
    </div>

    <DataTable :value="itemList" :loading="isLoading" paginator :rows="10">
      <!-- Columns here -->
    </DataTable>

    <<Feature>Sidebar
      v-if="form.isSidebarOpen.value"
      :form="form"
      @close="onSidebarClose"
    />
  </div>
</template>
```

---

# CONCLUSION

This FAMS Portal skill consolidates:
- **Architecture**: Vite, Vue 3, Composition API, PrimeVue 4, Pinia, Tailwind
- **Patterns**: Feature split, form composables, Pinia stores, reactive state
- **Components**: DataTable, Forms, Drawers, Messages, and PrimeVue integration
- **Styling**: Design tokens, dark mode, Tailwind utilities, PassThrough
- **API**: Centralized axios client, entity services, error handling
- **Deployment**: Build, env config, release phases
- **Quality**: Anti-patterns, code review checklist, best practices

**Start with Part 1 (Architecture), then implement features using Part 8 (Feature Blueprint). Refer to Part 11 (Quick Reference) during development.**
