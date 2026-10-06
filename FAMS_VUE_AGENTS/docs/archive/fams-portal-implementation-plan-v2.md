# FAMS Portal — Comprehensive Implementation Plan (v2)

This implementation plan provides a detailed, structured, and source-grounded blueprint for building the new front-end interface for the **Fixed Asset Management System (FAMS) Portal** using Vue 3 and PrimeVue 4. It translates the established development standards of the FAMS repository into a concrete roadmap for rolling out new modules, styling the user interface, managing state, and integrating with the back-end API.

---

## 1. Executive Summary & Objectives

The primary objective is to build a modern, secure, and highly responsive **FAMS Portal** front-end. The application is a Single Page Application (SPA) designed to serve internal and external stakeholders who track asset utilization, manage lifecycle states, run depreciation schedules, configure system workflows, and monitor fuel automation subsystems [113, 118, 142, 149]. 

This project adheres strictly to the existing codebase conventions of the FAMS ecosystem:
*   **Production-Ready Velocity**: Build with a clean, low-ceremony Composition API with zero TypeScript overhead [118, 149, 155].
*   **Accessibility First**: Fully WCAG-compliant design with keyboard navigation and screen reader support out-of-the-box via PrimeVue [34].
*   **Performance at Scale**: Optimized chunking, route-level lazy loading, and efficient rendering of large datasets using PrimeVue lazy data tables [131, 134, 137, 168].
*   **Cohesive Design System**: Styled using PrimeVue Lara preset, customized via design tokens, and paired with Tailwind CSS 4 utility classes [118, 122, 133, 164].

---

## 2. Architecture & Tech Stack

The portal leverages a modernized, lightweight frontend stack. By selecting high-efficiency, compiler-optimized tools, we eliminate context switching and minimize infrastructure overhead [116, 140, 171].

*   **Build Tooling & Scaffolding**: Powered by **Vite 5** for lightning-fast Hot Module Replacement (HMR) and optimized Rollup-based production builds [118, 130, 149].
*   **Core Framework**: **Vue 3.4** utilizing the **Composition API** and **`<script setup>`** compiler macros [118, 126, 149, 157]. The project is written in **plain JavaScript** (configured via `jsconfig.json`, no TypeScript) to remain consistent with core repository conventions [118, 124, 149, 155].
*   **State Management**: **Pinia 3**, organizing global states into single-domain stores (e.g., `authStore.js`), with complex derived logic cleanly separated into lightweight sibling utilities [118, 120, 123, 131, 151, 154, 162].
*   **Routing**: **Vue Router 4** for client-side navigation, managing nested views and protecting pathways via a unified global navigation guard [118, 123, 153, 154].
*   **UI Components**: **PrimeVue 4** styled mode, leveraging Lara preset design tokens and auto-imported on-demand using `unplugin-vue-components` to eliminate setup boilerplate and keep bundle sizes small [3, 118, 133, 164].
*   **Styling**: **Tailwind CSS 4** for rapid, utility-first custom layouts, running alongside PrimeVue themed elements under a structured CSS Cascade Layer [118, 122, 133, 164].

---

## 3. Directory Layout & Repository Conventions

To maintain consistency and prevent file layout fragmentation, all portal code must be organized according to the established FAMS-UI folder mapping [117, 118, 151].

```
FAMS-UI/
├── src/
│   ├── assets/             # styles.scss, tailwind.css, and custom theme tokens [120, 151]
│   ├── components/         # Shared generic UI elements (dashboard, landing widgets) [120, 151]
│   ├── composables/        # Cross-cutting reusable composition utilities [120, 128, 151, 159]
│   ├── layout/             # AppLayout, AppSidebar, AppTopbar, AppMenu(Item), AppConfig [120, 151]
│   ├── router/
│   │   └── index.js        # The single, consolidated router file for ALL paths [120, 122, 151, 153]
│   ├── service/
│   │   ├── apiService.js   # Centralized axios client instance with auto-toasts [120, 122, 151, 153]
│   │   └── AssetService.js # Entity-specific API communication definitions [122, 151, 153]
│   ├── stores/
│   │   ├── authStore.js    # Pinia store managing user session, roles, and portals [120, 123, 151, 154]
│   │   └── roleAccess.js   # Sibling helper holding derived routing/role calculations [120, 123, 151, 154]
│   └── views/
│       ├── pages/auth/     # Login, Register, LockScreen, AccessDenied, etc. [120, 151]
│       └── fams/           # Domain-specific portal feature modules [151]
│           ├── dashboard/  # Financial and utilization dashboards
│           ├── assets/     # Asset inventory lists and create/edit forms
│           ├── tanks/      # Fuel storage tanks monitoring & telemetry
│           └── workflows/  # Interactive lifecycle diagrams (Vue Flow) [122, 153]
```

