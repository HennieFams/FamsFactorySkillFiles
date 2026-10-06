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
      // Simulate API submit delay
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

      // Apply state update locally (Side effects)
      lookups.transactions.value.unshift(newTxn);

      // Deduct tank volume
      const selectedTank = lookups.tanks.value.find(t => t.id === form.tankId);
      if (selectedTank) {
        selectedTank.currentLiters -= Number(form.volume);
      }

      // Add to equipment current level
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

  return {
    form,
    errors,
    isSubmitting,
    submitForm,
    resetForm
  };
}
