<script setup>
import { onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { registerToast } from '@/service/notify';

// apiService raises toasts through notify.js; the toast instance comes from here,
// because useToast() only works inside a component's setup().
const toast = useToast();
onMounted(() => registerToast(toast));
</script>

<template>
  <Toast />
  <ConfirmDialog />
  <RouterView />
</template>
