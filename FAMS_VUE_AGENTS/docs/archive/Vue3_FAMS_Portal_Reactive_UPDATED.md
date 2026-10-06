---
name: fams-vue3-reactive-patterns
description: Enhanced skill for building the new FAMS portal using Vue 3 Composition API with PrimeVue 4. Covers advanced reactive patterns, form state management, composables architecture, and reactive design best practices specific to FAMS-UI portal development.
---

# FAMS Vue 3 Portal — Reactive Patterns & PrimeVue 4 Integration

## Overview

This skill extends the base `fams-vue3` skill with **deep reactive patterns** for building the new FAMS portal. It addresses:
- Composition API reactive state management (ref vs reactive vs computed)
- PrimeVue 4 component integration patterns
- Form state composables with validation
- Pinia store reactive architecture
- Data fetching and caching with reactivity
- Portal-specific multi-tenant reactive concerns

**Stack:** Vue 3.4 + Vite 5 + Composition API (`<script setup>`) + PrimeVue 4 + Pinia 3 + Tailwind CSS 4

---

## Reactivity Fundamentals for FAMS Portal

### ref vs reactive — Decision Tree

| Scenario | Use `ref` | Use `reactive` |
|---|---|---|
| Single primitive (string, number, boolean) | ✅ | ❌ |
| Single object | ✅ (recommended) | ✅ (ok for deeply-mutated shapes) |
| Form data object (fields scattered, validated individually) | ✅ (per-field refs) | ✅ (if mutating whole fields at once) |
| Deeply nested structure requiring frequent path mutations | ❌ | ✅ |
| Need to reassign entire value later | ✅ | ❌ (breaks reactivity) |
| Array of objects to mutate by index | ✅ | ✅ |
| Pinia store state | ✅ preferred | ✅ ok |

**FAMS Portal Pattern:** Use **`ref` for individual form fields** (clearer reactivity tracking) and **`reactive` for entity state objects** (when mutating nested properties frequently — e.g., `equipment.parameters`).

```javascript
// ✅ FAMS Portal: per-field refs (preferred for forms)
const equipmentId = ref(null);
const equipmentName = ref('');
const equipmentStatus = ref('ACTIVE');
const parameters = ref({});

// ✅ Also valid: one reactive object per form
const formState = reactive({
  equipmentId: null,
  equipmentName: '',
  equipmentStatus: 'ACTIVE',
  parameters: {},
});

// ❌ Avoid: mixing ref/reactive carelessly
const mixed = ref({ nested: { value: 1 } }); // Works but `.nested` access is verbose
```

### Reactivity Gotchas in Vue 3 (Already Fixed)

Vue 3 **no longer needs** `Vue.set()` or `this.$set()` for dynamic properties:

```javascript
// ✅ Vue 3: direct assignment works
const equipment = reactive({ name: 'Tank 1' });
equipment.newProperty = 'value'; // Reactive!

// ✅ Array mutations work directly
const items = ref([]);
items.value[0] = newItem; // Reactive!
items.value.length = 5; // Reactive!
```

The legacy Vue 2 FAMS code likely has many `$set` calls — **these can all be removed** in the Vue 3 rebuild.

---

## Composition API Pattern for FAMS Features

### 1. Feature Page + Sidebar + Composables Architecture

Each FAMS feature (e.g., Equipment) follows this split:

```
fams/equipment/
  Equipment.vue                   (page/list view)
  EquipmentSidebar.vue            (create/edit form panel)
  useEquipmentForm.js             (form state + methods)
  useEquipmentLookups.js          (dropdown/select data)
  useEquipmentPayloads.js         (build API request DTOs)
```

### 2. useEquipmentForm.js — The Reactive Form State Composable

