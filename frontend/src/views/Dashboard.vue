<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-title>Smart Factory Dashboard</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                    <ion-button @click="showSettings = true">
                        <ion-icon :icon="settingsOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                    <!-- Connection Status -->
                    <ion-chip :color="connectionStatusColor" class="connection-status" @click="toggleConnection">
                        <ion-icon :icon="connectionStatusIcon"></ion-icon>
                        <ion-label>{{ connectionStatus }}</ion-label>
                    </ion-chip>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content :fullscreen="true">
            <!-- System Alerts Banner -->
            <div v-if="systemAlerts.length > 0" class="alerts-banner">
                <ion-card v-for="alert in recentAlerts" :key="alert.id" :color="getAlertColor(alert.level)"
                    class="alert-card">
                    <ion-card-content>
                        <div class="alert-header">
                            <ion-icon :icon="getAlertIcon(alert.level)"></ion-icon>
                            <span class="alert-level">{{ alert.level.toUpperCase() }}</span>
                            <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
                            <ion-button fill="clear" size="small" @click="dismissAlert(alert.id)">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </div>
                        <p class="alert-message">{{ alert.message }}</p>
                        <div v-if="alert.details" class="alert-details">
                            <small>{{ JSON.stringify(alert.details, null, 2) }}</small>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Loading State -->
            <div v-if="isLoading && !hasData" class="loading-container">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading dashboard data...</p>
            </div>

            <!-- Main Dashboard Content -->
            <div v-else>
                <!-- Overview Statistics -->
                <div class="stats-section">
                    <ion-grid>
                        <ion-row>
                            <ion-col size="6" size-md="3">
                                <ion-card class="stat-card">
                                    <ion-card-content>
                                        <div class="stat-content">
                                            <ion-icon :icon="hardwareChipOutline" class="stat-icon"
                                                color="primary"></ion-icon>
                                            <div class="stat-info">
                                                <h2>{{ deviceCount }}</h2>
                                                <p>Active Devices</p>
                                            </div>
                                        </div>
                                    </ion-card-content>
                                </ion-card>
                            </ion-col>

                            <ion-col size="6" size-md="3">
                                <ion-card class="stat-card">
                                    <ion-card-content>
                                        <div class="stat-content">
                                            <ion-icon :icon="peopleOutline" class="stat-icon"
                                                color="success"></ion-icon>
                                            <div class="stat-info">
                                                <h2>{{ activeUsers.length }}</h2>
                                                <p>Connected Users</p>
                                            </div>
                                        </div>
                                    </ion-card-content>
                                </ion-card>
                            </ion-col>

                            <ion-col size="6" size-md="3">
                                <ion-card class="stat-card">
                                    <ion-card-content>
                                        <div class="stat-content">
                                            <ion-icon :icon="barChartOutline" class="stat-icon"
                                                color="warning"></ion-icon>
                                            <div class="stat-info">
                                                <h2>{{ totalSensorReadings }}</h2>
                                                <p>Sensor Readings</p>
                                            </div>
                                        </div>
                                    </ion-card-content>
                                </ion-card>
                            </ion-col>

                            <ion-col size="6" size-md="3">
                                <ion-card class="stat-card">
                                    <ion-card-content>
                                        <div class="stat-content">
                                            <ion-icon :icon="shieldCheckmarkOutline" class="stat-icon"
                                                color="tertiary"></ion-icon>
                                            <div class="stat-info">
                                                <h2>{{ systemAlerts.length }}</h2>
                                                <p>System Alerts</p>
                                            </div>
                                        </div>
                                    </ion-card-content>
                                </ion-card>
                            </ion-col>
                        </ion-row>
                    </ion-grid>
                </div>

                <!-- Real-time Sensor Data -->
                <ion-card v-if="latestSensorData.length > 0">
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="thermometerOutline"></ion-icon>
                            Latest Sensor Readings
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="sensor-grid">
                            <div v-for="reading in latestSensorData.slice(0, 8)" :key="reading.id" class="sensor-item">
                                <div class="sensor-header">
                                    <span class="device-id">{{ reading.device_id }}</span>
                                    <ion-chip :color="getSensorStatusColor(reading)" size="small">
                                        {{ reading.sensor_type }}
                                    </ion-chip>
                                </div>
                                <div class="sensor-value">
                                    {{ reading.value }} <small>{{ reading.unit }}</small>
                                </div>
                                <div class="sensor-time">{{ formatRelativeTime(reading.timestamp) }}</div>
                            </div>
                        </div>
                        <ion-button fill="outline" expand="block" @click="openSensorDetails" class="ion-margin-top">
                            View All Sensor Data
                        </ion-button>
                    </ion-card-content>
                </ion-card>

                <!-- Active MQTT Sessions -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="globeOutline"></ion-icon>
                            Active MQTT Sessions
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list v-if="activeUsers.length > 0">
                            <ion-item v-for="user in activeUsers" :key="user.user_id">
                                <ion-avatar slot="start">
                                    <div class="user-avatar">{{ user.user_id.charAt(0).toUpperCase() }}</div>
                                </ion-avatar>
                                <ion-label>
                                    <h3>{{ user.user_id }}</h3>
                                    <p>{{ user.subscribed_topics.length }} subscriptions | QoS {{ user.qos }}</p>
                                    <p class="user-status">
                                        <ion-chip :color="user.is_connected ? 'success' : 'danger'" size="small">
                                            {{ user.is_connected ? 'Connected' : 'Disconnected' }}
                                        </ion-chip>
                                    </p>
                                </ion-label>
                                <ion-button slot="end" fill="clear" @click="viewUserDetails(user)">
                                    <ion-icon :icon="informationCircleOutline"></ion-icon>
                                </ion-button>
                            </ion-item>
                        </ion-list>
                        <div v-else class="empty-state">
                            <ion-icon :icon="cloudOfflineOutline" size="large" color="medium"></ion-icon>
                            <p>No active MQTT sessions</p>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Device Management -->
                <ion-card v-if="devices.length > 0">
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="layersOutline"></ion-icon>
                            Device Overview
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="12" size-md="6" v-for="device in devices.slice(0, 6)" :key="device">
                                    <div class="device-card">
                                        <div class="device-header">
                                            <h4>{{ device }}</h4>
                                            <ion-chip color="primary" size="small">
                                                {{ getDeviceReadingCount(device) }} readings
                                            </ion-chip>
                                        </div>
                                        <div class="device-sensors">
                                            <ion-chip v-for="sensor in getDeviceSensorTypes(device)" :key="sensor"
                                                color="tertiary" size="small">
                                                {{ sensor }}
                                            </ion-chip>
                                        </div>
                                        <ion-button fill="outline" size="small" @click="viewDeviceDetails(device)">
                                            View Details
                                        </ion-button>
                                    </div>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                    </ion-card-content>
                </ion-card>

                <!-- Security & Access Control -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="lockClosedOutline"></ion-icon>
                            Security Status
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="6">
                                    <div class="security-item">
                                        <h4>ACL Status</h4>
                                        <p v-if="aclInfo">
                                            {{ aclInfo.total_users }} users, {{ aclInfo.total_roles }} roles
                                        </p>
                                        <ion-chip :color="aclInfo ? 'success' : 'danger'" size="small">
                                            {{ aclInfo ? 'Active' : 'Inactive' }}
                                        </ion-chip>
                                    </div>
                                </ion-col>
                                <ion-col size="6">
                                    <div class="security-item">
                                        <h4>Sensor Security</h4>
                                        <p v-if="ssInfo">
                                            {{ ssInfo.total_sensors }} active sensors
                                        </p>
                                        <ion-chip :color="ssInfo ? 'success' : 'danger'" size="small">
                                            {{ ssInfo ? 'Active' : 'Inactive' }}
                                        </ion-chip>
                                    </div>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                        <div class="security-actions">
                            <ion-button fill="outline" @click="openACLManagement">
                                <ion-icon :icon="peopleOutline" slot="start"></ion-icon>
                                Manage ACL
                            </ion-button>
                            <ion-button fill="outline" @click="openSSManagement">
                                <ion-icon :icon="shieldCheckmarkOutline" slot="start"></ion-icon>
                                Sensor Security
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Quick Actions -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="flashOutline"></ion-icon>
                            Quick Actions
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="action-grid">
                            <ion-button expand="block" @click="showPublishModal = true">
                                <ion-icon :icon="addCircleOutline" slot="start"></ion-icon>
                                Publish Data
                            </ion-button>
                            <ion-button expand="block" fill="outline" @click="showCommandModal = true">
                                <ion-icon :icon="sendOutline" slot="start"></ion-icon>
                                Send Command
                            </ion-button>
                            <ion-button expand="block" fill="outline" @click="openMQTTTest">
                                <ion-icon :icon="terminalOutline" slot="start"></ion-icon>
                                MQTT Test
                            </ion-button>
                            <ion-button expand="block" fill="outline" @click="reloadConfigurations">
                                <ion-icon :icon="refreshOutline" slot="start"></ion-icon>
                                Reload Config
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Publish Data Modal -->
            <ion-modal :is-open="showPublishModal" @will-dismiss="showPublishModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Publish Sensor Data</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showPublishModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list>
                        <ion-item>
                            <ion-input v-model="publishData.device_id" label="Device ID" placeholder="e.g., sensor_001"
                                label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="publishData.sensor_type" label="Sensor Type"
                                placeholder="e.g., temperature" label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model.number="publishData.value" type="number" label="Value"
                                placeholder="e.g., 23.5" label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="publishData.unit" label="Unit" placeholder="e.g., C"
                                label-placement="stacked"></ion-input>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="publishSensorData" :disabled="!isValidPublishData"
                        class="ion-margin-top">
                        <ion-icon :icon="sendOutline" slot="start"></ion-icon>
                        Publish Data
                    </ion-button>
                </ion-content>
            </ion-modal>

            <!-- Send Command Modal -->
            <ion-modal :is-open="showCommandModal" @will-dismiss="showCommandModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Send Device Command</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showCommandModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list>
                        <ion-item>
                            <ion-select v-model="commandData.device_id" label="Device" placeholder="Select device"
                                label-placement="stacked">
                                <ion-select-option v-for="device in devices" :key="device" :value="device">
                                    {{ device }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="commandData.command" label="Command" placeholder="e.g., get_status"
                                label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-textarea v-model="commandData.parameters" label="Parameters (JSON)"
                                placeholder='{"param1": "value1"}' label-placement="stacked" :rows="3"></ion-textarea>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="sendDeviceCommand" :disabled="!isValidCommandData"
                        class="ion-margin-top">
                        <ion-icon :icon="sendOutline" slot="start"></ion-icon>
                        Send Command
                    </ion-button>
                </ion-content>
            </ion-modal>

            <!-- Settings Modal -->
            <ion-modal :is-open="showSettings" @will-dismiss="showSettings = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Dashboard Settings</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showSettings = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list>
                        <ion-item>
                            <ion-input v-model="settings.userId" label="User ID" placeholder="Enter your user ID"
                                label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="settings.wsUrl" label="WebSocket URL"
                                placeholder="ws://localhost:8000/ws/ws" label-placement="stacked"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-toggle v-model="settings.autoRefresh">Auto Refresh</ion-toggle>
                        </ion-item>
                        <ion-item>
                            <ion-range v-model="settings.refreshInterval" min="5" max="60" step="5" pin="true">
                                <ion-label slot="start">5s</ion-label>
                                <ion-label slot="end">60s</ion-label>
                            </ion-range>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="saveSettings" class="ion-margin-top">
                        <ion-icon :icon="saveOutline" slot="start"></ion-icon>
                        Save Settings
                    </ion-button>
                </ion-content>
            </ion-modal>

            <!-- Floating Action Button -->
            <ion-fab vertical="bottom" horizontal="end" slot="fixed">
                <ion-fab-button color="primary">
                    <ion-icon :icon="addOutline"></ion-icon>
                </ion-fab-button>
                <ion-fab-list side="top">
                    <ion-fab-button @click="showPublishModal = true">
                        <ion-icon :icon="addCircleOutline"></ion-icon>
                    </ion-fab-button>
                    <ion-fab-button @click="showCommandModal = true">
                        <ion-icon :icon="sendOutline"></ion-icon>
                    </ion-fab-button>
                    <ion-fab-button @click="refreshData">
                        <ion-icon :icon="refreshOutline"></ion-icon>
                    </ion-fab-button>
                </ion-fab-list>
            </ion-fab>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons, IonButton,
    IonIcon, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonList,
    IonItem, IonLabel, IonChip, IonSpinner, IonAvatar, IonModal, IonGrid, IonRow, IonCol,
    IonInput, IonTextarea, IonSelect, IonSelectOption, IonToggle, IonRange,
    IonFab, IonFabButton, IonFabList, alertController, toastController
} from '@ionic/vue';
import {
    refreshOutline, settingsOutline, checkmarkCircleOutline, closeCircleOutline,
    hardwareChipOutline, peopleOutline, barChartOutline, shieldCheckmarkOutline,
    thermometerOutline, wifiOutline, informationCircleOutline, cloudOfflineOutline,
    layersOutline, lockClosedOutline, flashOutline, addCircleOutline, sendOutline,
    terminalOutline, closeOutline, saveOutline, addOutline, warningOutline,
    alertCircleOutline, checkmarkCircle, closeCircle, wifi,
    globeOutline
} from 'ionicons/icons';

