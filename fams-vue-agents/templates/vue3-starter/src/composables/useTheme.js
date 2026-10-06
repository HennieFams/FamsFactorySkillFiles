import { ref } from 'vue';

const KEY = 'fams-theme';
const isDark = ref(false);

function apply(dark) {
  isDark.value = dark;
  document.documentElement.classList.toggle('app-dark', dark);
}

export function applySavedTheme() {
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch { /* blocked */ }
  apply(saved === 'dark');
}

export function useTheme() {
  function toggle() {
    apply(!isDark.value);
    try { localStorage.setItem(KEY, isDark.value ? 'dark' : 'light'); } catch { /* blocked */ }
  }
  return { isDark, toggle };
}
