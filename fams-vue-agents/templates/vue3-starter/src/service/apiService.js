// fams-ui-standards §3 - THE ONLY FILE THAT TALKS TO THE FAMS API.
// Port of legacy FAMS-UI main.js $ajaxGet/$ajaxPost/$ajaxPut/$ajaxDelete/$ajaxPostAny:
// same base URL, same headers, same status handling - in one place.
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { notify } from './notify';

let onSessionExpired = () => { window.location.assign('/login'); };
/** Router sets this once so 401/498 navigate without a full reload. */
export function setSessionExpiredHandler(fn) { onSessionExpired = fn; }

const client = axios.create({
  baseURL: import.meta.env.VITE_ROOT_API,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

client.interceptors.request.use((config) => {
  if (!config.anonymous) {
    const auth = useAuthStore();
    Object.assign(config.headers, auth.headers());
  }
  return config;
});

const WARN_STATUSES = new Set([402, 403, 404, 405]);

export function handleApiError(error) {
  if (axios.isCancel(error)) return; // superseded request - not an error
  const status = error.response?.status;
  const data = error.response?.data || {};
  const title = data.title || 'Error/Notification';
  const message = data.message || error.message;

  if (status === 401 || status === 498) {
    useAuthStore().clear();
    notify({ severity: 'warn', summary: title, detail: message });
    onSessionExpired();
  } else if (WARN_STATUSES.has(status)) {
    notify({ severity: 'warn', summary: title, detail: message });
  } else if (status === 429) {
    notify({ severity: 'error', summary: title, detail: message || 'Too many requests - please wait and try again.' });
  } else {
    notify({ severity: 'error', summary: status ? title : 'Network error', detail: message });
  }
}

// opts: params, signal (AbortController), anonymous (login only), silent (no toast),
// adapter (tests only).
async function request(method, path, { params, data, signal, anonymous = false, silent = false, adapter } = {}) {
  try {
    const res = await client.request({ method, url: path, params, data, signal, anonymous, ...(adapter ? { adapter } : {}) });
    return res.data;
  } catch (error) {
    if (!silent) handleApiError(error);
    throw error;
  }
}

/** Paths are 'Controller/Action', relative to VITE_ROOT_API. Returns response.data. */
export const apiService = {
  get: (path, opts) => request('get', path, opts),
  post: (path, data, opts = {}) => request('post', path, { ...opts, data }),
  put: (path, data, opts = {}) => request('put', path, { ...opts, data }),
  delete: (path, opts) => request('delete', path, opts),
  /** Unauthenticated POST (legacy $ajaxPostAny) - login only. */
  postAnonymous: (path, data, opts = {}) => request('post', path, { ...opts, data, anonymous: true })
};

export default apiService;