### The FAMS Feature-Module Split Rule
Every domain feature placed under `src/views/fams/<feature>/` must be split into dedicated components and composables rather than being dumped into a single monolithic file [121, 124, 152, 155].

1.  **`<Feature>.vue`**: The main landing or listing page for that module (contains the search inputs, data grids, and high-level layout) [121, 122, 152].
2.  **`<Feature>Sidebar.vue`**: A collapsible PrimeVue Drawer (formerly *Sidebar* in v3) containing forms to create, update, or inspect details of the entity [121, 134, 138, 152, 169].
3.  **`use<Feature>Form.js`**: A stateful composable managing form input reactivity, validation rules, and submission statuses [121, 136, 152, 167].
4.  **`use<Feature>Lookups.js`**: A composable wrapping dropdown option retrievals, category lists, and static options [121, 152].
5.  **`use<Feature>Payloads.js`**: A plain JS utility file that houses logic to shape and transform reactive form states into the exact schema expected by the back-end API [121, 122, 152, 153].

---

## 4. Domain Core Implementations: Tanks & Telemetry Subsystem

FAMS Portal integrates with the localized physical IoT and Edge gateways to supervise fuel storage tanks and interpret telemetry streams [1, 10, 17]. This domain requires rigorous mathematical modeling and strict status guardrails.

### 4.1. Physical Volume Calculations (Horizontal Cylindrical Tanks)
Buried retail and commercial cylindrical tanks have non-linear volume curves. The frontend must implement two computational modes to convert wet product depth height ($h$) into physical Liters [13]:

#### Mode A: The Geometric Segment Formula (Exact Mathematical Model)
For a horizontal cylinder of radius $R$ and length $L$, the fuel volume at a wet height depth $h$ (where $0 \le h \le 2R$) is calculated as [13, 14]:
1.  **Circular Segment Angle ($\theta$ in radians)**:
    $$\theta = 2 \cdot \arccos\left(\frac{R - h}{R}\right)$$
2.  **Segment Cross-Sectional Area ($A$)**:
    $$A = \frac{1}{2} R^2 (\theta - \sin\theta)$$
3.  **Total Wet Volume ($V_{raw}$ in cubic meters)**:
    $$V_{raw} = A \cdot L$$
4.  **Liters Normalization ($V_{liters}$)**:
    $$V_{liters} = V_{raw} \cdot 1000$$

#### Mode B: Strapping Table Interpolation (Operational Fallback)
For tilted, deformed, or non-uniform tanks, the system falls back to **Linear Interpolation** against a calibrated strapping table [14]. Given strapping coordinates $(h_1, V_1)$ and $(h_2, V_2)$ where $h_1 \le h_{current} \le h_2$, the current volume $V_{current}$ is [15]:
$$V_{current} = V_1 + \frac{h_{current} - h_1}{h_2 - h_1} \cdot (V_2 - V_1)$$

### 4.2. Capacity Percentage & Alert Thresholds
To prevent environmental and physical hazards, the working threshold of the tank is capped at a strict **Safe Fill Limit of 95% of nominal tank volume** [15, 16]:
$$\text{Capacity \%} = \frac{\text{Current Volume}}{\text{Total Safe Fill Capacity}} \cdot 100$$

The system evaluates Capacity Percentage ($\text{Cap\%}$) to drive real-time dashboard notifications, tag styles, and visual alarm severities [16]:
*   **$\text{Cap\%} \ge 95.0\%$**: **Critical** state (Red flashing UI, dispatching Overfill Lockout Event) [16].
*   **$85.0\% \le \text{Cap\%} < 95.0\%$**: **Warning** state (Amber UI, dispatching High Fill Alert) [16].
*   **$15.0\% < \text{Cap\%} < 85.0\%$**: **Healthy** state (Emerald UI, Standard Operation) [16].
*   **$5.0\% < \text{Cap\%} \le 15.0\%$**: **Warning** state (Amber UI, dispatching Low Fill Run-out Alert) [16].
*   **$\text{Cap\%} \le 5.0\%$**: **Critical** state (Red UI, dispatching Critical Run-out Event) [16].

