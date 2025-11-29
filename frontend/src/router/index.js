import { createRouter, createWebHistory } from '@ionic/vue-router';

const routes = [
  {
    path: '',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: {
      title: 'Smart Factory Dashboard',
      requiresAuth: false
    }
  },
  {
    path: '/mqtt-test',
    name: 'MqttTest',
    component: () => import('@/views/MqttTestClient.vue'),
    meta: {
      title: 'MQTT Test & Management',
      requiresAuth: false
    }
  },
  {
    path: '/acl-management',
    name: 'ACLManagement',
    component: () => import('@/views/ACLManagement.vue'),
    meta: {
      title: 'ACL Management',
      requiresAuth: false
    }
  },
  {
    path: '/ss-management',
    name: 'SSManagement',
    component: () => import('@/views/SSManagement.vue'),
    meta: {
      title: 'Sensor Security Management',
      requiresAuth: false
    }
  },
  {
    path: '/sensor-details',
    name: 'SensorDetails',
    component: () => import('@/views/SensorDetails.vue'),
    meta: {
      title: 'Sensor Details',
      requiresAuth: false
    }
  },
  {
    path: '/device/:id',
    name: 'DeviceDetails',
    component: () => import('@/views/DeviceDetails.vue'),
    meta: {
      title: 'Device Details',
      requiresAuth: false
    }
  },
  {
    path: '/readings',
    name: 'AllReadings',
    component: () => import('@/views/AllReadings.vue'),
    meta: {
      title: 'All Sensor Readings',
      requiresAuth: false
    }
  },
  // Redirect any unmatched routes to dashboard
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

// Navigation guards
router.beforeEach((to, from, next) => {
  // Set page title
  if (to.meta.title) {
    document.title = `${to.meta.title} - Smart Factory`;
  } else {
    document.title = 'Smart Factory';
  }

  // Authentication check (if needed in the future)
  if (to.meta.requiresAuth) {
    // Add authentication logic here
    const isAuthenticated = true; // Replace with actual auth check
    if (!isAuthenticated) {
      next('/login');
      return;
    }
  }

  next();
});

export default router;
