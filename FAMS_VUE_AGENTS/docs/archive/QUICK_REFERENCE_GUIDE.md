# FAMS Portal Vue 3 — Quick Reference Guide

## 🚀 Feature Development Workflow (5-Step Checklist)

```
┌─────────────────────────────────────────────────┐
│ 1. CREATE COMPOSABLES                           │
│    ├─ useFeatureName.js      (form state)      │
│    ├─ useFeatureNameLookups.js (dropdown data)  │
│    └─ useFeatureNamePayloads.js (DTO building)  │
├─────────────────────────────────────────────────┤
│ 2. CREATE SERVICE CLASS                         │
│    └─ FeatureService.js (API calls + caching)   │
├─────────────────────────────────────────────────┤
│ 3. CREATE COMPONENTS                            │
│    ├─ FeatureName.vue        (page/list)        │
│    └─ FeatureNameSidebar.vue  (create/edit)     │
├─────────────────────────────────────────────────┤
│ 4. CREATE PINIA STORE (if needed)               │
│    └─ stores/featureStore.js  (cross-feature)   │
├─────────────────────────────────────────────────┤
│ 5. ADD ROUTE                                    │
│    └─ router/index.js (add lazy-loaded route)   │
└─────────────────────────────────────────────────┘
```

---

## 📋 Reactive State Patterns

### Pattern 1: Form with Individual Field Refs

```javascript
// useEquipmentForm.js
import { ref, reactive, computed } from 'vue';

export function useEquipmentForm() {
  // ✅ Individual refs for form fields
  const formData = reactive({
    id: null,
    name: '',
    type: null,
    status: 'ACTIVE',
  });

  const formErrors = reactive({
    name: '',
    type: '',
  });

  // Computed validity
  const isFormValid = computed(() => {
    return formData.name.trim() && formData.type;
  });

  return { formData, formErrors, isFormValid };
}
```

### Pattern 2: Filtered & Paginated List

```javascript
// In component or store
const items = ref([]);
const filters = reactive({ search: '', status: null });
const page = ref(1);
const pageSize = ref(10);

// ✅ Derived with computed (auto-caches)
const filtered = computed(() => {
  return items.value.filter(item => 
    (!filters.search || item.name.includes(filters.search)) &&
    (!filters.status || item.status === filters.status)
  );
});

const paginated = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filtered.value.slice(start, start + pageSize.value);
});

const total = computed(() => filtered.value.length);
```

### Pattern 3: Pinia Store (Setup Syntax)

```javascript
// stores/equipmentStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { EquipmentService } from '@/service/EquipmentService';

export const useEquipmentStore = defineStore('equipment', () => {
  // State
  const items = ref([]);
  const isLoading = ref(false);

  // Computed
  const activeItems = computed(() => 
    items.value.filter(i => i.status === 'ACTIVE')
  );

  // Actions
  const fetchAll = async () => {
    isLoading.value = true;
    try {
      const response = await EquipmentService.getAll();
      items.value = response.data;
    } finally {
      isLoading.value = false;
    }
  };

  const addItem = async (payload) => {
    const response = await EquipmentService.create(payload);
    items.value.push(response.data);
  };

  return { items, isLoading, activeItems, fetchAll, addItem };
});
```

---

## 🎯 Component Patterns

### Pattern 4: Page with DataTable & Sidebar

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { useEquipmentForm } from './useEquipmentForm';
import { EquipmentService } from '@/service/EquipmentService';

const equipmentList = ref([]);
const isLoading = ref(false);
const form = useEquipmentForm();

onMounted(() => loadList());

const loadList = async () => {
  isLoading.value = true;
  equipmentList.value = await EquipmentService.getAll();
  isLoading.value = false;
};

const onAddNew = () => {
  form.resetForm();
  form.isSidebarOpen.value = true;
};

const onEdit = (row) => {
  form.loadFormData(row.id);
  form.isSidebarOpen.value = true;
};
</script>

<template>
  <div class="p-6">
    <Button label="Add" @click="onAddNew" />
    <DataTable :value="equipmentList" :loading="isLoading">
      <Column field="name" header="Name" />
      <Column header="Actions">
        <template #body="{ data }">
          <Button icon="pi pi-pencil" @click="onEdit(data)" />
        </template>
      </Column>
    </DataTable>
    <EquipmentSidebar v-if="form.isSidebarOpen" :form="form" />
  </div>
</template>
```

### Pattern 5: Sidebar with Form Inputs

```vue
<script setup>
import { computed } from 'vue';

const props = defineProps({
  formData: Object,
  formErrors: Object,
});

const emit = defineEmits(['submit', 'close']);

// ✅ Computed two-way binding for form fields
const name = computed({
  get: () => props.formData.name,
  set: (val) => { props.formData.name = val; },
});
</script>