### 4.3. Automatic Tank Gauge (ATG) Telemetry & ASCII Framing
For **Pilot #1 (Tank Communication & Health Card)**, telemetry streams communicate with edge physical devices over RS-232/RS-485 serial buses (locked to **9600 Baud, 8 Data Bits, No Parity, 1 Stop Bit / 9600 8N1**) or TCP/IP remote socket clients (with a max of 3 retries, exponential backoff, and a **5000ms** socket timeout) [3, 4].

The parser interprets ASCII control framing modeled after the **Veeder-Root S90 protocol** [4]:
*   **`<SOH>` (Start of Header)**: `0x01` [4]
*   **`<ETX>` (End of Text)**: `0x03` [4]
*   **Checksum Verification**: A 4-character hex checksum appended after `<ETX>`, which is the bitwise XOR sum of all bytes starting *after* `<SOH>` up to and including `<ETX>` [4].
*   **Unit Standardization**: The portal parses the fixed-width columns of the `i20100` command response (In-Tank Fuel Inventory) and normalizes metrics: Volumes to Liters, Heights to Millimeters, and Temperatures to Celsius [5, 7].

### 4.4. Telemetry Fault Shielding & Watchdog Bounds
To protect systems from hardware-induced noise, the application enforces the following behaviors [8]:
*   **Communication Watchdog**: If the duration between the gateway UTC time and the `LastAtgUpdate` timestamp exceeds **10 minutes**, the system sets `communicationStatus = 'Offline'`, overrides the warning text to *"ATG Telemetry Offline for >10 mins."*, and alerts the maintenance dispatch [17].
*   **Simulated Data Flags**: If the metadata flags `isSimulated === true`, the UI tag must display **`[EMULATED]`** and log files are annotated to avoid sending physical technicians to a site during emulated dry-runs [17].

---

## 5. Feature Roadmap & PrimeVue 4 Component Mapping

The FAMS Portal is divided into four critical functional areas. Below is the mapping of each feature's functional requirements to specific PrimeVue 4 components [134, 165].

### 5.1. Core Asset Inventory & Auditing
Users need to view their complete register of fixed assets, search with multiple parameters, sort columns, and inspect individual item logs [134].
*   **Component Configuration**:
    *   **`DataTable` + `Column`**: Display asset lists. Enable `:lazy=\"true\"` to run pagination, sorting, and filtering on the server side [134, 137, 165, 168]. Add `:stripedRows=\"true\"` and `:rowHover=\"true\"` to enhance grid scanning readability [137, 168].
    *   **`Drawer`** (renamed from *Sidebar* in v4): Slide out from the right of the screen when creating or editing an asset, ensuring users do not lose their current filter state on the main table [121, 134, 138, 165, 169].
    *   **`DatePicker`** (renamed from *Calendar* in v4): Selection of acquisition, warranty expiration, and audit dates [134, 138, 165, 169].
    *   **`Select`** (renamed from *Dropdown* in v4): Choosing asset status, locations, or assigning departments [134, 138, 165, 169].

### 5.2. System Workflows & Interactive Lifecycle Diagrams
FAMS must visualize the progression of an asset through its operational lifecycle (e.g., *Procured* $\rightarrow$ *Active* $\rightarrow$ *Maintenance* $\rightarrow$ *Depreciated* $\rightarrow$ *Disposed*) [122, 142, 150].
*   **Component Configuration**:
    *   **`@vue-flow/core`**: Run interactive nodes and edges that represent the asset lifecycle [122, 153].
    *   **`Controls` + `MiniMap` + `Background`**: Standard navigation and styling panels for flow diagrams [122, 153].
    *   **`Custom Node Components`** (e.g., `UsageFlowNode.vue`): Tailored HTML templates for rendering nodes with custom indicators like asset count, current cost, or health status [122, 153].

### 5.3. Financial Tracking & Depreciation Models
Financial administrators require access to historical depreciation schedules, cost center summaries, and asset procurement timelines [11, 142, 153].
*   **Component Configuration**:
    *   **`Timeline`**: Render historical cost events, audits, and upgrades in chronological order next to a graphical vertical stem [10, 41, 165].
    *   **`Accordion` / `AccordionTab`**: Group complex calculations (e.g., Straight-Line, Double Declining, Units of Production) into collapsible panels, letting accountants focus on one calculation sheet at a time [11, 12, 165].
    *   **`Tabs` / `TabPanel` / `TabList`** (v4 API): Replaces older v3 TabViews. Used to segment data tables between active depreciations, historical models, and asset disposals [12, 134, 138, 165, 169].

