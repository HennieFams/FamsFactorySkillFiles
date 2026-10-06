<script setup>
const items = [
  { label: 'Dashboard', icon: 'pi pi-th-large', to: '/main/dashboard' }
];
</script>

<template>
  <nav class="hidden w-60 shrink-0 bg-fams-charcoal text-fams-paper md:block" aria-label="Main">
    <div class="fams-heading px-5 py-5 text-2xl font-bold uppercase tracking-wide">
      FAMS<span class="text-fams-orange">.</span>
    </div>
    <ul class="space-y-1 px-2">
      <li v-for="item in items" :key="item.to">
        <RouterLink
          :to="item.to"
          class="flex items-center gap-3 rounded-md px-3 py-2 text-sm uppercase tracking-wider hover:bg-fams-graphite"
          active-class="border-l-4 border-fams-orange bg-fams-graphite text-fams-orange"
        >
          <i :class="item.icon" aria-hidden="true" />
          {{ item.label }}
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
