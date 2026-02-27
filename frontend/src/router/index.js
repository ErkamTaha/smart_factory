import { createRouter, createWebHistory } from '@ionic/vue-router';

const routes = [
  {
    path: '',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: 'Sign In',
      requiresAuth: false,
      guestOnly: true
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: {
      title: 'Create Account',
      requiresAuth: false,
      guestOnly: true
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: {
      title: 'Smart Factory Dashboard',
      requiresAuth: true
    }
  },
  {
    path: '/mqtt-test',
    name: 'MqttTest',
    component: () => import('@/views/MqttTestClient.vue'),
    meta: {
      title: 'MQTT Test & Management',
      requiresAuth: true
    }
  },
  {
    path: '/acl-management',
    name: 'ACLManagement',
    component: () => import('@/views/ACLManagement.vue'),
    meta: {
      title: 'ACL Management',
      requiresAuth: true
    }
  },
  {
    path: '/ss-management',
    name: 'SSManagement',
    component: () => import('@/views/SSManagement.vue'),
    meta: {
      title: 'Sensor Security Management',
      requiresAuth: true
    }
  },
  {
    path: '/sensor-details',
    name: 'SensorDetails',
    component: () => import('@/views/SensorDetails.vue'),
    meta: {
      title: 'Sensor Details',
      requiresAuth: true
    }
  },
  {
    path: '/device/:id',
    name: 'DeviceDetails',
    component: () => import('@/views/DeviceDetails.vue'),
    meta: {
      title: 'Device Details',
      requiresAuth: true
    }
  },
  {
    path: '/readings',
    name: 'AllReadings',
    component: () => import('@/views/AllReadings.vue'),
    meta: {
      title: 'All Sensor Readings',
      requiresAuth: true
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

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - Smart Factory`;
  } else {
    document.title = 'Smart Factory';
  }

  const isAuthenticated = !!localStorage.getItem('access_token')

  // Redirect authenticated users away from login/register
  if (to.meta.guestOnly && isAuthenticated) {
    next('/dashboard')
    return
  }

  // Redirect unauthenticated users to login
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
    return
  }

  next()
});

export default router;