### 5.4. Management Dashboards & Executive Reports
High-level executives need visual widgets summarizing total portfolio valuation, net cash flow, risk score distributions, and pending approvals [1, 142].
*   **Component Configuration**:
    *   **`Card`**: Standardized, flexible layouts for stat banners displaying total balance, net flow, and active risk scores [1, 11, 165].
    *   **`Chart`**: Thin, canvas-based Chart.js wrapper representing portfolio trends, cost center distributions, and monthly depreciation trajectories [9, 134, 165].
    *   **`MeterGroup`**: Scalar layout visualizing asset risk ratios or category distributions within a closed 100% stack bar [18, 33, 165].

---

## 6. Implementation Blueprints & Integration Patterns

### 6.1. The API Integration Layer (`src/service/`)
Do not instantiate independent axios clients. All services must route through the single unified `apiClient` defined in `apiService.js` to ensure the application retains centralized error-toasters and default baseUrl configs [122, 124, 153, 155].

```javascript
// src/service/AssetService.js
import { apiClient } from './apiService';

export const AssetService = {
  // Fetch active assets with support for server-side lazy loading [134, 137, 168]
  getAssets(params) {
    return apiClient.get('/assets', { params });
  },

  getAssetById(id) {
    return apiClient.get(`/assets/${id}`);
  },

  createAsset(payload) {
    return apiClient.post('/assets', payload);
  },

  updateAsset(id, payload) {
    return apiClient.put(`/assets/${id}`, payload);
  },

  deleteAsset(id) {
    return apiClient.delete(`/assets/${id}`);
  }
};
```

### 6.2. Tank Telemetry S90 Parser Composable (`src/views/fams/tanks/`)
This composable handles S90 ASCII data parsing, checksum evaluation, and state modeling [4, 7, 152].

```javascript
// src/views/fams/tanks/useTankTelemetry.js
import { ref } from 'vue';

export function useTankTelemetry() {
  const parsedData = ref(null);
  const parseError = ref(null);

  // Calculates Veeder-Root XOR Checksum [4]
  function calculateXORChecksum(payload) {
    let checksum = 0;
    for (let i = 0; i < payload.length; i++) {
      checksum ^= payload.charCodeAt(i);
    }
    return checksum.toString(16).toUpperCase().padStart(4, '0');
  }

  function parseS90Frame(rawFrame) {
    try {
      parseError.value = null;
      
      // 1. Framing Checks [7]
      const sohIndex = rawFrame.indexOf('\x01');
      const etxIndex = rawFrame.indexOf('\x03');
      if (sohIndex === -1 || etxIndex === -1 || etxIndex < sohIndex) {
        throw new Error('Frame is missing SOH or ETX control character boundaries.');
      }

      // 2. Extract Parts [4]
      const payload = rawFrame.substring(sohIndex + 1, etxIndex + 1); // XOR sum includes ETX [4]
      const providedChecksum = rawFrame.substring(etxIndex + 1).trim();
      
      // 3. Verify Checksum [7]
      const computedChecksum = calculateXORChecksum(payload);
      if (computedChecksum !== providedChecksum) {
        throw new Error(`XOR Checksum Mismatch. Computed: ${computedChecksum}, Received: ${providedChecksum}`);
      }

      // 4. Tokenization & Positional Slicing (e.g. Command i20100) [5, 7]
      const lines = rawFrame.substring(sohIndex + 1, etxIndex).split('\n');
      if (lines.length < 4) {
        throw new Error('Incomplete S90 Response format.');
      }

      // Find the row representing Tank 1 [5]
      const tankRow = lines.find(line => line.trim().startsWith('1'));
      if (!tankRow) throw new Error('Tank record not found in inventory payload.');

      // Extract by fixed-width columns [7]
      const parts = tankRow.trim().split(/\s+/);
      const volume = parseFloat(parts[2]);
      const height = parseFloat(parts[3]);
      const temp = parseFloat(parts[5]);
      const capacity = parseFloat(parts[6]);

      // Normalize physical properties [7]
      parsedData.value = {
        tankId: parseInt(parts[0]),
        productName: parts[1],
        currentVolume: volume,          // Normalized to Liters [7]
        fuelHeightMm: height,           // Normalized to Millimeters [7]
        temperatureCelsius: temp,       // Normalized to Celsius [7]
        capacityLiters: capacity,
        timestampUtc: new Date().toISOString()
      };
    } catch (err) {
      parseError.value = err.message;
      parsedData.value = null;
    }
  }

  return { parsedData, parseError, parseS90Frame };
}
```

