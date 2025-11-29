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

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// API methods
const apiService = {
  // Health and status
  getHealth: () => api.get('/api/health'),
  getDatabaseStatus: () => api.get('/api/database/status'),

  // IoT endpoints
  getDevices: () => api.get('/api/iot/devices'),
  getDeviceData: (deviceId, limit = 10) => api.get(`/api/iot/data/${deviceId}?limit=${limit}`),
  publishSensorData: (data) => api.post('/api/iot/data', data),
  sendCommand: (command) => api.post('/api/iot/command', command),
  getLatestData: (limit = 20) => api.get(`/api/iot/latest?limit=${limit}`),
  getSensorTypeData: (type, hours) => api.get(`/api/iot/sensors/${sensor_type}`, type, hours),
  getRecentCommands: (limit = 20) => api.get(`api/iot/commands?limit=${limit}`),
  getIotStats: () => api.get(`api/iot/stats`),

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
  getActiveSessions: () => api.get('/api/acl/sessions'),

  // SS endpoints
  getSSInfo: () => api.get('/api/ss/info'),
  getAllSensors: (checkActiveness) => api.get('/api/ss/sensors', {
    params: { checkActiveness }
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

  // User management
  getActiveUsers: () => api.get('/api/users'),
}

export default apiService
