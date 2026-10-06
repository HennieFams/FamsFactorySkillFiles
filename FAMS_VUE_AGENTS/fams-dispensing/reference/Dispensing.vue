<!-- src/views/fams/dispensing/Dispensing.vue -->
<script setup>
import { ref, reactive } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import Card from 'primevue/card';
import ProgressBar from 'primevue/progressbar';
import { useDispensingLookups } from './useDispensingLookups';
import DispensingDialog from './DispensingDialog.vue';

// Toast Notifications Service
const toast = useToast();

// Ingest Lookups Data (Static / Real-time Telemetry Data)
const lookups = useDispensingLookups();

// Quick Dispense dialog management
const isDialogVisible = ref(false);
const selectedEquipment = ref(null);

// Search and Filter variables
const searchQuery = ref('');
const filters = reactive({
  global: { value: null }
});

// Trigger Dispensing Dialog for a specific equipment card
function handleQuickFuel(equipment) {
  if (equipment.status === 'Maintenance') {
    toast.add({
      severity: 'error',
      summary: 'Equipment Lockout',
      detail: `${equipment.name} is currently flagged as Maintenance. Lockout tags are active.`,
      life: 5000
    });
    return;
  }
  selectedEquipment.value = equipment;
  isDialogVisible.value = true;
}

// Open General Dispense Form
function handleGenericDispense() {
  selectedEquipment.value = null;
  isDialogVisible.value = true;
}

// Success callback from the dialog submission
function handleDispenseSuccess(txn) {
  toast.add({
    severity: 'success',
    summary: 'Dispensation Authorized',
    detail: `Successfully processed transaction ${txn.id}. ${txn.volume} L delivered to ${txn.equipmentName}.`,
    life: 5000
  });
}

// Delete / Void transaction confirmation
function handleVoidTransaction(data) {
  const targetIndex = lookups.transactions.value.findIndex(t => t.id === data.id);
  if (targetIndex !== -1) {
    lookups.transactions.value[targetIndex].status = 'Voided';
    toast.add({
      severity: 'warn',
      summary: 'Transaction Voided',
      detail: `Transaction ${data.id} has been voided. Telemetry balances are being updated.`,
      life: 4000
    });
  }
}
</script>