import webSocketService from '@/services/websocket';
import { useIotStore } from '@/stores/iot';

// Store and router
const iotStore = useIotStore();
const router = useRouter();

// Reactive State
const isLoading = ref(false);
const hasData = ref(false);
const error = ref(null);

// WebSocket connection status
const isConnected = ref(false);
const connectionStatus = ref('Disconnected');

// Modals
const showPublishModal = ref(false);
const showCommandModal = ref(false);
const showSettings = ref(false);

// Data stores
const devices = ref([]);
const latestSensorData = ref([]);
const activeUsers = ref([]);
const systemAlerts = ref([]);
const aclInfo = ref(null);
const ssInfo = ref(null);

// Forms data
const publishData = ref({
    device_id: '',
    sensor_type: '',
    value: 0,
    unit: ''
});

const commandData = ref({
    device_id: '',
    command: '',
    parameters: ''
});

const settings = ref({
    userId: 'erkam',
    wsUrl: 'ws://localhost:8000/ws/ws',
    autoRefresh: true,
    refreshInterval: 15
});

// Computed properties
const connectionStatusColor = computed(() => {
    switch (connectionStatus.value) {
        case 'Connected': return 'success';
        case 'Connecting': return 'warning';
        case 'Disconnected': return 'danger';
        default: return 'medium';
    }
});

