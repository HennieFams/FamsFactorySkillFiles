import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthService } from '@/service/AuthService';
import { useAuthStore } from '@/stores/authStore';

export function useLogin() {
  const router = useRouter();
  const auth = useAuthStore();
  const username = ref('');
  const password = ref('');
  const isSubmitting = ref(false);
  const error = ref('');

  async function submit() {
    error.value = '';
    if (!username.value.trim() || !password.value) {
      error.value = 'Username and password are required.';
      return;
    }
    isSubmitting.value = true;
    try {
      const data = await AuthService.authenticate(username.value.trim(), password.value);
      const entry = data?.value?.[0];
      if (!entry?.token) { error.value = 'Login failed.'; return; }
      auth.setSession({
        token: entry.token,
        userRoles: entry.userRoles,
        account: entry.account ? { accountId: entry.account.accountId, accountKey: entry.account.accountKey } : undefined
      });
      router.push(router.currentRoute.value.query.to || '/main/dashboard');
    } catch {
      error.value = 'Login failed.';
    } finally {
      password.value = '';
      isSubmitting.value = false;
    }
  }

  return { username, password, isSubmitting, error, submit };
}
