# FAMS Vue 3 Developer Skill File (v2)

#### name: fams-vue3-portal-skill
#### description: Standard developer and LLM instruction sheet for building, extending, or maintaining features in the FAMS Portal (Vue 3, PrimeVue 4, Tailwind CSS 4, Pinia 3, Vite 5). It mandates project layout rules, component and composable modularization patterns, reactivity practices, and styling conventions.

---

## 1. FAMS-UI (Vue 3) Stack & Core Architecture

All frontend developments inside this repository must adhere to the following technological parameters [118, 149]:
*   **Core Framework**: **Vue 3.4** utilizing the **Composition API** with **`<script setup>`** compiler macros [118, 149, 157].
*   **Project Language**: Plain, standard **JavaScript** (configured via `jsconfig.json`, no TypeScript allowed!) [118, 124, 149, 155].
*   **Build Tooling**: **Vite 5** [118, 149].
*   **UI Framework**: **PrimeVue 4** styled mode, Lara preset, using the `@primeuix/themes` design-token engine [118, 133, 149, 164].
*   **Utility CSS**: **Tailwind CSS 4** [118, 149, 164].
*   **Routing**: **Vue Router 4** [118, 149, 153].
*   **Global State**: **Pinia 3** [118, 149, 162].

---

## 2. Directory Structure & Feature Splitting

Keep folders organized strictly by domain. Under `src/views/fams/`, every new feature must split its views, forms, and validation states into small, decoupled files [120, 121, 124, 151, 152]:

```
src/
  assets/            # styles.scss, tailwind.css, design token configurations [120, 133, 151, 164]
  components/        # Reusable global component library (e.g. ColumnFilterBar.vue) [120, 122, 151, 153]
  composables/       # Global cross-cutting composables [120, 128, 151, 159]
  layout/            # AppLayout.vue, AppSidebar.vue, etc. [120, 151]
  router/index.js    # Consolidates ALL routes. Children lazy-load under /main [120, 122, 123, 151, 153]
  service/           # Centralized axios apiClient & service definitions [120, 122, 151, 153]
  stores/            # Pinia stores (authStore.js) & pure sibling helpers [120, 123, 151, 154, 162]
  views/
    fams/            # Module folder mapping FAMS features [120, 151]
      <feature>/     # e.g., assets/ or inventory/ or tanks/ [121, 152]
        <Feature>.vue           # Main display & table grid component [121, 122, 152]
        <Feature>Sidebar.vue    # Creation, edit, or details drawer panel [121, 134, 138, 152, 165]
        use<Feature>Form.js     # Form input validation and state composition [121, 136, 152, 167]
        use<Feature>Lookups.js  # Category, status, and department selection sources [121, 152]
        use<Feature>Payloads.js # Translates form structure into API-compliant JSON [121, 122, 152, 153]
```

### The Feature-Module Split Principle
*   Never write a single monolithic `.vue` file containing list rendering, editing drawer, form validation, and payload formatting [124, 155, 163].
*   Keep markup files (`.vue`) focused entirely on template layout and rendering [121, 21].
*   Delegate state, formatting, and networking concerns to sidecar composables (`.js`) [121, 128, 159].

---

## 3. General Vue 3 Reactivity & `<script setup>` Conventions

### 3.1. Declaring Reactive State: `ref()` vs `reactive()`
Select the correct reactivity wrapper depending on use case [125, 156]:

| Reactivity API | Best Used For |
| :--- | :--- |
| **`ref()`** | Primitives (String, Number, Boolean), arrays, or single objects that may require complete reassignment (`myRef.value = newThing`) [125, 156]. |
| **`reactive()`** | Complex, deep objects or state collections mutated in place. **Warning**: Never reassign a `reactive()` object wholesale, or its reactivity connection is immediately broken [125, 132, 156, 163]. |
| **`computed()`** | Derived, read-only reactive properties. Never create side-effects or manually mutate refs within a watcher if a computed calculation can replace it [125, 132, 156, 163]. |
| **`shallowRef()`** | Very large immutable arrays (e.g. massive API response grids) to bypass deep observer performance overhead [125, 130, 131, 156]. |

```javascript
// Reactivity Preservation when Destructuring: [126]
const formState = reactive({ username: '', age: 0 });

// BAD: Destructuring directly breaks reactivity! [138]
const { username } = formState;

// GOOD: Use toRefs() to preserve reactivity links [123, 157]
const { username } = toRefs(formState);
```

### 3.2. Compiler Macros in `<script setup>`
*   `defineProps()`, `defineEmits()`, and `defineModel()` are compiler macros [126, 157].
*   Do **not** import them explicitly; they are automatically available during compilation [126, 157].
*   Never invoke them inside conditional branches, hooks, or nested functions [126, 157].
*   Use `defineModel()` (introduced in Vue 3.4) to streamline two-way component binding [118, 126, 157]:
    ```vue
    <!-- CustomInput.vue -->
    <script setup>
    const model = defineModel(); // Handled as reactive proxy [126, 157]
    </script>
    <template>
      <input v-model="model" class="border border-slate-300 rounded p-2" />
    </template>
    ```