```javascript
import { ref, reactive, computed } from 'vue';
import { useEquipmentPayloads } from './useEquipmentPayloads';
import { EquipmentService } from '@/service/EquipmentService';

export function useEquipmentForm() {
  // ─────────────────────────────────────
  // Form state: per-field refs (clearer tracking)
  // ─────────────────────────────────────
  const formData = reactive({
    id: null,
    name: '',
    type: null, // Select component
    status: 'ACTIVE',
    location: '',
    parameters: {}, // Nested object — mutate keys directly
  });

  const formErrors = reactive({
    name: '',
    type: '',
    location: '',
  });

  const isLoading = ref(false);
  const isSidebarOpen = ref(false);
  const isSubmitting = ref(false);

  // ─────────────────────────────────────
  // Computed: form validity
  // ─────────────────────────────────────
  const isFormValid = computed(() => {
    return formData.name.trim() && formData.type;
  });

  const hasErrors = computed(() => {
    return Object.values(formErrors).some(err => err);
  });

  // ─────────────────────────────────────
  // Methods: state manipulation
  // ─────────────────────────────────────
  
  const resetForm = () => {
    formData.id = null;
    formData.name = '';
    formData.type = null;
    formData.status = 'ACTIVE';
    formData.location = '';
    formData.parameters = {};
    Object.keys(formErrors).forEach(key => {
      formErrors[key] = '';
    });
  };

  const loadFormData = async (equipmentId) => {
    isLoading.value = true;
    try {
      const response = await EquipmentService.getById(equipmentId);
      // Populate form reactively
      formData.id = response.id;
      formData.name = response.name;
      formData.type = response.type;
      formData.status = response.status;
      formData.location = response.location;
      formData.parameters = { ...response.parameters }; // Shallow copy
    } catch (error) {
      formErrors.name = 'Failed to load equipment';
    } finally {
      isLoading.value = false;
    }
  };

  const validateForm = () => {
    let valid = true;
    
    if (!formData.name.trim()) {
      formErrors.name = 'Equipment name is required';
      valid = false;
    } else {
      formErrors.name = '';
    }

    if (!formData.type) {
      formErrors.type = 'Equipment type is required';
      valid = false;
    } else {
      formErrors.type = '';
    }

    return valid;
  };

  const submitForm = async () => {
    if (!validateForm()) return;

    isSubmitting.value = true;
    try {
      const payload = useEquipmentPayloads().buildSavePayload(formData);
      
      if (formData.id) {
        await EquipmentService.update(formData.id, payload);
      } else {
        await EquipmentService.create(payload);
      }
      
      resetForm();
      isSidebarOpen.value = false;
    } catch (error) {
      formErrors.name = error.message || 'Failed to save equipment';
    } finally {
      isSubmitting.value = false;
    }
  };

  return {
    // State
    formData,
    formErrors,
    isLoading,
    isSidebarOpen,
    isSubmitting,
    
    // Computed
    isFormValid,
    hasErrors,
    
    // Methods
    resetForm,
    loadFormData,
    validateForm,
    submitForm,
  };
}
```

### 3. Equipment.vue (Page Component) — Using the Composable

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import Equipment from './EquipmentSidebar.vue';
import { useEquipmentForm } from './useEquipmentForm';
import { EquipmentService } from '@/service/EquipmentService';

// Compose reactive form state
const equipmentForm = useEquipmentForm();
const toast = useToast();

// Page-level state
const equipmentList = ref([]);
const isLoadingList = ref(false);
const selectedEquipment = ref(null);

// Load equipment list on mount
onMounted(async () => {
  await loadEquipmentList();
});

const loadEquipmentList = async () => {
  isLoadingList.value = true;
  try {
    const response = await EquipmentService.getAll();
    equipmentList.value = response.data || [];
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load equipment list',
      life: 3000,
    });
  } finally {
    isLoadingList.value = false;
  }
};

// Sidebar handlers
const onAddNew = () => {
  equipmentForm.resetForm();
  equipmentForm.isSidebarOpen.value = true;
};

const onEdit = (row) => {
  selectedEquipment.value = row;
  equipmentForm.loadFormData(row.id);
  equipmentForm.isSidebarOpen.value = true;
};

const onSidebarClose = () => {
  equipmentForm.isSidebarOpen.value = false;
  equipmentForm.resetForm();
  loadEquipmentList(); // Refresh if saved
};

