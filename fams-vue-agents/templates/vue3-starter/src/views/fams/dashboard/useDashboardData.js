import { ref, shallowRef, computed } from 'vue';
import { DispensingReportService } from '@/service/DispensingReportService';

// Data for the dashboard page comes ONLY through this composable (fams-ui-standards §3.2).
export function useDashboardData() {
  const rows = shallowRef([]);          // large read-only list -> shallowRef (§4)
  const isLoading = ref(false);
  const loadedAt = ref(null);
  let controller = null;

  const totalVolume = computed(() => rows.value.reduce((sum, r) => sum + (Number(r.Volume) || 0), 0));

  async function load(range) {
    controller?.abort();                // cancel a superseded request (§4)
    controller = new AbortController();
    isLoading.value = true;
    try {
      const data = await DispensingReportService.getLogbook(range, controller.signal);
      rows.value = Array.isArray(data) ? data : (data?.value ?? []);
      loadedAt.value = new Date();
    } catch {
      // apiService already told the user; keep the previous data on screen
    } finally {
      isLoading.value = false;
    }
  }

  return { rows, isLoading, loadedAt, totalVolume, load };
}