const connectionStatusIcon = computed(() => {
    switch (connectionStatus.value) {
        case 'Connected': return globeOutline;
        case 'Connecting': return globeOutline;
        case 'Disconnected': return warningOutline;
        default: return closeCircle;
    }
});

const deviceCount = computed(() => devices.value.length);
const totalSensorReadings = computed(() => latestSensorData.value.length);
const recentAlerts = computed(() => systemAlerts.value.slice(0, 3));

const isValidPublishData = computed(() => {
    return publishData.value.device_id &&
        publishData.value.sensor_type &&
        publishData.value.unit &&
        publishData.value.value !== null;
});

const isValidCommandData = computed(() => {
    return commandData.value.device_id && commandData.value.command;
});

// Auto-refresh watcher
let refreshInterval = null;
watch(() => settings.value.autoRefresh, (enabled) => {
    if (enabled) {
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
});

// Methods
const showToast = async (message, color = 'primary') => {
    const toast = await toastController.create({
        message,
        duration: 3000,
        color,
        position: 'bottom'
    });
    await toast.present();
};

const showAlert = async (header, message) => {
    const alert = await alertController.create({
        header,
        message,
        buttons: ['OK']
    });
    await alert.present();
};

// WebSocket Event Handlers
const handleConnectionStatus = (data) => {
    if (data.status === 'connected') {
        isConnected.value = true;
        connectionStatus.value = 'Connected';
        showToast('Connected to system', 'success');
    } else if (data.status === 'disconnected') {
        isConnected.value = false;
        connectionStatus.value = 'Disconnected';
        showToast('Disconnected from system', 'warning');
    } else if (data.status === 'error') {
        isConnected.value = false;
        connectionStatus.value = 'Error';
        showToast('Connection error', 'danger');
    }
};

const handleSystemAlert = (data) => {
    const alert = {
        id: Date.now() + Math.random(),
        level: data.level,
        message: data.message,
        details: data.details,
        timestamp: new Date().toISOString()
    };

    systemAlerts.value.unshift(alert);

    // Keep only last 20 alerts
    if (systemAlerts.value.length > 20) {
        systemAlerts.value = systemAlerts.value.slice(0, 20);
    }

    // Show toast for critical alerts
    if (data.level === 'error' || data.level === 'critical') {
        showToast(`${data.level.toUpperCase()}: ${data.message}`, 'danger');
    }
};

const handleSensorData = (data) => {
    const sensorReading = {
        id: Date.now() + Math.random(),
        device_id: data.data.device_id || 'unknown',
        sensor_type: data.data.sensor_type || 'unknown',
        value: data.data.value,
        unit: data.data.unit || '',
        timestamp: data.data.timestamp || new Date().toISOString(),
        topic: data.topic,
        qos: data.qos,
        retain: data.retain
    };

    // Add to sensor readings
    latestSensorData.value.unshift(sensorReading);

    // Keep only last 50 readings
    if (latestSensorData.value.length > 50) {
        latestSensorData.value = latestSensorData.value.slice(0, 50);
    }

    // Auto-discover devices from sensor data
    const deviceId = sensorReading.device_id;
    if (deviceId !== 'unknown' && !devices.value.includes(deviceId)) {
        devices.value.push(deviceId);
        console.log(`Auto-discovered new device: ${deviceId}`);
    }
};

const handlePublishAck = (data) => {
    if (data.status === 'success') {
        console.log('Publish successful:', data.topic);
    } else {
        showToast(`Publish failed: ${data.topic}`, 'danger');
        console.error('Publish failed:', data);
    }
};

// New WebSocket Event Handlers for system data
const handleUsersList = (data) => {
    console.log('Received users list:', data);
    if (data.users) {
        activeUsers.value = data.users;
    }
};

const handleSystemStatus = (data) => {
    console.log('Received system status:', data);

    // Extract device information from user status
    if (data.user_id && data.subscribed_topics) {
        // Update devices list based on active subscriptions
        const deviceTopics = data.subscribed_topics.filter(topic =>
            topic.startsWith('sf/sensors/') && topic !== 'sf/sensors/#'
        );

        const newDevices = deviceTopics.map(topic => {
            const parts = topic.split('/');
            return parts[2]; // Extract device ID from sf/sensors/DEVICE_ID/...
        }).filter(device => device && !devices.value.includes(device));

        devices.value = [...new Set([...devices.value, ...newDevices])];
    }
};

const handleSystemInfo = (data) => {
    console.log('Received system info:', data);
    // This would need to be implemented on the backend
    // For now, we'll handle ACL and SS info when available
    if (data.acl_info) {
        aclInfo.value = data.acl_info;
    }
    if (data.ss_info) {
        ssInfo.value = data.ss_info;
    }
};

const handleDeviceStatus = (data) => {
    console.log('Received device status:', data);
    // Handle device status updates
    if (data.device_id && !devices.value.includes(data.device_id)) {
        devices.value.push(data.device_id);
    }
};

const handleMqttStatus = (data) => {
    console.log('Received MQTT status:', data);
    // Handle MQTT connection status updates
};

// WebSocket-based Data Loading (replacing API methods)
const requestSystemStatus = () => {
    if (!isConnected.value) return;

    // Request status information via WebSocket
    webSocketService.send({
        type: 'get_status'
    });
};

const requestUsersList = () => {
    if (!isConnected.value) return;

    // Request list of all connected users
    webSocketService.send({
        type: 'get_all_users'
    });
};

const requestSystemInfo = () => {
    if (!isConnected.value) return;

    // Request system information (ACL, SS, backend status)
    webSocketService.send({
        type: 'get_system_info'
    });
};

// WebSocket-based refresh that requests all current data
const refreshData = () => {
    if (!isConnected.value) {
        showToast('Connect to WebSocket first', 'warning');
        return;
    }

    isLoading.value = true;

    // Request all data via WebSocket
    requestSystemStatus();
    requestUsersList();
    requestSystemInfo();

    // Set hasData to true since we're now connected
    hasData.value = true;
    isLoading.value = false;
};

// Connection Management
const connectWebSocket = async () => {
    if (!settings.value.userId.trim()) {
        showAlert('Error', 'Please set a User ID in settings');
        return;
    }

    connectionStatus.value = 'Connecting';
    isLoading.value = true;

    try {
        await webSocketService.connect(settings.value.wsUrl, settings.value.userId, authStore.token);

        // Subscribe to all necessary topics for real-time updates
        webSocketService.subscribeMQTT([
            'sf/+/+/status',        // User and backend status
            'sf/sensors/#',         // All sensor data
            'sf/commands/#',        // All commands
            'sf/backend/status'     // Backend status
        ], 1);

        showToast('Connected to Smart Factory system', 'success');

        // Request initial data after connection is established
        setTimeout(() => {
            requestSystemStatus();
            requestUsersList();
            requestSystemInfo();
        }, 1000); // Give time for subscriptions to be established

    } catch (error) {
        connectionStatus.value = 'Error';
        showToast('Failed to connect', 'danger');
    } finally {
        isLoading.value = false;
    }
};

const disconnectWebSocket = () => {
    webSocketService.disconnect();
    connectionStatus.value = 'Disconnected';
};

const toggleConnection = () => {
    if (isConnected.value) {
        disconnectWebSocket();
    } else {
        connectWebSocket();
    }
};

// Action Methods
const publishSensorData = async () => {
    try {
        // Create the sensor data payload
        const sensorData = {
            device_id: publishData.value.device_id,
            sensor_type: publishData.value.sensor_type,
            value: publishData.value.value,
            unit: publishData.value.unit,
            timestamp: new Date().toISOString()
        };

        // Publish through WebSocket (user's MQTT client) instead of REST API
        const topic = `sf/sensors/${publishData.value.device_id}/${publishData.value.sensor_type}`;
        webSocketService.publishMQTT(topic, sensorData, 1, false);

        showPublishModal.value = false;
        publishData.value = { device_id: '', sensor_type: '', value: 0, unit: '' };
        showToast('Data published successfully', 'success');

        // Don't call refreshData() immediately as we'll receive the data via WebSocket
    } catch (err) {
        showToast('Failed to publish data', 'danger');
    }
};

const sendDeviceCommand = async () => {
    try {
        let parameters = {};
        if (commandData.value.parameters.trim()) {
            parameters = JSON.parse(commandData.value.parameters);
        }

        // Create the command payload
        const commandPayload = {
            command: commandData.value.command,
            parameters: parameters,
            timestamp: new Date().toISOString()
        };

        // Send command through WebSocket (user's MQTT client) instead of REST API
        const topic = `sf/commands/${commandData.value.device_id}`;
        webSocketService.publishMQTT(topic, commandPayload, 1, false);

        showCommandModal.value = false;
        commandData.value = { device_id: '', command: '', parameters: '' };
        showToast('Command sent successfully', 'success');
    } catch (err) {
        showToast('Failed to send command', 'danger');
    }
};

const reloadConfigurations = () => {
    if (!isConnected.value) {
        showToast('Connect to WebSocket first', 'warning');
        return;
    }

    // Send reload requests via WebSocket
    webSocketService.send({
        type: 'reload_acl'
    });

    webSocketService.send({
        type: 'reload_ss'
    });

    showToast('Configuration reload requested', 'success');

    // Request fresh system info after reload
    setTimeout(() => {
        requestSystemInfo();
    }, 2000);
};

// Navigation Methods
const openMQTTTest = () => {
    router.push('/mqtt-test');
};

const openACLManagement = () => {
    router.push('/acl-management');
};

const openSSManagement = () => {
    router.push('/ss-management');
};

const openSensorDetails = () => {
    router.push('/sensor-details');
};

const viewDeviceDetails = (deviceId) => {
    router.push(`/device/${deviceId}`);
};

const viewUserDetails = async (user) => {
    const topics = user.subscribed_topics.join(', ') || 'None';
    const alert = await alertController.create({
        header: `User: ${user.user_id}`,
        message: `
      <strong>Status:</strong> ${user.is_connected ? 'Connected' : 'Disconnected'}<br>
      <strong>QoS:</strong> ${user.qos}<br>
      <strong>Subscribed Topics:</strong> ${topics}<br>
      <strong>Broker:</strong> ${user.broker}
    `,
        buttons: ['OK']
    });
    await alert.present();
};

// Utility Methods
const dismissAlert = (alertId) => {
    systemAlerts.value = systemAlerts.value.filter(alert => alert.id !== alertId);
};

const getAlertColor = (level) => {
    switch (level) {
        case 'error':
        case 'critical': return 'danger';
        case 'warning': return 'warning';
        case 'info': return 'primary';
        default: return 'medium';
    }
};

const getAlertIcon = (level) => {
    switch (level) {
        case 'error':
        case 'critical': return alertCircleOutline;
        case 'warning': return warningOutline;
        case 'info': return informationCircleOutline;
        default: return informationCircleOutline;
    }
};

const getSensorStatusColor = (reading) => {
    // You can implement logic based on sensor limits here
    return 'primary';
};

const getDeviceReadingCount = (deviceId) => {
    return latestSensorData.value.filter(r => r.device_id === deviceId).length;
};

const getDeviceSensorTypes = (deviceId) => {
    const types = new Set();
    latestSensorData.value
        .filter(r => r.device_id === deviceId)
        .forEach(r => types.add(r.sensor_type));
    return Array.from(types);
};

const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
};

