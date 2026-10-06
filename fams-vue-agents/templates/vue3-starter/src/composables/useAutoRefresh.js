import { ref, onMounted, onBeforeUnmount } from 'vue';

// One shared auto-refresh (fams-quick-report §3.2, fams-ui-standards §4):
// polls every `intervalMs` while enabled, pauses while the browser tab is hidden.
export function useAutoRefresh(callback, intervalMs = 60000) {
  const enabled = ref(false);
  let timer = null;

  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function start() {
    stop();
    if (enabled.value && !document.hidden) timer = setInterval(callback, intervalMs);
  }
  function setEnabled(value) { enabled.value = value; start(); }
  function onVisibility() { if (document.hidden) stop(); else { if (enabled.value) callback(); start(); } }

  onMounted(() => document.addEventListener('visibilitychange', onVisibility));
  onBeforeUnmount(() => { stop(); document.removeEventListener('visibilitychange', onVisibility); });

  return { enabled, setEnabled };
}