<template>
  <div class="space-y-8 p-6 bg-slate-50/30 dark:bg-slate-950/10 min-h-screen">
    <!-- Header Page Area -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-5">
      <div>
        <h1 class="text-2xl font-black text-slate-900 dark:text-white tracking-tight">FAMS Quick Dispensing Portal</h1>
        <p class="text-sm text-slate-500 mt-1">Real-time hardware telemetry matching, card-style fleet status indicators, and transaction logging.</p>
      </div>
      <Button 
        label="Log Manual Dispense" 
        icon="pi pi-plus" 
        class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-4 rounded-xl shadow-sm flex items-center gap-2 self-start md:self-auto text-sm"
        @click="handleGenericDispense"
      />
    </div>

    <!-- Active Fuel Sources (Tank Status Widget) -->
    <div class="space-y-3">
      <h2 class="text-xs font-bold text-slate-400 dark:text-slate-600 uppercase tracking-widest font-mono">Live Automated Fuel Source Levels</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          v-for="tank in lookups.tanks.value" 
          :key="tank.id" 
          class="border border-slate-200 dark:border-slate-800 rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between space-y-3"
        >
          <div class="flex items-start justify-between">
            <div>
              <span class="text-[10px] font-mono font-semibold text-slate-400 uppercase">{{ tank.id }} ({{ tank.product }})</span>
              <h3 class="font-bold text-slate-800 dark:text-slate-200 mt-0.5 text-sm">{{ tank.name }}</h3>
            </div>
            <Tag 
              :value="`${Math.round((tank.currentLiters / tank.capacity) * 100)}% Capacity`" 
              :severity="tank.currentLiters / tank.capacity < 0.2 ? 'danger' : tank.currentLiters / tank.capacity < 0.5 ? 'warn' : 'success'"
              class="font-semibold"
            />
          </div>
          <div class="space-y-1.5">
            <ProgressBar 
              :value="Math.round((tank.currentLiters / tank.capacity) * 100)" 
              :showValue="false" 
              class="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden [&>[role=progressbar]]:bg-emerald-500"
            />
            <div class="flex justify-between text-[11px] font-mono text-slate-500">
              <span>Remaining: <span class="font-bold text-slate-800 dark:text-white">{{ tank.currentLiters.toLocaleString() }} L</span></span>
              <span>Total Capacity: {{ tank.capacity.toLocaleString() }} L</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Card-Style Equipment Fleet -->
    <div class="space-y-3">
      <h2 class="text-xs font-bold text-slate-400 dark:text-slate-600 uppercase tracking-widest font-mono">Select Fleet Equipment for Direct Dispensation</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <Card 
          v-for="equipment in lookups.equipments.value" 
          :key="equipment.id" 
          class="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden flex flex-col justify-between transition-all duration-200 hover:shadow-md"
        >
          <template #title>
            <div class="flex items-start justify-between">
              <span class="text-[10px] font-mono text-slate-400">{{ equipment.id }}</span>
              <span 
                class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
                :class="equipment.status === 'Active' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'"
              >
                {{ equipment.status }}
              </span>
            </div>
            <h3 class="text-sm font-bold text-slate-800 dark:text-white mt-1 line-clamp-1 leading-tight">{{ equipment.name }}</h3>
            <p class="text-[10px] text-slate-500 font-mono">{{ equipment.type }}</p>
          </template>

          <template #content>
            <div class="space-y-2.5 py-2">
              <div class="flex justify-between text-[10px] font-mono">
                <span class="text-slate-500">Tank Fuel Limit:</span>
                <span class="font-bold text-slate-700 dark:text-slate-300">{{ equipment.limitLiters }} L</span>
              </div>
              <div class="space-y-1">
                <div class="flex justify-between text-[10px] font-bold text-slate-600 dark:text-slate-400">
                  <span>Current: {{ equipment.currentLevel }} L</span>
                  <span>{{ Math.round((equipment.currentLevel / equipment.limitLiters) * 100) }}%</span>
                </div>
                <ProgressBar 
                  :value="Math.round((equipment.currentLevel / equipment.limitLiters) * 100)" 
                  :showValue="false" 
                  class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden"
                  :class="[
                    (equipment.currentLevel / equipment.limitLiters) <= 0.2 ? '[&>[role=progressbar]]:bg-red-500' :
                    (equipment.currentLevel / equipment.limitLiters) <= 0.5 ? '[&>[role=progressbar]]:bg-amber-500' : 
                    '[&>[role=progressbar]]:bg-emerald-500'
                  ]"
                />
              </div>
            </div>
          </template>

          <template #footer>
            <div class="pt-2 border-t border-slate-100 dark:border-slate-800/80">
              <Button 
                :label="equipment.status === 'Maintenance' ? 'Under Maintenance' : 'Quick Dispense'" 
                :icon="equipment.status === 'Maintenance' ? 'pi pi-lock' : 'pi pi-cog'" 
                class="w-full text-xs py-1.5 font-bold rounded-lg border flex items-center justify-center gap-1"
                :class="[
                  equipment.status === 'Maintenance' 
                    ? 'border-slate-200 dark:border-slate-800 bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'border-slate-200 hover:border-emerald-600 hover:bg-emerald-50/10 text-slate-700 hover:text-emerald-500 dark:border-slate-800'
                ]"
                @click="handleQuickFuel(equipment)"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Data Table transaction log (CRUD style) -->
    <div class="space-y-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-sm font-bold text-slate-950 dark:text-white uppercase tracking-wider">Historical Transactions Log</h2>
          <p class="text-xs text-slate-500 mt-0.5">CRUD transaction management pipeline. Void actions revert calculated balances.</p>
        </div>
        
        <!-- Keyword search control -->
        <IconField iconPosition="left" class="self-start md:self-auto">
          <InputIcon>
            <i class="pi pi-search text-xs text-slate-400" />
          </InputIcon>
          <InputText 
            v-model="searchQuery" 
            placeholder="Search transactions..." 
            class="text-xs border border-slate-200 dark:border-slate-800 rounded-lg p-2 pl-8 bg-slate-50/50 dark:bg-slate-950/20"
          />
        </IconField>
      </div>

      <!-- PrimeVue 4 DataTable component -->
      <DataTable 
        :value="lookups.transactions.value" 
        class="text-xs font-mono mt-3"
        stripedRows
        rowHover
        paginator 
        :rows="5"
        v-model:filters="filters"
        :globalFilterFields="['id', 'equipmentName', 'operator', 'status', 'tankId']"
      >
        <Column field="id" header="Txn ID" style="width: 12%" />
        <Column field="timestamp" header="Timestamp" style="width: 18%" />
        <Column field="equipmentName" header="Equipment Name" style="width: 25%" />
        <Column field="tankId" header="Source Tank" style="width: 12%" />
        <Column field="volume" header="Volume (L)" style="width: 12%">
          <template #body="slotProps">
            <span class="font-bold text-slate-900 dark:text-white">{{ slotProps.data.volume.toFixed(1) }} L</span>
          </template>
        </Column>
        <Column field="operator" header="Operator" style="width: 13%" />
        <Column field="status" header="Status" style="width: 10%">
          <template #body="slotProps">
            <Tag 
              :value="slotProps.data.status" 
              :severity="slotProps.data.status === 'Completed' ? 'success' : 'danger'"
              class="text-[9px] tracking-wide"
            />
          </template>
        </Column>
        <Column header="Actions" :exportable="false" style="width: 10%">
          <template #body="slotProps">
            <Button 
              icon="pi pi-trash" 
              outlined 
              rounded 
              severity="danger" 
              class="h-6 w-6 p-0 border-red-500 text-red-500 hover:bg-red-500/10 rounded-full flex items-center justify-center"
              v-tooltip.top="'Void Transaction'"
              :disabled="slotProps.data.status === 'Voided'"
              @click="handleVoidTransaction(slotProps.data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Telemetry Gateway Alerts Message -->
    <Toast position="top-right" />

    <!-- Nested Component Dialog Popup -->
    <DispensingDialog 
      v-model:visible="isDialogVisible"
      :equipment="selectedEquipment"
      :lookups="lookups"
      @dispense-success="handleDispenseSuccess"
    />
  </div>
</template>
