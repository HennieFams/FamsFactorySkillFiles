import { createApp } from 'vue';
import { createPinia } from 'pinia';
import PrimeVue from 'primevue/config';
import ToastService from 'primevue/toastservice';
import ConfirmationService from 'primevue/confirmationservice';

import '@fontsource/oswald/500.css';
import '@fontsource/oswald/700.css';
import '@fontsource/roboto-condensed/400.css';
import '@fontsource/roboto-condensed/700.css';
import 'primeicons/primeicons.css';
import './assets/fams-theme.css';

import App from './App.vue';
import router from './router';
import { primeVueOptions } from './theme/famsPreset';
import { applySavedTheme } from './composables/useTheme';

applySavedTheme();

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, primeVueOptions)
  .use(ToastService)
  .use(ConfirmationService)
  .mount('#app');
