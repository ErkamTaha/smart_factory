import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiService from '@/services/api';

export const useIotStore = defineStore('iot', () => {
    // State
    const devices = ref([]);
    const sensorData = ref({});
    const latestData = ref([]);
    const isLoading = ref(false);
    const error = ref(null);
    const isConnected = ref(false);

    // Computed
    const deviceCount = computed(() => devices.value.length);
    const totalReadings = computed(() => {
        return Object.values(sensorData.value).reduce((total, readings) => total + readings.length, 0);
    });

    // Actions
    const setLoading = (loading) => {
        isLoading.value = loading;
    };

    const setError = (errorMessage) => {
        error.value = errorMessage;
    };

    const clearError = () => {
        error.value = null;
    };

    // Check backend health
    const checkConnection = async () => {
        try {
            const health = await apiService.checkHealth();
            isConnected.value = health.status === 'ok';
            return health;
        } catch (err) {
            isConnected.value = false;
            setError('Failed to connect to backend');
            throw err;
        }
    };

    // Fetch all devices
    const fetchDevices = async () => {
        try {
            setLoading(true);
            clearError();

            const response = await apiService.getDevices();
            devices.value = response.devices;

            return response;
        } catch (err) {
            setError(`Failed to fetch devices: ${err.message}`);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Fetch data for specific device
    const fetchDeviceData = async (deviceId, limit = 10) => {
        try {
            setLoading(true);
            clearError();

            const response = await apiService.getDeviceData(deviceId, limit);
            sensorData.value[deviceId] = response.data;

            return response;
        } catch (err) {
            setError(`Failed to fetch data for ${deviceId}: ${err.message}`);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Fetch latest data from all devices
    const fetchLatestData = async (limit = 20) => {
        try {
            setLoading(true);
            clearError();

            const response = await apiService.getLatestData(limit);
            latestData.value = response.data;

            return response;
        } catch (err) {
            setError(`Failed to fetch latest data: ${err.message}`);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Publish sensor data
    const publishData = async (data) => {
        try {
            setLoading(true);
            clearError();

            const response = await apiService.publishSensorData(data);

            // Update local state
            await fetchLatestData();
            if (devices.value.includes(data.device_id)) {
                await fetchDeviceData(data.device_id);
            } else {
                // Add new device to list
                devices.value.push(data.device_id);
            }

            return response;
        } catch (err) {
            setError(`Failed to publish data: ${err.message}`);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Send command to device
    const sendCommand = async (command) => {
        try {
            setLoading(true);
            clearError();

            const response = await apiService.sendCommand(command);
            return response;
        } catch (err) {
            setError(`Failed to send command: ${err.message}`);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Get device data from local state
    const getDeviceData = (deviceId) => {
        return sensorData.value[deviceId] || [];
    };

    // Get latest reading for a specific device and sensor type
    const getLatestReading = (deviceId, sensorType) => {
        const deviceData = getDeviceData(deviceId);
        const filtered = deviceData.filter(reading => reading.sensor_type === sensorType);
        return filtered.length > 0 ? filtered[0] : null;
    };

    // Get unique sensor types for a device
    const getDeviceSensorTypes = (deviceId) => {
        const deviceData = getDeviceData(deviceId);
        const types = deviceData.map(reading => reading.sensor_type);
        return [...new Set(types)];
    };

    // Refresh all data
    const refreshAll = async () => {
        try {
            setLoading(true);
            await Promise.all([
                checkConnection(),
                fetchDevices(),
                fetchLatestData()
            ]);
        } catch (err) {
            console.error('Failed to refresh data:', err);
        } finally {
            setLoading(false);
        }
    };

    return {
        // State
        devices,
        sensorData,
        latestData,
        isLoading,
        error,
        isConnected,

        // Computed
        deviceCount,
        totalReadings,

        // Actions
        setLoading,
        setError,
        clearError,
        checkConnection,
        fetchDevices,
        fetchDeviceData,
        fetchLatestData,
        publishData,
        sendCommand,
        getDeviceData,
        getLatestReading,
        getDeviceSensorTypes,
        refreshAll
    };
});