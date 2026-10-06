import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

// Session values used by apiService headers (fams-ui-standards §3.4). Persisted the same
// way as legacy FAMS-UI (accessToken/roles in sessionStorage, account in localStorage),
// so a user logged in to the legacy portal and the new app share one session model.
function read(storage, key) {
  try { return storage.getItem(key); } catch { return null; }
}
function write(storage, key, value) {
  try {
    if (value === null || value === undefined || value === '') storage.removeItem(key);
    else storage.setItem(key, value);
  } catch { /* storage blocked - keep in memory only */ }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(read(sessionStorage, 'accessToken'));
  const roles = ref(safeJson(read(sessionStorage, 'roles')));
  const accountId = ref(read(localStorage, 'userAccountId'));
  const accountKey = ref(read(localStorage, 'userAccountKey'));
  const userKey = ref(read(localStorage, 'userKey'));

  const isAuthenticated = computed(() => !!accessToken.value);
  const userId = computed(() => roles.value?.id ?? null);

  function setSession({ token, userRoles, account, key }) {
    accessToken.value = token;
    roles.value = userRoles ?? null;
    write(sessionStorage, 'accessToken', token);
    write(sessionStorage, 'roles', userRoles ? JSON.stringify(userRoles) : null);
    if (account) setAccount(account);
    if (key !== undefined) { userKey.value = key; write(localStorage, 'userKey', key); }
  }

  function setAccount({ accountId: id, accountKey: k }) {
    accountId.value = id != null ? String(id) : null;
    accountKey.value = k ?? null;
    write(localStorage, 'userAccountId', accountId.value);
    write(localStorage, 'userAccountKey', accountKey.value);
  }

  function clear() {
    accessToken.value = null;
    roles.value = null;
    write(sessionStorage, 'accessToken', null);
    write(sessionStorage, 'roles', null);
  }

  // Header values in the legacy names the FAMS API expects.
  function headers() {
    const h = {};
    if (accessToken.value) h.Authorization = `Bearer ${accessToken.value}`;
    if (userId.value != null) h.userId = String(userId.value);
    if (accountId.value) h.accountId = accountId.value;
    if (accountKey.value) h.accountKey = accountKey.value;
    if (userKey.value) h.userKey = userKey.value;
    return h;
  }

  return { accessToken, roles, accountId, accountKey, userKey, isAuthenticated, userId, setSession, setAccount, clear, headers };
});

function safeJson(text) {
  try { return text ? JSON.parse(text) : null; } catch { return null; }
}
