<!-- src/views/fams/dispensing/DispensingDialog.vue -->
<script setup>
import { computed, watch } from 'vue';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import Select from 'primevue/select';
import InputNumber from 'primevue/inputnumber';
import InputText from 'primevue/inputtext';
import ProgressBar from 'primevue/progressbar';
import Message from 'primevue/message';
import { useDispensingForm } from './useDispensingForm';

const props = defineProps({
  visible: { type: Boolean, required: true },
  equipment: { type: Object, default: null },
  lookups: { type: Object, required: true }
});

const emit = defineEmits(['update:visible', 'dispense-success']);

// Dynamic dialog visibility
const showDialog = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
});

// Calculate current fuel percentage for the equipment
const fuelPercentage = computed(() => {
  if (!props.equipment) return 0;
  return Math.min(100, Math.round((props.equipment.currentLevel / props.equipment.limitLiters) * 100));
});

// ProgressBar color based on equipment fuel level
const fuelPercentageSeverity = computed(() => {
  const pct = fuelPercentage.value;
  if (pct <= 20) return 'danger';
  if (pct <= 50) return 'warn';
  return 'success';
});

// Composable-driven Quick Dispense Form
const { form, errors, isSubmitting, submitForm, resetForm } = useDispensingForm(
  props.lookups,
  (newTxn) => {
    emit('dispense-success', newTxn);
    showDialog.value = false;
  }
);

// Sync equipmentId to form when equipment prop changes
watch(
  () => props.equipment,
  (newVal) => {
    resetForm();
    if (newVal) {
      form.equipmentId = newVal.id;
    }
  },
  { immediate: true }
);
</script>

<template>
  <Dialog 
    v-model:visible="showDialog" 
    :header="equipment ? `Equipment Telemetry: ${equipment.name}` : 'Quick Dispensing Event'" 
    :style="{ width: '45rem' }" 
    modal 
    dismissableMask
    class="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 shadow-xl"
  >
    <div class="space-y-6 pt-2">
      <!-- 1. Equipment Telemetry Summary -->
      <div v-if="equipment" class="border border-slate-100 dark:border-slate-800 rounded-lg p-4 bg-slate-50/50 dark:bg-slate-950/20">
        <h3 class="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3">Live Metrics & Status</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono mb-4 text-slate-600 dark:text-slate-400">
          <div>ID: <span class="font-bold text-slate-900 dark:text-white">{{ equipment.id }}</span></div>
          <div>Type: <span class="font-bold text-slate-900 dark:text-white">{{ equipment.type }}</span></div>
          <div>Status: 
            <span 
              class="px-2 py-0.5 rounded text-[10px] font-bold"
              :class="equipment.status === 'Active' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'"
            >
              {{ equipment.status }}
            </span>
          </div>
          <div>Last Fueled: <span class="font-bold text-slate-900 dark:text-white">{{ equipment.lastFuelDate }}</span></div>
        </div>

        <div class="space-y-1.5">
          <div class="flex justify-between text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
            <span>Fuel Level Indicator:</span>
            <span>{{ equipment.currentLevel }} / {{ equipment.limitLiters }} Liters ({{ fuelPercentage }}%)</span>
          </div>
          <ProgressBar 
            :value="fuelPercentage" 
            :showValue="false" 
            class="h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden"
            :class="[
              fuelPercentageSeverity === 'danger' ? '[&>[role=progressbar]]:bg-red-500' :
              fuelPercentageSeverity === 'warn' ? '[&>[role=progressbar]]:bg-amber-500' : 
              '[&>[role=progressbar]]:bg-emerald-500'
            ]"
          />
        </div>
      </div>

      <!-- 2. Action Form Section -->
      <div class="space-y-4">
        <h3 class="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Execute Dispensing Action</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Fuel Source Dropdown -->
          <div class="flex flex-col gap-1.5">
            <label for="tankSelect" class="text-xs font-bold text-slate-600 dark:text-slate-400">Select Fuel Source Tank *</label>
            <Select 
              id="tankSelect"
              v-model="form.tankId" 
              :options="lookups.tanks.value" 
              optionLabel="name" 
              optionValue="id" 
              placeholder="Select Source Tank" 
              class="w-full text-sm border border-slate-200 dark:border-slate-800 rounded p-1.5 bg-white dark:bg-slate-950"
              :class="{ 'p-invalid border-red-500': errors.tankId }"
            >
              <template #option="slotProps">
                <div class="flex items-center justify-between w-full text-xs font-mono">
                  <span>{{ slotProps.option.name }}</span>
                  <span class="font-bold text-slate-500">({{ slotProps.option.currentLiters }} L Left)</span>
                </div>
              </template>
            </Select>
            <small v-if="errors.tankId" class="text-red-500 text-[11px] font-semibold">{{ errors.tankId }}</small>
          </div>

          <!-- Volume Input -->
          <div class="flex flex-col gap-1.5">
            <label for="volumeInput" class="text-xs font-bold text-slate-600 dark:text-slate-400">Volume to Dispense (Liters) *</label>
            <InputNumber 
              id="volumeInput"
              v-model="form.volume" 
              :min="0"
              :max="1000"
              :minFractionDigits="1"
              :maxFractionDigits="2"
              placeholder="0.00" 
              class="w-full text-sm"
              :class="{ 'p-invalid border-red-500': errors.volume }"
              :pt="{
                root: { class: 'border border-slate-200 dark:border-slate-800 rounded p-1.5 bg-white dark:bg-slate-950 w-full' },
                input: { class: 'border-none p-0 outline-none w-full bg-transparent' }
              }"
            />
            <small v-if="errors.volume" class="text-red-500 text-[11px] font-semibold">{{ errors.volume }}</small>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Operator signature field -->
          <div class="flex flex-col gap-1.5">
            <label for="operator" class="text-xs font-bold text-slate-600 dark:text-slate-400">Operator Initials/Name *</label>
            <InputText 
              id="operator"
              v-model="form.operator" 
              placeholder="e.g., J. Doe" 
              class="w-full text-sm border border-slate-200 dark:border-slate-800 rounded p-1.5 bg-white dark:bg-slate-950"
              :class="{ 'p-invalid border-red-500': errors.operator }"
            />
            <small v-if="errors.operator" class="text-red-500 text-[11px] font-semibold">{{ errors.operator }}</small>
          </div>

          <!-- Notes -->
          <div class="flex flex-col gap-1.5">
            <label for="notes" class="text-xs font-bold text-slate-600 dark:text-slate-400">Transaction Notes (Optional)</label>
            <InputText 
              id="notes"
              v-model="form.notes" 
              placeholder="e.g., Routine equipment top-off" 
              class="w-full text-sm border border-slate-200 dark:border-slate-800 rounded p-1.5 bg-white dark:bg-slate-950"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Controls -->
    <template #footer>
      <div class="flex justify-end gap-3 mt-4 pt-2 border-t border-slate-100 dark:border-slate-800">
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          severity="secondary" 
          outlined 
          class="border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm font-semibold rounded-lg"
          @click="showDialog = false" 
          :disabled="isSubmitting"
        />
        <Button 
          label="Authorize Dispense" 
          icon="pi pi-check" 
          severity="success" 
          class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 text-sm font-semibold rounded-lg flex items-center gap-1.5 shadow-sm"
          @click="submitForm" 
          :loading="isSubmitting"
        />
      </div>
    </template>
  </Dialog>
</template>
