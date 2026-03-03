import axios from 'axios'

// Create API instance with base configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor - attach JWT token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor - handle 401 by redirecting to login
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      localStorage.removeItem('mqtt_credentials')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API methods
const apiService = {
  // Auth endpoints
  login: (username, password) => api.post('/api/auth/login',
    new URLSearchParams({ username, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  ),
  register: (username, email, password) => api.post('/api/auth/register', { username, email, password }),
  getCurrentUser: () => api.get('/api/auth/me'),
  refreshToken: () => api.post('/api/auth/refresh'),
  getMqttCredentials: () => api.get('/api/mqtt/credentials'),

  // Health and status
  getHealth: () => api.get('/api/health'),
  getDatabaseStatus: () => api.get('/api/health'),

  // MQTT / Device endpoints
  getDevices: (activeOnly = true) => api.get(`/api/mqtt/devices?active_only=${activeOnly}`),
  getDeviceData: (deviceId, limit = 10) => api.get(`/api/mqtt/devices/${deviceId}/readings?limit=${limit}`),
  publishSensorData: (data) => api.post('/api/mqtt/readings', data),
  sendCommand: (command) => api.post('/api/mqtt/commands', command),
  getLatestData: (limit = 20) => api.get(`/api/mqtt/readings?limit=${limit}`),
  getLatestReadings: (limit = 20) => api.get(`/api/mqtt/readings?limit=${limit}`),
  getSensorTypeData: (sensorType, limit = 20) => api.get(`/api/mqtt/readings?limit=${limit}`),
  getRecentCommands: (limit = 20) => api.get(`/api/mqtt/commands?limit=${limit}`),
  getMqttDevices: (activeOnly = true) => api.get(`/api/mqtt/devices?active_only=${activeOnly}`),
  getMqttStats: () => api.get('/api/mqtt/stats'),
  getIotStats: () => api.get('/api/mqtt/stats'),

  // ACL endpoints
  getACLInfo: () => api.get('/api/acl/info'),
  getAllUsers: () => api.get('/api/acl/users'),
  createUser: (user) => api.post('/api/acl/users', user),
  getUser: (userId) => api.get(`/api/acl/users/${userId}`),
  updateUser: (userId, update) => api.put(`/api/acl/users/${userId}`, update),
  deleteUser: (userId) => api.delete(`/api/acl/users/${userId}`),
  getAllRoles: () => api.get('/api/acl/roles'),
  checkPermission: (check) => api.post('/api/acl/check', check),
  addUserPermission: (userId, permission) => api.post(`/api/acl/users/${userId}/permissions`, permission),
  reloadACL: () => api.post('/api/acl/reload'),
  getActiveSessions: () => api.get('/api/mqtt/sessions'),

  // SS endpoints
  getSSInfo: () => api.get('/api/ss/info'),
  getAllSensors: (checkActiveness) => api.get('/api/ss/sensors', {
    params: { check_activeness: checkActiveness }
  }),
  addSensor: (sensor) => api.post('/api/ss/sensors', sensor),
  getSensor: (sensorId) => api.get(`/api/ss/sensors/${sensorId}`),
  updateSensor: (sensorId, update) => api.put(`/api/ss/sensors/${sensorId}`, update),
  deleteSensor: (sensorId) => api.delete(`/api/ss/sensors/${sensorId}`),
  getAllTypes: () => api.get('/api/ss/types'),
  checkAlert: (check) => api.post('/api/ss/check', check),
  addLimitConfig: (sensorId, limit_config) => api.put(`/api/ss/sensors/${sensorId}/limits`, limit_config),
  reloadSS: () => api.post('/api/ss/reload'),
  getAlerts: () => api.get('/api/ss/alerts'),
  resolveAlert: (alertId) => api.post(`/api/ss/alerts/${alertId}/resolve`),
  revertAlert: (alertId) => api.post(`/api/ss/alerts/${alertId}/revert`),

  // User management (active sessions)
  getActiveUsers: () => api.get('/api/mqtt/sessions'),
}

export default apiService