const formatRelativeTime = (timestamp) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diff = now - time;
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return 'Just now';
    if (minutes === 1) return '1 min ago';
    if (minutes < 60) return `${minutes} mins ago`;

    const hours = Math.floor(minutes / 60);
    if (hours === 1) return '1 hour ago';
    return `${hours} hours ago`;
};

const saveSettings = () => {
    localStorage.setItem('dashboardSettings', JSON.stringify(settings.value));
    showSettings.value = false;
    showToast('Settings saved', 'success');

    // Reconnect with new settings
    webSocketService.disconnect();
    setTimeout(connectWebSocket, 1000);
};

const loadSettings = () => {
    const saved = localStorage.getItem('dashboardSettings');
    if (saved) {
        try {
            settings.value = { ...settings.value, ...JSON.parse(saved) };
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
    }
};

const startAutoRefresh = () => {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(refreshData, settings.value.refreshInterval * 1000);
};

const stopAutoRefresh = () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
};

// Lifecycle
onMounted(() => {
    loadSettings();

    // Register all WebSocket event handlers
    webSocketService.on('connection_status', handleConnectionStatus);
    webSocketService.on('sensor_data', handleSensorData);
    webSocketService.on('system_alert', handleSystemAlert);
    webSocketService.on('publish_ack', handlePublishAck);
    webSocketService.on('users_list', handleUsersList);
    webSocketService.on('status', handleSystemStatus);
    webSocketService.on('system_info', handleSystemInfo);
    webSocketService.on('device_status', handleDeviceStatus);
    webSocketService.on('mqtt_status', handleMqttStatus);

    // Connect first, then data will come via WebSocket
    connectWebSocket();

    // Start auto-refresh if enabled (now just refreshes via WebSocket)
    if (settings.value.autoRefresh) {
        startAutoRefresh();
    }
});