const onDelete = async (id) => {
  try {
    await EquipmentService.delete(id);
    toast.add({
      severity: 'success',
      summary: 'Deleted',
      detail: 'Equipment deleted successfully',
      life: 2000,
    });
    await loadEquipmentList();
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message,
      life: 3000,
    });
  }
};
</script>

<template>
  <div class="p-6">
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-2xl font-bold">Equipment</h1>
      <Button
        icon="pi pi-plus"
        label="Add Equipment"
        @click="onAddNew"
      />
    </div>

    <!-- DataTable with reactive list -->
    <DataTable
      :value="equipmentList"
      :loading="isLoadingList"
      responsiveLayout="scroll"
      paginator
      :rows="10"
      stripedRows
      tableStyle="min-width: 50rem"
    >
      <Column field="name" header="Name" />
      <Column field="type" header="Type" />
      <Column field="status" header="Status">
        <template #body="slotProps">
          <Tag
            :value="slotProps.data.status"
            :severity="slotProps.data.status === 'ACTIVE' ? 'success' : 'warning'"
          />
        </template>
      </Column>
      <Column header="Actions">
        <template #body="slotProps">
          <Button
            icon="pi pi-pencil"
            rounded
            text
            severity="warning"
            @click="onEdit(slotProps.data)"
          />
          <Button
            icon="pi pi-trash"
            rounded
            text
            severity="danger"
            @click="onDelete(slotProps.data.id)"
          />
        </template>
      </Column>
    </DataTable>

    <!-- Sidebar (drawer) for create/edit -->
    <EquipmentSidebar
      v-if="equipmentForm.isSidebarOpen.value"
      :formData="equipmentForm.formData"
      :formErrors="equipmentForm.formErrors"
      :isSubmitting="equipmentForm.isSubmitting.value"
      :isLoading="equipmentForm.isLoading.value"
      @submit="equipmentForm.submitForm"
      @close="onSidebarClose"
    />
  </div>
</template>
```

### 4. EquipmentSidebar.vue — PrimeVue Form with Reactive Binding

```vue
<script setup>
import { computed } from 'vue';
import { useEquipmentLookups } from './useEquipmentLookups';

const props = defineProps({
  formData: Object,
  formErrors: Object,
  isSubmitting: Boolean,
  isLoading: Boolean,
});

const emit = defineEmits(['submit', 'close']);

const lookups = useEquipmentLookups();

// Local computed for v-model binding
const name = computed({
  get: () => props.formData.name,
  set: (val) => {
    props.formData.name = val;
  },
});

const type = computed({
  get: () => props.formData.type,
  set: (val) => {
    props.formData.type = val;
  },
});

const status = computed({
  get: () => props.formData.status,
  set: (val) => {
    props.formData.status = val;
  },
});

const onSubmit = () => {
  emit('submit');
};

const onClose = () => {
  emit('close');
};
</script>

<template>
  <Drawer
    v-model:visible="isOpen"
    header="Equipment"
    :modal="true"
    :blockScroll="true"
    @hide="onClose"
  >
    <form @submit.prevent="onSubmit" class="space-y-4">
      <!-- Name field with reactive binding and error display -->
      <div>
        <label for="name" class="block text-sm font-medium mb-2">Name</label>
        <InputText
          id="name"
          v-model="name"
          :class="{ 'ng-invalid ng-touched': formErrors.name }"
          type="text"
          placeholder="Equipment name"
          class="w-full"
        />
        <Message
          v-if="formErrors.name"
          severity="error"
          :text="formErrors.name"
          class="mt-2"
        />
      </div>

      <!-- Type select field -->
      <div>
        <label for="type" class="block text-sm font-medium mb-2">Type</label>
        <Select
          id="type"
          v-model="type"
          :options="lookups.equipmentTypes"
          optionLabel="label"
          optionValue="value"
          placeholder="Select equipment type"
          class="w-full"
        />
        <Message
          v-if="formErrors.type"
          severity="error"
          :text="formErrors.type"
          class="mt-2"
        />
      </div>

      <!-- Status toggle -->
      <div>
        <label class="block text-sm font-medium mb-2">Status</label>
        <ToggleSwitch
          v-model="status"
          trueValue="ACTIVE"
          falseValue="INACTIVE"
        />
      </div>

      <!-- Actions -->
      <div class="flex gap-2 justify-end mt-6">
        <Button
          label="Cancel"
          severity="secondary"
          @click="onClose"
        />
        <Button
          label="Save"
          :loading="isSubmitting"
          @click="onSubmit"
        />
      </div>
    </form>
  </Drawer>
