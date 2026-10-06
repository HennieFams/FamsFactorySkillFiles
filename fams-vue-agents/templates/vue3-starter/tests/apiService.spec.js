import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

const notify = vi.fn();
vi.mock('@/service/notify', () => ({ notify: (m) => notify(m), registerToast: () => {} }));

const { apiService, handleApiError, setSessionExpiredHandler } = await import('@/service/apiService');
const { useAuthStore } = await import('@/stores/authStore');

function adapterReturning(status, data = {}) {
  return vi.fn(async (config) => {
    if (status >= 200 && status < 300) return { data, status, statusText: 'OK', headers: {}, config };
    const err = new Error(`Request failed with status code ${status}`);
    err.config = config; err.response = { status, data, headers: {}, config }; err.isAxiosError = true;
    throw err;
  });
}

describe('apiService', () => {
  beforeEach(() => {
    sessionStorage.clear(); localStorage.clear(); notify.mockReset();
    setActivePinia(createPinia());
  });

  it('sends the legacy FAMS headers on every authenticated call', async () => {
    const auth = useAuthStore();
    auth.setSession({ token: 'T0K', userRoles: { id: 42 }, account: { accountId: 321, accountKey: 'AK' }, key: 'UK' });
    const adapter = adapterReturning(200, { ok: 1 });
    const data = await apiService.get('Ctrl/Act', { adapter });
    expect(data).toEqual({ ok: 1 });
    const h = adapter.mock.calls[0][0].headers;
    expect(h.Authorization).toBe('Bearer T0K');
    expect(h.userId).toBe('42');
    expect(h.accountId).toBe('321');
    expect(h.accountKey).toBe('AK');
    expect(h.userKey).toBe('UK');
  });

  it('sends no auth headers on the anonymous login call', async () => {
    useAuthStore().setSession({ token: 'T0K', userRoles: { id: 1 } });
    const adapter = adapterReturning(200, {});
    await apiService.postAnonymous('FAMSlegacy/Authenticate', { Username: 'a', Password: 'b' }, { adapter });
    expect(adapter.mock.calls[0][0].headers.Authorization).toBeUndefined();
  });

  it.each([401, 498])('clears the session and redirects on %i', async (status) => {
    const auth = useAuthStore();
    auth.setSession({ token: 'T0K', userRoles: { id: 1 } });
    const expired = vi.fn();
    setSessionExpiredHandler(expired);
    await expect(apiService.get('x', { adapter: adapterReturning(status, { title: 'T', message: 'M' }) })).rejects.toBeTruthy();
    expect(auth.isAuthenticated).toBe(false);
    expect(expired).toHaveBeenCalled();
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ severity: 'warn' }));
  });

  it.each([402, 403, 404, 405])('warns on %i', async (status) => {
    handleApiError({ response: { status, data: { title: 'T', message: 'M' } }, message: 'x' });
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ severity: 'warn', summary: 'T', detail: 'M' }));
  });

  it('errors on 429 and on network failure', () => {
    handleApiError({ response: { status: 429, data: {} }, message: 'x' });
    handleApiError({ message: 'Network Error' });
    expect(notify.mock.calls.map((c) => c[0].severity)).toEqual(['error', 'error']);
  });

  it('can stay silent', async () => {
    await expect(apiService.get('x', { adapter: adapterReturning(500), silent: true })).rejects.toBeTruthy();
    expect(notify).not.toHaveBeenCalled();
  });
});
