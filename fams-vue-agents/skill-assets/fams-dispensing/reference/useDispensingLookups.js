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
    return tanks.value.find(t => t.id === id); // fixed: was `e.id === id`
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
