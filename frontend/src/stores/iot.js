import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiService from '../services/api'

export const useIotStore = defineStore('iot', () => {
  // State
  const devices = ref([])
  const latestSensorData = ref([])
  const activeUsers = ref([])
  const systemAlerts = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Health status
  const backendHealth = ref(null)
  const databaseStatus = ref(null)

  // Computed
  const deviceCount = computed(() => devices.value.length)
  const totalSensorReadings = computed(() => latestSensorData.value.length)
  const recentAlerts = computed(() => systemAlerts.value.slice(0, 3))

  const isHealthy = computed(() => {
    return backendHealth.value?.status === 'ok' &&
      databaseStatus.value?.status === 'connected'
  })

  // Actions
  const loadDevices = async () => {
    try {
      isLoading.value = true
      const response = await apiService.getDevices()
      devices.value = response.data.devices || []
    } catch (err) {
      error.value = err.message
      console.error('Failed to load devices:', err)
    } finally {
      isLoading.value = false
    }
  }

  const loadLatestData = async (limit = 20) => {
    try {
      const response = await apiService.getLatestData(limit)
      latestSensorData.value = response.data.data || []
    } catch (err) {
      error.value = err.message
      console.error('Failed to load latest data:', err)
    }
  }

  const loadActiveUsers = async () => {
    try {
      const response = await apiService.getActiveUsers()
      activeUsers.value = response.data.users || []
    } catch (err) {
      error.value = err.message
      console.error('Failed to load active users:', err)
    }
  }

  const checkHealth = async () => {
    try {
      const [healthResponse, dbResponse] = await Promise.all([
        apiService.getHealth(),
        apiService.getDatabaseStatus()
      ])

      backendHealth.value = healthResponse.data
      databaseStatus.value = dbResponse.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to check health:', err)
    }
  }

  const publishSensorData = async (data) => {
    try {
      const response = await apiService.publishSensorData(data)
      // Refresh latest data after publishing
      await loadLatestData()
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const sendCommand = async (command) => {
    try {
      const response = await apiService.sendCommand(command)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const addSystemAlert = (alert) => {
    systemAlerts.value.unshift({
      id: Date.now() + Math.random(),
      ...alert,
      timestamp: new Date().toISOString()
    })

    // Keep only last 20 alerts
    if (systemAlerts.value.length > 20) {
      systemAlerts.value = systemAlerts.value.slice(0, 20)
    }
  }

  const dismissAlert = (alertId) => {
    systemAlerts.value = systemAlerts.value.filter(alert => alert.id !== alertId)
  }

  const addSensorReading = (reading) => {
    latestSensorData.value.unshift({
      id: Date.now() + Math.random(),
      ...reading,
      timestamp: reading.timestamp || new Date().toISOString()
    })

    // Keep only last 50 readings
    if (latestSensorData.value.length > 50) {
      latestSensorData.value = latestSensorData.value.slice(0, 50)
    }
  }

  const refreshAll = async () => {
    await Promise.all([
      loadDevices(),
      loadLatestData(),
      loadActiveUsers(),
      checkHealth()
    ])
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    devices,
    latestSensorData,
    activeUsers,
    systemAlerts,
    isLoading,
    error,
    backendHealth,
    databaseStatus,

    // Computed
    deviceCount,
    totalSensorReadings,
    recentAlerts,
    isHealthy,

    // Actions
    loadDevices,
    loadLatestData,
    loadActiveUsers,
    checkHealth,
    publishSensorData,
    sendCommand,
    addSystemAlert,
    dismissAlert,
    addSensorReading,
    refreshAll,
    clearError
  }
})
