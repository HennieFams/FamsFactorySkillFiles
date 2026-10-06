<script setup>
import { useLogin } from '@/composables/useLogin';

const { username, password, isSubmitting, error, submit } = useLogin();
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-fams-charcoal p-4">
    <form class="w-full max-w-sm space-y-4 rounded-md border border-fams-orange-glow bg-fams-graphite p-6 text-fams-paper" @submit.prevent="submit">
      <p class="fams-eyebrow">Fuel Intelligence</p>
      <h1 class="text-3xl font-bold uppercase">FAMS Login</h1>
      <div class="space-y-1">
        <label for="username" class="text-sm">Username</label>
        <InputText id="username" v-model="username" class="w-full" autocomplete="username" />
      </div>
      <div class="space-y-1">
        <label for="password" class="text-sm">Password</label>
        <Password v-model="password" input-id="password" class="w-full" input-class="w-full" :feedback="false" toggle-mask autocomplete="current-password" />
      </div>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <Button type="submit" label="Sign in" class="w-full" :loading="isSubmitting" />
    </form>
  </div>
</template>