<template>
  <Drawer :visible="true" header="Equipment" @hide="$emit('close')">
    <div class="space-y-4">
      <div>
        <label>Name</label>
        <InputText v-model="name" />
        <Message v-if="formErrors.name" severity="error" :text="formErrors.name" />
      </div>
      <div>
        <Button label="Save" @click="$emit('submit')" />
        <Button label="Cancel" @click="$emit('close')" />
      </div>
    </div>
  </Drawer>
</template>
```

---

## 🔌 PrimeVue 4 Bindings

### DataTable (Lazy Loading)

```vue
<DataTable
  :value="items"
  :loading="isLoading"
  :lazy="true"
  :paginator="true"
  :first="(page - 1) * pageSize"
  :rows="pageSize"
  :totalRecords="totalItems"
  @page="(e) => page = Math.ceil((e.first + 1) / e.rows)"
  @sort="(e) => { sortField = e.sortField; sortOrder = e.sortOrder; }"
>
  <Column field="name" header="Name" sortable />
</DataTable>
```

### Select (Dropdown)

```vue
<Select
  v-model="formData.type"
  :options="lookups.equipmentTypes"
  optionLabel="label"
  optionValue="value"
  placeholder="Select type"
/>
```

### DatePicker

```vue
<DatePicker
  v-model="formData.createdDate"
  dateFormat="yy-mm-dd"
  placeholder="Select date"
/>
```

### ToggleSwitch (Boolean)

```vue
<ToggleSwitch
  v-model="formData.isActive"
  trueValue="ACTIVE"
  falseValue="INACTIVE"
/>
```

### MultiSelect

```vue
<MultiSelect
  v-model="formData.tags"
  :options="lookups.tags"
  optionLabel="name"
  optionValue="id"
  placeholder="Select tags"
/>
```

### Message (Error Display)

```vue
<Message
  v-if="formErrors.name"
  severity="error"
  :text="formErrors.name"
/>
```

---

## 🎣 Watch & Computed Quick Rules

### Use `computed` for:
```javascript
// ✅ Filtering
const activeEquipment = computed(() => 
  items.value.filter(i => i.status === 'ACTIVE')
);

// ✅ Formatting
const formattedDate = computed(() => 
  new Date(date.value).toLocaleDateString()
);

// ✅ Derived totals
const totalCost = computed(() =>
  items.value.reduce((sum, i) => sum + i.cost, 0)
);
```

### Use `watch` for:
```javascript
// ✅ API calls on filter change
watch(
  () => filters.search,
  async (newSearch) => {
    items.value = await search(newSearch);
  }
);

// ✅ Portal context change
watch(
  () => currentPortal.value?.id,
  async (portalId) => {
    if (portalId) await loadPortalData(portalId);
  }
);

// ✅ Side effects (localStorage, emits)
watchEffect(() => {
  localStorage.setItem('filter', JSON.stringify(filters));
});
```

---

## 🛠️ Common Tasks

### Task 1: Load data on component mount
```javascript
onMounted(async () => {
  isLoading.value = true;
  try {
    data.value = await Service.getAll();
  } catch (err) {
    showError(err.message);
  } finally {
    isLoading.value = false;
  }
});
```

### Task 2: Handle form submission
```javascript
const onSubmit = async () => {
  if (!validateForm()) return;
  
  isSubmitting.value = true;
  try {
    const payload = buildPayload(formData);
    await Service.save(payload);
    showSuccess('Saved');
    resetForm();
    close();
  } catch (err) {
    formErrors.submit = err.message;
  } finally {
    isSubmitting.value = false;
  }
};
```

### Task 3: Delete with confirmation
```javascript
const onDelete = (id) => {
  confirm.require({
    message: 'Are you sure?',
    accept: async () => {
      try {
        await Service.delete(id);
        items.value = items.value.filter(i => i.id !== id);
        showSuccess('Deleted');
      } catch (err) {
        showError(err.message);
      }
    },
  });
};
```

### Task 4: Filter with search debounce
```javascript
const searchTerm = ref('');
const searchResults = ref([]);

const debouncedSearch = debounce(async (term) => {
  if (!term) { searchResults.value = []; return; }
  searchResults.value = await Service.search(term);
}, 300);

watch(() => searchTerm.value, debouncedSearch);
```

### Task 5: Multi-select with filter
```javascript
<MultiSelect
  v-model="selectedIds"
  :options="allItems"
  optionLabel="name"
  optionValue="id"
  filter
  placeholder="Type to filter..."
/>
```

---

## 💾 Service Class Template

```javascript
// service/FeatureService.js
import { apiClient } from './apiService';

class FeatureService {
  async getAll() {
    const response = await apiClient.get('/feature');
    return response.data;
  }

  async getById(id) {
    return apiClient.get(`/feature/${id}`).then(r => r.data);
  }

