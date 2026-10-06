import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { setSessionExpiredHandler } from '@/service/apiService';

// Every route is lazy-loaded (fams-ui-standards §4). App routes nest under /main
// (fams-portal-master Part 5).
const routes = [
  { path: '/', redirect: '/main/dashboard' },
  { path: '/login', name: 'login', component: () => import('@/views/pages/auth/Login.vue'), meta: { requiresAuth: false } },
  {
    path: '/main',
    component: () => import('@/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/fams/dashboard/Dashboard.vue'),
        meta: { breadcrumb: [{ label: 'Dashboard' }] }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/pages/NotFound.vue') }
];

const router = createRouter({ history: createWebHistory(import.meta.env.BASE_URL), routes });

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.matched.some((r) => r.meta.requiresAuth) && !auth.isAuthenticated) {
    return { name: 'login', query: { to: to.fullPath } };
  }
  return true;
});

setSessionExpiredHandler(() => router.push({ name: 'login' }));

export default router;
