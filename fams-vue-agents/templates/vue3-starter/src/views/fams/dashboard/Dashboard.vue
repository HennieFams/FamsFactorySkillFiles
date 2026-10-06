<script setup>
import { onMounted } from 'vue';
import StatusTag from '@/components/shared/StatusTag.vue';
import { useDashboardData } from './useDashboardData';

const { rows, isLoading, loadedAt, totalVolume, load } = useDashboardData();

function monthRange() {
  const now = new Date();
  const iso = (d) => d.toISOString().slice(0, 10);
  return { fromDate: iso(new Date(now.getFullYear(), now.getMonth(), 1)), toDate: iso(new Date(now.getFullYear(), now.getMonth() + 1, 0)) };
}

onMounted(() => load(monthRange()));
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="fams-eyebrow">01 / Overview</p>
      <h1 class="text-3xl font-bold uppercase">Dashboard</h1>
    </header>

    <div class="grid gap-4 md:grid-cols-3">
      <div class="fams-panel p-4">
        <p class="fams-eyebrow">Volume this month</p>
        <Skeleton v-if="isLoading && !rows.length" height="2.5rem" />
        <!-- "no data" is not zero (fams-ui-standards §2) -->
        <p v-else-if="!loadedAt" class="fams-heading text-4xl font-bold text-fams-steel">—</p>
        <p v-else class="fams-heading text-4xl font-bold">{{ totalVolume.toLocaleString() }} L</p>
        <p class="text-xs text-fams-steel">
          {{ loadedAt ? `Updated ${loadedAt.toLocaleTimeString()}` : 'No data loaded yet' }}
        </p>
      </div>
      <div class="fams-panel flex flex-wrap items-center gap-2 p-4">
        <StatusTag status="critical" />
        <StatusTag status="warning" />
        <StatusTag status="active" />
        <StatusTag status="healthy" />
        <StatusTag status="offline" />
      </div>
    </div>
  </section>
</template>