  async create(payload) {
    return apiClient.post('/feature', payload).then(r => r.data);
  }

  async update(id, payload) {
    return apiClient.put(`/feature/${id}`, payload).then(r => r.data);
  }

  async delete(id) {
    return apiClient.delete(`/feature/${id}`);
  }
}

export const FeatureService = new FeatureService();
```

---

## 🗺️ Route Registration Template

```javascript
// router/index.js
const routes = [
  {
    path: '/main/feature',
    component: () => import('@/views/fams/feature/Feature.vue'),
    meta: {
      breadcrumb: 'Feature',
      roles: ['ADMIN', 'USER'],
      portal: ['ALL'],
      requiresAuth: true,
    },
  },
];
```

---

## 🎨 Styling with PrimeVue & Tailwind

### Tailwind Classes
```vue
<div class="p-6 space-y-4">           <!-- padding, spacing -->
  <div class="mb-4 flex items-center">  <!-- margin, flexbox -->
    <h1 class="text-2xl font-bold">Title</h1>
  </div>
  <input class="w-full border rounded p-2" /> <!-- width, border, rounded -->
</div>
```

### PrimeVue Component Class Styling
```vue
<!-- Use pt prop for component customization -->
<Button
  label="Click"
  :pt="{ root: { class: 'bg-blue-600 text-white' } }"
/>

<!-- Or use Tailwind + :unstyled for full control -->
<Button
  label="Click"
  :unstyled="true"
  class="bg-blue-600 text-white px-4 py-2 rounded"
/>
```

---

## ✅ Pre-Commit Checklist

Before pushing a new feature:

- [ ] Form validation works (empty, invalid, required fields)
- [ ] Sidebar opens/closes reactively
- [ ] Add/Edit/Delete operations work
- [ ] DataTable updates after save
- [ ] Error messages display
- [ ] No console errors
- [ ] Component names follow pattern: `Feature.vue`, `FeatureSidebar.vue`
- [ ] Composables follow pattern: `useFeature*.js`
- [ ] Service class created: `FeatureService.js`
- [ ] Route added to `router/index.js`
- [ ] No manual `$forceUpdate()` calls
- [ ] Using `storeToRefs()` if accessing Pinia store
- [ ] No TypeScript (plain JavaScript)
- [ ] No test files (not configured)

---

## 🚨 Common Pitfalls & Quick Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Form not updating | Reactive state not returned | Export state from composable in setup |
| Sidebar won't close | `isSidebarOpen` not toggleable | Use `ref` not `const`, emit close event |
| DataTable shows blank | `:value` not bound correctly | Use `:value="items"` where items is `ref([])` |
| Computed doesn't re-run | Dependency not tracked | Make sure deps are reactive (in computed return) |
| Store mutations don't reflect | Using Vuex pattern | Use Pinia actions that mutate state directly |
| Validation always passes | validateForm() not called | Call before submit, return early if invalid |
| Search on every keystroke | No debounce | Wrap in debounce utility |
| Memory leak on unmount | No cleanup | Use onUnmounted, cancel watch, clear subscriptions |

---

## 📚 Where to Find Full Details

| Topic | Find In |
|-------|---------|
| Detailed reactive patterns | `Vue3_FAMS_Portal_Reactive_UPDATED.md` |
| PrimeVue 4 components | `Vue3_SKILL.md` → PrimeVue 4 Knowledge section |
| Project structure | `Vue3_SKILL.md` → Directory Map |
| Legacy FAMS behavior | `Vue2_SKILL.md` (for reference only) |
| API contracts | Backend docs (not yet in skill) |
| Auth & routing | `Vue3_SKILL.md` → Routing & Auth Gate |
| Styling & theme | `Vue3_SKILL.md` → Styling section |

---

## 🎓 Learning Path

1. **Read:** Evaluation & Update Summary (`EVALUATION_SUMMARY.md`)
2. **Skim:** Full reactive patterns skill (`Vue3_FAMS_Portal_Reactive_UPDATED.md`) — sections 1-4
3. **Build:** First feature using this quick reference
4. **Deep dive:** Reactive patterns skill sections 5-10 as needed
5. **Refer:** This quick reference during development

---

## 💬 When to Ask for Help

- ❓ "How do I structure a form?" → See Pattern 1 (Form with Refs) above
- ❓ "How do I filter + paginate?" → See Pattern 2 (Filtered List) above
- ❓ "How do I build a page?" → See Pattern 4 (Page with DataTable) above
- ❓ "DataTable not lazy-loading" → Check PrimeVue 4 Bindings section
- ❓ "Watch vs Computed?" → See Watch & Computed Quick Rules
- ❓ "Pinia setup?" → See Pattern 3 (Pinia Store)
- ❓ "Service class design?" → See Service Class Template
- ❓ "Portal auth?" → See `Vue3_SKILL.md` routing section