</template>
```

---

## PrimeVue 4 Reactive Patterns

### DataTable with Reactive Data

```vue
<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { DataTableService } from '@/service/DataTableService';

// Reactive table state
const tableState = reactive({
  data: [],
  first: 0,
  rows: 10,
  sortField: 'name',
  sortOrder: 1,
  filters: {},
  totalRecords: 0,
});

const isLoading = ref(false);

// Lazy-load with server-side pagination
const onPage = async (event) => {
  tableState.first = event.first;
  tableState.rows = event.rows;
  await loadData();
};

const onSort = async (event) => {
  tableState.sortField = event.sortField;
  tableState.sortOrder = event.sortOrder;
  tableState.first = 0;
  await loadData();
};

const onFilter = async (event) => {
  tableState.filters = event.filters;
  tableState.first = 0;
  await loadData();
};

const loadData = async () => {
  isLoading.value = true;
  try {
    const response = await DataTableService.fetchData({
      first: tableState.first,
      rows: tableState.rows,
      sortField: tableState.sortField,
      sortOrder: tableState.sortOrder,
      filters: tableState.filters,
    });
    tableState.data = response.data;
    tableState.totalRecords = response.totalRecords;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => loadData());
</script>

<template>
  <DataTable
    :value="tableState.data"
    :loading="isLoading"
    :lazy="true"
    :paginator="true"
    :first="tableState.first"
    :rows="tableState.rows"
    :totalRecords="tableState.totalRecords"
    @page="onPage"
    @sort="onSort"
    @filter="onFilter"
    sortField="name"
    :sortOrder="tableState.sortOrder"
    responsiveLayout="scroll"
  >
    <Column field="name" header="Name" sortable filter />
    <Column field="type" header="Type" sortable filter />
    <!-- more columns -->
  </DataTable>
</template>
```

### Form Validation with Reactive State

```javascript
// useFormValidation.js
import { ref, computed, reactive } from 'vue';

export function useFormValidation(initialValues = {}) {
  const formData = reactive({ ...initialValues });
  const errors = reactive({});
  const touched = reactive({});
  const isSubmitting = ref(false);

  const isValid = computed(() => {
    return Object.keys(errors).every(key => !errors[key]);
  });

  const setFieldError = (field, message) => {
    errors[field] = message;
  };

  const setFieldTouched = (field, isTouched = true) => {
    touched[field] = isTouched;
  };

  const validateField = (field, validationFn) => {
    const error = validationFn(formData[field]);
    setFieldError(field, error);
    return !error;
  };

  const validateForm = (validationSchema) => {
    let hasErrors = false;
    Object.keys(validationSchema).forEach(field => {
      if (!validateField(field, validationSchema[field])) {
        hasErrors = true;
      }
    });
    return !hasErrors;
  };

  const resetForm = (newValues = {}) => {
    Object.keys(formData).forEach(key => delete formData[key]);
    Object.assign(formData, { ...initialValues, ...newValues });
    Object.keys(errors).forEach(key => delete errors[key]);
    Object.keys(touched).forEach(key => delete touched[key]);
  };

  return {
    formData,
    errors,
    touched,
    isSubmitting,
    isValid,
    setFieldError,
    setFieldTouched,
    validateField,
    validateForm,
    resetForm,
  };
}
```

---

## Pinia Store Reactive Patterns (FAMS Portal)

### Entity Store with Reactive State and Actions

```javascript
// stores/equipmentStore.js
import { defineStore } from 'pinia';
import { ref, reactive, computed } from 'vue';
import { EquipmentService } from '@/service/EquipmentService';

export const useEquipmentStore = defineStore('equipment', () => {
  // ─────────────────────────────────────
  // State
  // ─────────────────────────────────────
  const items = ref([]);
  const isLoading = ref(false);
  const error = ref(null);
  
  const filters = reactive({
    status: null,
    type: null,
    search: '',
  });

  const pagination = reactive({
    currentPage: 1,
    pageSize: 10,
    totalItems: 0,
  });

  // ─────────────────────────────────────
  // Computed (derived state)
  // ─────────────────────────────────────
  const filteredItems = computed(() => {
    return items.value.filter(item => {
      let match = true;
      
      if (filters.status && item.status !== filters.status) {
        match = false;
      }
      if (filters.type && item.type !== filters.type) {
        match = false;
      }
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        match = item.name.toLowerCase().includes(searchLower);
      }
      
      return match;
    });
  });

  const paginatedItems = computed(() => {
    const start = (pagination.currentPage - 1) * pagination.pageSize;
    return filteredItems.value.slice(start, start + pagination.pageSize);
  });

  const totalPages = computed(() => {
    return Math.ceil(filteredItems.value.length / pagination.pageSize);
  });

  // ─────────────────────────────────────
  // Actions
  // ─────────────────────────────────────
  const fetchItems = async () => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await EquipmentService.getAll();
      items.value = response.data || [];
      pagination.totalItems = items.value.length;
    } catch (err) {
      error.value = err.message;
      items.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  const addItem = async (payload) => {
    try {
      const response = await EquipmentService.create(payload);
      items.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  };

  const updateItem = async (id, payload) => {
    try {
      const response = await EquipmentService.update(id, payload);
      const index = items.value.findIndex(i => i.id === id);
      if (index !== -1) {
        items.value[index] = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  };

  const deleteItem = async (id) => {
    try {
      await EquipmentService.delete(id);
      items.value = items.value.filter(i => i.id !== id);
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  };

  const setFilter = (filterKey, value) => {
    filters[filterKey] = value;
    pagination.currentPage = 1; // Reset to page 1 on filter change
  };

  const setPage = (page) => {
    pagination.currentPage = page;
  };

  const clearFilters = () => {
    filters.status = null;
    filters.type = null;
    filters.search = '';
    pagination.currentPage = 1;
  };

  return {
    // State
    items,
    isLoading,
    error,
    filters,
    pagination,
    
    // Computed
    filteredItems,
    paginatedItems,
    totalPages,
    
    // Actions
    fetchItems,
    addItem,
    updateItem,
    deleteItem,
    setFilter,
    setPage,
    clearFilters,
  };
});
```

### Using the Store in a Component

```vue
<script setup>
import { onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useEquipmentStore } from '@/stores/equipmentStore';

const equipmentStore = useEquipmentStore();

// Destructure with storeToRefs to maintain reactivity
const { items, isLoading, filters, paginatedItems, totalPages } = storeToRefs(equipmentStore);
const { fetchItems, setFilter, setPage } = equipmentStore;

onMounted(() => fetchItems());
</script>

<template>
  <div>
    <!-- Filter section (reactive) -->
    <div class="mb-4 space-y-2">
      <Select
        v-model="filters.status"
        :options="['ACTIVE', 'INACTIVE']"
        placeholder="Filter by status"
        @update:modelValue="(val) => setFilter('status', val)"
      />
      <InputText
        v-model="filters.search"
        placeholder="Search..."
        @update:modelValue="(val) => setFilter('search', val)"
      />
    </div>

    <!-- Table -->
    <DataTable :value="paginatedItems" :loading="isLoading">
      <Column field="name" header="Name" />
      <Column field="status" header="Status" />
    </DataTable>

    <!-- Pagination -->
    <Paginator
      v-model:first="(filters.currentPage - 1) * filters.pageSize"
      :rows="filters.pageSize"
      :totalRecords="items.length"
      @page="(e) => setPage(Math.ceil((e.first + 1) / e.rows))"
    />
  </div>
</template>
```

---

## Portal-Specific Reactive Concerns

### Multi-Tenant Reactive Context

For a FAMS portal with multiple tenants/organizations:

```javascript
// stores/portalStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const usePortalStore = defineStore('portal', () => {
  const currentPortal = ref(null); // { id, name, type, permissions }
  const currentUser = ref(null);
  const portalFeatures = ref([]);

  const isPortalLoaded = computed(() => !!currentPortal.value);

  const hasFeature = (featureName) => {
    return portalFeatures.value.includes(featureName);
  };

  const hasPermission = (permission) => {
    return currentUser.value?.permissions?.includes(permission) || false;
  };

  const setPortal = (portal) => {
    currentPortal.value = portal;
  };

  const setCurrentUser = (user) => {
    currentUser.value = user;
  };

  const setPortalFeatures = (features) => {
    portalFeatures.value = features;
  };

  const loadPortalContext = async (portalId) => {
    // Fetch portal config, features, permissions
    const response = await PortalService.getContext(portalId);
    setPortal(response.portal);
    setCurrentUser(response.user);
    setPortalFeatures(response.features);
  };

  return {
    currentPortal,
    currentUser,
    portalFeatures,
    isPortalLoaded,
    hasFeature,
    hasPermission,
    setPortal,
    setCurrentUser,
    setPortalFeatures,
    loadPortalContext,
  };
});
```

### Conditional Feature Rendering Based on Portal

```vue
<script setup>
import { usePortalStore } from '@/stores/portalStore';

const portalStore = usePortalStore();
</script>

<template>
  <!-- Equipment features (reactive based on portal permissions) -->
  <section v-if="portalStore.hasFeature('EQUIPMENT_MANAGEMENT')">
    <EquipmentModule />
  </section>

  <!-- Reporting features (role-based) -->
  <section v-if="portalStore.hasPermission('VIEW_REPORTS')">
    <ReportingModule />
  </section>
</template>
```

---

## Watch & Computed Best Practices for Portal

### When to Use watch() vs computed

| Scenario | Use `computed` | Use `watch` |
|---|---|---|
| Derive new data from reactive source | ✅ | ❌ |
| Side effects (API calls, DOM mutations) | ❌ | ✅ |
| Filter/transform an array | ✅ | ❌ |
| Cascade save to localStorage on change | ❌ | ✅ (watchEffect) |
| Format display value | ✅ | ❌ |
| Track multiple deps for single side effect | ❌ | ✅ |

### Efficient Watching in FAMS

```javascript
// ✅ Good: computed (no side effects)
const activeEquipment = computed(() => {
  return items.value.filter(item => item.status === 'ACTIVE');
});

// ✅ Good: watch with cleanup
watch(
  () => currentPortal.value?.id,
  async (newPortalId) => {
    if (newPortalId) {
      await loadPortalData(newPortalId);
    }
  },
  { immediate: true }
);

// ✅ Good: watchEffect for side effects
watchEffect(async () => {
  if (filters.search) {
    await debounceSearch(filters.search);
  }
});

// ❌ Avoid: side effects in computed
const badComputed = computed(() => {
  // Don't call APIs here!
  fetchData(); // ❌ BAD
  return items.value;
});
```

---

## Data Fetching & Caching Patterns

### Reactive Data Service with Caching

```javascript
// service/EquipmentService.js
import { apiClient } from './apiService';

class EquipmentService {
  constructor() {
    this.cache = {};
    this.cacheTime = 5 * 60 * 1000; // 5 minutes
  }

  async getAll(forceRefresh = false) {
    const cacheKey = 'allEquipment';
    
    // Return cached data if fresh
    if (!forceRefresh && this.cache[cacheKey]) {
      const { data, timestamp } = this.cache[cacheKey];
      if (Date.now() - timestamp < this.cacheTime) {
        return { data };
      }
    }

    // Fetch fresh data
    const response = await apiClient.get('/equipment');
    
    // Cache the result
    this.cache[cacheKey] = {
      data: response.data,
      timestamp: Date.now(),
    };

    return { data: response.data };
  }

  async getById(id) {
    const response = await apiClient.get(`/equipment/${id}`);
    return response.data;
  }

  async create(payload) {
    const response = await apiClient.post('/equipment', payload);
    // Invalidate cache on mutation
    delete this.cache['allEquipment'];
    return response.data;
  }

  async update(id, payload) {
    const response = await apiClient.put(`/equipment/${id}`, payload);
    delete this.cache['allEquipment'];
    return response.data;
  }

  async delete(id) {
    await apiClient.delete(`/equipment/${id}`);
    delete this.cache['allEquipment'];
  }

  invalidateCache(key = null) {
    if (key) {
      delete this.cache[key];
    } else {
      this.cache = {};
    }
  }
}

export const EquipmentService = new EquipmentService();
```

---

## Common Reactive Mistakes & Fixes

| Mistake | Problem | Fix |
|---|---|---|
| `const state = reactive({...}); state = {...}` | Breaks reactivity (reassign whole) | Use `ref` or mutate properties: `Object.assign(state, {...})` |
| Accessing `reactive()` without `.value` | Works but inconsistent | Use `ref` for consistency, or always mutate reactive properties |
| Watching `reactive()` without deep option | Nested changes not detected | Add `:watch("obj", ..., { deep: true })` |
| Computed inside event handler | Recomputes every time | Move to `setup()` level |
| `v-model` on derived computed | Can cause double-binding issues | Use `defineModel()` or getter/setter computed |
| Mutating props directly | Violates one-way data flow | Use `defineModel()` or emit update events |

---

## Checklist: Building a New FAMS Portal Feature

1. **Create composables first** (form state, lookups, payloads)
   - `useFeatureForm.js` — form data as `reactive`, validation methods
   - `useFeatureLookups.js` — dropdown/select options as `ref`
   - `useFeaturePayloads.js` — pure functions to build DTOs

2. **Design the page component** (`Feature.vue`)
   - Compose the form composable
   - Set up list state (DataTable, filters, pagination)
   - Call `onMounted(() => loadList())`

3. **Design the sidebar** (`FeatureSidebar.vue`)
   - Accept `formData`, `formErrors`, form methods via props/composable
   - Use PrimeVue components with `v-model` for two-way binding
   - Emit events for save/cancel

4. **Create Pinia store** (if needed for cross-feature state)
   - Setup store with `defineStore('featureName', () => {...})`
   - Export `ref`/`reactive` state and computed derived state
   - Actions call services and mutate state

5. **Test reactivity**
   - Verify form changes trigger validation re-renders
   - Verify list filters update `paginatedItems` computed
   - Verify Pinia mutations update UI immediately
   - No manual `$forceUpdate()` calls needed (Vue 3 doesn't have it)

---

## Performance Tips for Portal with Large Datasets

1. **Use `:lazy="true"` on DataTable** — load only visible page
2. **Use `virtualScrollerOptions`** for huge lists
3. **Computed over filters in template** — cache transformations
4. **Watch with debounce for search** — avoid firing on every keystroke
5. **Lazy load routes** — `() => import('@/views/...')`
6. **Use `storeToRefs()` when accessing Pinia** — avoid unnecessary reactivity wrapping

---

## Key Differences from Vue 2 FAMS App

| Vue 2 FAMS | Vue 3 Portal | Why Changed |
|---|---|---|
| Options API + `data()` | Composition API + `<script setup>` | Clearer, more reusable |
| Vuex modules (mutations/actions) | Pinia setup stores | Simpler, more functional |
| Props drilling + event emitting | Pinia + composables | Less prop clutter |
| Vuesax components | PrimeVue 4 | Modern, maintained, design-token-based |
| Global `Vue.filter()` | Composable functions + computed | Tree-shakeable, explicit |
| `$set` for dynamic props | Direct assignment (Proxy-based) | Automatic reactivity |
| Manual error handling | `apiService.js` centralized toasts | Consistent UX |
