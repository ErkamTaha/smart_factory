import axios from 'axios';

class ApiService {
    constructor() {
        this.api = axios.create({
            baseURL: 'http://localhost:8000', // Your FastAPI backend URL
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Request interceptor
        this.api.interceptors.request.use(
            (config) => {
                console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        // Response interceptor
        this.api.interceptors.response.use(
            (response) => {
                return response;
            },
            (error) => {
                console.error('API Error:', error.response?.data || error.message);
                return Promise.reject(error);
            }
        );
    }

    // Health check
    async checkHealth() {
        const response = await this.api.get('/api/health');
        return response.data;
    }

    // Get all devices
    async getDevices() {
        const response = await this.api.get('/api/iot/devices');
        return response.data;
    }

    // Get data for specific device
    async getDeviceData(deviceId, limit = 10) {
        const response = await this.api.get(`/api/iot/data/${deviceId}?limit=${limit}`);
        return response.data;
    }

    // Publish sensor data
    async publishSensorData(data) {
        const response = await this.api.post('/api/iot/data', data);
        return response.data;
    }

    // Send command to device
    async sendCommand(command) {
        const response = await this.api.post('/api/iot/command', command);
        return response.data;
    }

    // Get latest data from all devices
    async getLatestData(limit = 20) {
        const response = await this.api.get(`/api/iot/latest?limit=${limit}`);
        return response.data;
    }

    // Update base URL (useful for different environments)
    updateBaseURL(url) {
        this.api.defaults.baseURL = url;
    }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;