onUnmounted(() => {
    // Cleanup all event handlers
    webSocketService.off('connection_status', handleConnectionStatus);
    webSocketService.off('sensor_data', handleSensorData);
    webSocketService.off('system_alert', handleSystemAlert);
    webSocketService.off('publish_ack', handlePublishAck);
    webSocketService.off('users_list', handleUsersList);
    webSocketService.off('status', handleSystemStatus);
    webSocketService.off('system_info', handleSystemInfo);
    webSocketService.off('device_status', handleDeviceStatus);
    webSocketService.off('mqtt_status', handleMqttStatus);
    webSocketService.disconnect();
    stopAutoRefresh();
});
</script>

<style scoped>
.connection-status {
    margin-right: 8px;
    cursor: pointer;
    transition: opacity 0.2s;
}

.connection-status:hover {
    opacity: 0.8;
}

.alerts-banner {
    padding: 8px 16px;
    background: var(--ion-color-light);
}

.alert-card {
    margin-bottom: 8px;
}

.alert-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.alert-level {
    font-weight: bold;
    font-size: 0.8em;
}

.alert-time {
    font-size: 0.7em;
    color: var(--ion-color-medium);
    margin-left: auto;
}

.alert-message {
    margin: 8px 0;
    font-weight: 500;
}

.alert-details {
    background: rgba(255, 255, 255, 0.3);
    padding: 8px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.7em;
    max-height: 100px;
    overflow-y: auto;
}

