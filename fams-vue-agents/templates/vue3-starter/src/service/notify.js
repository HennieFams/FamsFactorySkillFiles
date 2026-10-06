// App-level toast bus (fams-ui-standards §3.7). App.vue registers the PrimeVue toast
// instance once; apiService (and anything outside setup()) calls notify().
let toastInstance = null;
const pending = [];

export function registerToast(toast) {
  toastInstance = toast;
  while (pending.length) toastInstance.add(pending.shift());
}

export function notify({ severity = 'info', summary = '', detail = '', life = 5500 }) {
  const msg = { severity, summary, detail, life };
  if (toastInstance) toastInstance.add(msg);
  else pending.push(msg);
}