---

## 4. PrimeVue 4 & Tailwind CSS 4 Styling Conventions

PrimeVue 4 uses a modern **design token** system (`@primeuix/themes`) that integrates perfectly with Tailwind layers [133, 164].

### 4.1. Core Styling Rules
1.  **Tailwind First**: Use utility classes for position, padding, layout spacing, and flex/grid systems [118, 122, 153, 164].
2.  **No Hand-written CSS overrides**: Avoid using CSS deep selectors (`:deep()`) or adding `!important` to force styling changes [133, 164].
3.  **PassThrough (`pt`) Prop**: Target internal sub-elements of any PrimeVue component to apply one-off styling adjustments [133, 164]:
    ```vue
    <p-button pt:root:class="bg-blue-500 hover:bg-blue-600 border-none rounded-lg" />
    ```
4.  **Dark Mode Integration**: Set `.app-dark` as the root dark-mode class on the top-level element [122, 133, 164]. Keep `darkModeSelector: '.app-dark'` inside the PrimeVue theme configuration at app setup [133, 164].
5.  **Icon Standard**: Use **PrimeIcons** class syntax (e.g., `<i class="pi pi-check" />` or `icon="pi pi-check"`) rather than nesting ad-hoc inline SVGs [138, 169].

### 4.2. PrimeVue 4 Component Map
When building views, map requirements to these PrimeVue 4 core elements [134, 165, 169]:

*   **Tables**: `DataTable` and `Column` [134, 165].
    *   Set `:lazy="true"` for large data sheets so paging, filter, and sort events trigger API queries [134, 137, 165, 168].
    *   Set `:stripedRows="true"` and `:rowHover="true"` to aid visual row tracking [137, 168].
*   **Form Inputs**:
    *   Text: `InputText`, `Textarea`, `InputNumber`, `Password` [134, 165].
    *   Dates: `DatePicker` (formerly *Calendar* in v3) [134, 138, 165, 169].
    *   Selection: `Select` (formerly *Dropdown* in v3), `MultiSelect`, `Checkbox`, `RadioButton`, `ToggleSwitch` [134, 138, 165, 169].
*   **Feedback & Messaging**:
    *   Toast notifications: `Toast` component + `useToast()` composable [134, 135, 165, 166].
    *   Form-level inline notices: `<Message severity="error">` pattern paired with validation outputs [134, 136, 165, 167].
*   **Overlays**:
    *   Dialog boxes: `Dialog` [134, 138, 165].
    *   Collapsible forms: `Drawer` (formerly *Sidebar* in v3) [134, 138, 165, 169].
    *   Tooltips: `v-tooltip` directive [136, 167].
*   **Confirmations**: `ConfirmDialog` + `useConfirm()` composable [134, 135, 165, 166]. Never use native browser window alerts for destructive changes [135].

---

## 5. State Management & Routing Architecture

### 5.1. Pinia 3 Setup Stores
*   Keep Pinia stores focused strictly on global, cross-cutting state concerns (e.g., authentication session, portal selections) [120, 123, 162].
*   Do **not** use global store keys to house local UI-only variables (like a sidebar open state or form field errors) [131, 162].
*   Adopt the **setup store** function syntax:
    ```javascript
    import { ref, computed } from 'vue';
    import { defineStore } from 'pinia';

    export const usePortalStore = defineStore('portal', () => {
      const activePortal = ref('fams-main');
      const portals = ref(['fams-main', 'fams-financials']);

      const currentPortalName = computed(() => {
        return activePortal.value === 'fams-main' ? 'Asset Management' : 'Financials';
      });

      function setPortal(name) {
        if (portals.value.includes(name)) {
          activePortal.value = name;
        }
      }

      return { activePortal, portals, currentPortalName, setPortal };
    });
    ```
*   If a store requires complex processing logic (like mapping permission flags, mapping default routes, etc.), extract that logic into a sibling helper file (e.g., `roleAccess.js`) and import it [120, 123, 131, 154, 162].

### 5.2. Unified Navigation Guard
All routes must be registered as lazy-loaded children nested under `/main` in `src/router/index.js` to ensure they inherit the global layouts and authorization middleware [120, 122, 123, 124, 151, 153, 154]:

```javascript
// src/router/index.js (Route Blueprint)
{
  path: '/main',
  component: () => import('@/layout/AppLayout.vue'), // Standard Shell [154]
  children: [
    {
      path: 'assets',
      name: 'fams-assets',
      component: () => import('@/views/fams/assets/Assets.vue'),
      meta: {
        requiresAuth: true,
        portal: 'fams-main',
        roles: ['Admin', 'Manager'],
        breadcrumb: [{ label: 'FAMS' }, { label: 'Asset Register' }]
      }
    }
  ]
}
```

---

## 6. Telemetry Parsing & Computational Standards (Tanks/ATG)

FAMS Portal developers must implement domain math and transport rules with absolute precision [11, 12].

### 6.1. Geometric Tank Volume Formula JS Implementation
To parse liquid depths inside horizontal cylindrical tanks, integrate this mathematical blueprint inside `useTankLookups.js` or `useTankPayloads.js` [13]:

```javascript
/**
 * Calculates current fuel volume inside a horizontal cylindrical tank [13]
 * @param {number} h - Current wet height depth in millimeters [12, 13]
 * @param {number} R - Tank physical radius in millimeters
 * @param {number} L - Tank physical length in millimeters
 * @returns {number} Normalized fuel volume in Liters [13]
 */
export function calculateCylinderVolume(h, R, L) {
  if (h <= 0) return 0.0;
  if (h >= 2 * R) {
    // Tank is completely full; calculate total volume
    const totalVolumeM3 = Math.PI * Math.pow(R / 1000, 2) * (L / 1000);
    return totalVolumeM3 * 1000;
  }

  // 1. Convert inputs from mm to meters
  const h_m = h / 1000;
  const R_m = R / 1000;
  const L_m = L / 1000;

  // 2. Segment angle theta in radians [13, 14]
  const theta = 2 * Math.acos((R_m - h_m) / R_m);

  // 3. Circular cross-sectional area [14]
  const area = 0.5 * Math.pow(R_m, 2) * (theta - Math.sin(theta));

  // 4. Raw volume in cubic meters [14]
  const volumeM3 = area * L_m;

  // 5. Convert to Liters [14]
  return volumeM3 * 1000;
}
```

### 6.2. Veeder-Root Checksum Validation (ASCII XOR)
When handling direct socket strings in custom gateway configurations, implement XOR logic:

```javascript
/**
 * Validates a raw Veeder-Root S90 ASCII telemetry packet [4]
 * @param {string} rawFrame - Raw string containing SOH, ETX, and 4-char hex checksum [4]
 * @returns {boolean} True if frame is uncorrupted and matching [7]
 */
export function validateAtgChecksum(rawFrame) {
  const sohIndex = rawFrame.indexOf('\x01'); // SOH
  const etxIndex = rawFrame.indexOf('\x03'); // ETX
  
  if (sohIndex === -1 || etxIndex === -1 || etxIndex < sohIndex) {
    return false;
  }

  // Extract payload between SOH (exclusive) and ETX (inclusive) [4]
  const payload = rawFrame.substring(sohIndex + 1, etxIndex + 1);
  const providedChecksum = rawFrame.substring(etxIndex + 1).trim();

  // XOR Sum of all characters in payload [4]
  let calculatedXor = 0;
  for (let i = 0; i < payload.length; i++) {
    calculatedXor ^= payload.charCodeAt(i);
  }

  const computedChecksum = calculatedXor.toString(16).toUpperCase().padStart(4, '0');
  return computedChecksum === providedChecksum;
}
```

---

## 7. Common Developer Anti-Patterns to Flag (PR Audit Checklist)

During Code Review, the AI Challenger and human Lead Developer must **REJECT** any Pull Requests showing these anti-patterns [124, 132, 155, 163]:

1.  **TypeScript Usage**: Any `.ts` file, typing declarations (`type`, `interface`), or type parameters (`<Type>`). The project is strictly standard JavaScript [118, 124, 149, 155].
2.  **Prop Mutation**: Child components mutating prop fields directly instead of emitting event changes or utilizing `defineModel()` [132, 157, 163].
3.  **Ad-hoc Axios Clients**: Declaring direct Axios calls inside services instead of routing queries through the centralized, unified `apiService.js` client [122, 124, 153, 155].
4.  **Mono-component Overload**: Placing table listings, filter menus, editing sidebars, and form logic inside a single monolithic `.vue` file [121, 124, 152, 155].
5.  **Watcher Abuse**: Excessive deep watchers (`{ deep: true }`) causing performance lag [158, 163]. Always convert derived logic to synchronous computed caches [125, 132, 156, 163].
6.  **Direct DOM Alteration**: Selecting and updating elements directly via Javascript (e.g. `document.querySelector`) instead of using Vue's reactive bindings and `nextTick()` [101, 132].
7.  **Reassigning `reactive()`**: Wholesale reassignment of a reactive object (`state = reactive({...})`), which breaks proxy tracking [125, 132, 156, 163]. Use `ref()` or `Object.assign()` [125, 132, 156].