.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    gap: 16px;
}

.stats-section {
    padding: 16px;
}

.stat-card {
    height: 100px;
    margin: 0;
}

.stat-content {
    display: flex;
    align-items: center;
    height: 100%;
    gap: 12px;
}

.stat-icon {
    font-size: 2rem;
    flex-shrink: 0;
}

.stat-info h2 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: bold;
}

.stat-info p {
    margin: 4px 0 0 0;
    font-size: 0.8rem;
    color: var(--ion-color-medium);
}

.sensor-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
}

.sensor-item {
    background: var(--ion-color-light);
    padding: 12px;
    border-radius: 8px;
    border-left: 4px solid var(--ion-color-primary);
}

.sensor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.device-id {
    font-weight: bold;
    font-size: 0.9em;
}

.sensor-value {
    font-size: 1.4em;
    font-weight: bold;
    margin-bottom: 4px;
}

.sensor-time {
    font-size: 0.7em;
    color: var(--ion-color-medium);
}

.user-avatar {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--ion-color-primary);
    color: white;
    font-weight: bold;
    border-radius: 50%;
}

.user-status {
    margin-top: 4px;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--ion-color-medium);
}

.device-card {
    background: var(--ion-color-light);
    padding: 16px;
    border-radius: 8px;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.device-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.device-header h4 {
    margin: 0;
    font-size: 1rem;
}

.device-sensors {
    margin-bottom: 12px;
    flex: 1;
}

.security-item {
    text-align: center;
    padding: 16px;
}

.security-item h4 {
    margin: 0 0 8px 0;
    font-size: 1rem;
}

.security-item p {
    margin: 8px 0;
    font-size: 0.8rem;
    color: var(--ion-color-medium);
}

.security-actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
}

.action-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 8px;
}

@media (max-width: 768px) {
    .stats-section {
        padding: 8px;
    }

    .stat-content {
        flex-direction: column;
        text-align: center;
    }

    .sensor-grid {
        grid-template-columns: 1fr;
    }

    .security-actions {
        flex-direction: column;
    }

    .action-grid {
        grid-template-columns: 1fr;
    }
}
</style>