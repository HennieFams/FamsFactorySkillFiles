<script setup>
import { useTheme } from '@/composables/useTheme';

const { isDark, toggle } = useTheme();
</script>

<template>
  <header class="flex items-center justify-between border-b border-fams-fog bg-white px-4 py-3 dark:border-fams-steel dark:bg-fams-graphite">
    <span class="fams-eyebrow">FAMS Fuel Intelligence</span>
    <Button
      :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
      text
      rounded
      :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
      @click="toggle"
    />
  </header>
</template>
