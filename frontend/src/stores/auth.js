import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiService from '../services/api'

export const useAuthStore = defineStore('auth', () => {
    // State
    const token = ref(localStorage.getItem('access_token') || null)
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
    const mqttCredentials = ref(JSON.parse(localStorage.getItem('mqtt_credentials') || 'null'))

    // Computed
    const isAuthenticated = computed(() => !!token.value)
    const username = computed(() => user.value?.username || '')

    // Actions
    const login = async (username, password) => {
        const response = await apiService.login(username, password)
        const { access_token } = response.data

        token.value = access_token
        localStorage.setItem('access_token', access_token)

        // Fetch user info after login
        await fetchUser()
        return response.data
    }

    const register = async (username, email, password) => {
        const response = await apiService.register(username, email, password)
        return response.data
    }

    const fetchUser = async () => {
        const response = await apiService.getCurrentUser()
        user.value = response.data
        localStorage.setItem('user', JSON.stringify(response.data))
        return response.data
    }

    const fetchMqttCredentials = async () => {
        const response = await apiService.getMqttCredentials()
        mqttCredentials.value = response.data
        localStorage.setItem('mqtt_credentials', JSON.stringify(response.data))
        return response.data
    }

    const logout = () => {
        token.value = null
        user.value = null
        mqttCredentials.value = null
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        localStorage.removeItem('mqtt_credentials')
    }

    return {
        token,
        user,
        mqttCredentials,
        isAuthenticated,
        username,
        login,
        register,
        fetchUser,
        fetchMqttCredentials,
        logout,
    }
})