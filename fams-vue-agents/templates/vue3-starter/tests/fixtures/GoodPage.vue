<script setup>
import { useDashboardData } from '@/views/fams/dashboard/useDashboardData';
const { rows } = useDashboardData();
</script>
<template><div class="bg-fams-paper text-fams-charcoal">{{ rows.length }}</div></template>