---

## 7. Styling, Theming, and Brand Identity

The visual layer blends Tailwind's rapid layouts with PrimeVue's accessible UI widgets. Customizations are achieved globally through the preset token system rather than writing unstructured inline styles or fighting CSS hierarchy with `!important` [122, 133, 164].

*   **Design-Token Presets**: The project uses **PrimeVue 4 design-tokens** mapped to the **Lara preset** via `@primeuix/themes` [122, 133, 164].
*   **Theming Options**: Customizations to the brand primary palette, border radii, and paddings are defined programmatically at app bootstrap using `definePreset()` overrides [164]:
    ```javascript
    import { definePreset } from '@primeuix/themes';
    import Lara from '@primeuix/themes/lara';

    const MyFamsPreset = definePreset(Lara, {
        semantic: {
            primary: {
                50: '{indigo.50}',
                100: '{indigo.100}',
                500: '{indigo.500}',
                600: '{indigo.600}',
                900: '{indigo.900}'
            }
        }
    });
    ```
*   **Dark Mode Support**: Dark mode is controlled by appending the `.app-dark` selector to the HTML element. Ensure the PrimeVue configuration options are set accordingly during setup [122, 133, 164]:
    ```javascript
    options: { darkModeSelector: '.app-dark' }
    ```
*   **Custom Sidebar Integration**: The \"engineering-blueprint\" dark industrial sidebar utilizes `assets/layout/_fams_sidebar_theme.scss` combined with the background SVGs stored in `/public/` [122, 153]. This is custom repository SCSS and does not conflict with PrimeVue's layer emissions [122, 133, 164].
*   **Icons**: Standardize on **PrimeIcons** (`pi pi-<name>`) for all menus, action buttons, and navigation nodes to ensure class-based icon consistency [138, 169].

---

## 8. Quality Gates & Release Roadmap

The migration and rollout of the FAMS Portal is divided into four distinct phases to manage risk, ensure complete test coverage, and prevent regression [176].

### Phase 1: Prepare (Estimated: 2 Weeks) [176, 201]
*   Establish Vite build setup and verify auto-import resolvers are active [118, 133, 164].
*   Configure **ESLint** with Vue 3 rules (`.eslintrc.cjs`) to detect and block deprecations before they enter the branch [124, 149, 155, 180].
*   Pre-declare component event outputs using `defineEmits` upfront to satisfy Vue 3 requirements [126, 150, 181].

### Phase 2: Feature Development (Estimated: 4 Weeks) [176, 201]
*   Implement the core layouts, top bar, sidebar, and breadcrumb structures under the `/main` route using `AppLayout.vue` [120, 122, 123, 151].
*   Scaffold the FAMS feature views utilizing the page + sidebar + composable architectural split [121, 124, 152].
*   Verify that reactivity is strictly preserved by using `ref()` for composable returns and avoiding destructured references of raw `reactive()` objects [125, 126, 156, 157].

### Phase 3: Bug Bash & Quality Assurance [190]
*   Invite development and product teams to run manual test cycles in an isolated development sandbox [190, 191].
*   Monitor browser console outputs for PrimeVue deprecation warnings or layout misalignments caused by Vue 3 whitespace handling optimizations [144, 157, 158, 189].
*   Ensure that any reactive updates bound to objects or nested arrays are properly tracked (opt-out of deep reactivity via `shallowRef` only when handling extremely heavy, immutable datasets) [100, 125, 131, 133, 156].

### Phase 4: Production Deployment [176, 200]
*   Compile production-ready bundles to the `./dist` directory using `npm run build` [43, 44, 124, 155].
*   Integrate global router guards to safely map permissions, redirecting unauthenticated traffic to `/login` and parsing meta-roles cleanly [120, 123, 154].
*   Set up rolling A/B canary distributions if possible, keeping rollback pathways active in case of production exceptions [176, 200, 201].
