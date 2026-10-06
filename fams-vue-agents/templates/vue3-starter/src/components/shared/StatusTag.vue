<script setup>
import { computed } from 'vue';

// fams-ui-standards §2 - the one way to show a status: colour + icon + label.
const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (v) => ['critical', 'warning', 'active', 'healthy', 'offline'].includes(v)
  },
  label: { type: String, default: '' },
  pulse: { type: Boolean, default: false }
});

const STYLES = {
  critical: { cls: 'bg-fams-orange-deep text-white', icon: 'pi pi-exclamation-triangle', text: 'CRITICAL' },
  warning: { cls: 'bg-fams-amber text-fams-charcoal', icon: 'pi pi-exclamation-circle', text: 'WARNING' },
  active: { cls: 'border border-fams-orange text-fams-orange', icon: 'pi pi-circle-fill', text: 'LIVE' },
  healthy: { cls: 'border border-fams-steel text-fams-steel', icon: 'pi pi-check', text: 'NORMAL' },
  offline: { cls: 'border border-dashed border-fams-fog text-fams-steel', icon: 'pi pi-ban', text: 'NO DATA' }
};

const style = computed(() => STYLES[props.status]);
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-bold uppercase tracking-wider"
    :class="[style.cls, { 'animate-pulse': pulse && status === 'critical' }]"
    role="status"
  >
    <i :class="style.icon" class="text-[0.7rem]" aria-hidden="true" />
    {{ label || style.text }}
  </span>
</template>
