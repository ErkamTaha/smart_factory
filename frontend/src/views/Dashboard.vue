<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-icon :icon="businessOutline" class="toolbar-logo"></ion-icon>
                </ion-buttons>
                <ion-title>Smart Factory</ion-title>
                <!-- Toolbar inline stats -->
                <div class="toolbar-stats" slot="end">
                    <span class="toolbar-stat" title="Connected Users">
                        <ion-icon :icon="peopleOutline"></ion-icon>{{ activeUsers.length }}
                    </span>
                    <span class="toolbar-stat" :class="{ 'toolbar-stat-alert': systemAlerts.length > 0 }" title="Alerts">
                        <ion-icon :icon="alertCircleOutline"></ion-icon>{{ systemAlerts.length }}
                    </span>
                </div>
                <ion-buttons slot="end">
                    <ion-button color="light" title="Refresh data" @click="refreshData" :disabled="isRefreshing || !isConnected">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                    <ion-button color="light" title="Settings" @click="showSettings = true">
                        <ion-icon :icon="settingsOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                    <ion-button color="light" title="Logout" @click="handleLogout">
                        <ion-icon :icon="logOutOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                    <!-- Connection Status -->
                    <span class="connection-chip" :class="`connection-chip-${connectionStatus.toLowerCase()}`" @click="toggleConnection">
                        <ion-icon :icon="connectionStatusIcon"></ion-icon>
                        {{ connectionStatus }}
                    </span>
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
            <div v-if="isLoading && !hasData" class="page-loading">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading dashboard data...</p>
            </div>

            <!-- Main Dashboard Content -->
            <div v-else class="dashboard-content">
                <!-- Device Strip (horizontal scroll) -->
                <ion-card v-if="deviceSummaries.length > 0" class="device-strip-card">
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="hardwareChipOutline"></ion-icon>
                            Devices
                            <ion-chip color="primary" size="small" class="reading-count-badge">
                                {{ deviceSummaries.length }}
                            </ion-chip>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="device-scroll">
                            <div v-for="dev in deviceSummaries" :key="dev.id"
                                class="device-card" @click="viewDeviceDetails(dev.id)">
                                <div class="device-avatar" :style="getDeviceAvatarStyle(dev.types)">
                                    <ion-icon :icon="getDeviceIcon(dev.types)"></ion-icon>
                                </div>
                                <div class="device-info">
                                    <div class="device-name">{{ dev.id }}</div>
                                    <div class="device-types">
                                        <span v-for="t in dev.types" :key="t" class="device-type-badge" :style="getSensorPillStyle(t)">{{ t }}</span>
                                    </div>
                                </div>
                                <div class="device-age">{{ formatRelativeTime(dev.lastTs) }}</div>
                            </div>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Latest Sensor Readings (horizontal scroll) -->
                <ion-card v-if="latestSensorData.length > 0" class="sensor-scroll-card">
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="thermometerOutline"></ion-icon>
                            Latest Readings
                            <ion-chip color="primary" size="small" class="reading-count-badge">
                                {{ latestSensorData.length }}
                            </ion-chip>
                            <ion-button fill="clear" size="small" class="view-all-btn" @click="router.push('/readings')">
                                View All
                                <ion-icon :icon="chevronForwardOutline" slot="end"></ion-icon>
                            </ion-button>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="sensor-scroll">
                            <div v-for="reading in latestSensorData.slice(0, 8)" :key="reading.id"
                                class="sensor-card">
                                <div class="sensor-card-top">
                                    <div class="sensor-type-pill" :style="getSensorPillStyle(reading.sensor_type)">
                                        <ion-icon :icon="getSensorIcon(reading.sensor_type)"></ion-icon>
                                        <span>{{ reading.sensor_type }}</span>
                                    </div>
                                    <span class="sensor-age">{{ formatRelativeTime(reading.timestamp) }}</span>
                                </div>
                                <div class="sensor-card-value">
                                    {{ reading.value !== undefined && reading.value !== null ? reading.value : '—' }}
                                    <span class="sensor-unit">{{ reading.unit }}</span>
                                </div>
                                <div class="sensor-card-bottom">
                                    <ion-icon :icon="hardwareChipOutline" class="device-icon"></ion-icon>
                                    <span class="sensor-device">{{ reading.device_id }}</span>
                                </div>
                            </div>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Security & Sessions side by side -->
                <div class="cards-row">
                    <!-- Security & Access Control -->
                    <ion-card class="half-card">
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="lockClosedOutline"></ion-icon>
                                Security
                            </ion-card-title>
                        </ion-card-header>
                        <ion-card-content>
                            <div class="security-item">
                                <h4>
                                    <ion-icon :icon="peopleOutline"></ion-icon>
                                    ACL
                                </h4>
                                <p v-if="aclInfo">{{ aclInfo.total_users }} users / {{ aclInfo.total_roles }} roles</p>
                                <ion-chip :color="aclInfo ? 'success' : 'danger'" size="small">
                                    {{ aclInfo ? 'Active' : 'Inactive' }}
                                </ion-chip>
                                <ion-button fill="outline" size="small" @click="openACLManagement" class="security-btn">
                                    Manage
                                </ion-button>
                            </div>
                            <div class="card-divider"></div>
                            <div class="security-item">
                                <h4>
                                    <ion-icon :icon="shieldCheckmarkOutline"></ion-icon>
                                    Sensor SS
                                </h4>
                                <p v-if="ssInfo">{{ ssInfo.total_sensors }} sensors</p>
                                <ion-chip :color="ssInfo ? 'success' : 'danger'" size="small">
                                    {{ ssInfo ? 'Active' : 'Inactive' }}
                                </ion-chip>
                                <ion-button fill="outline" size="small" @click="openSSManagement" class="security-btn">
                                    Manage
                                </ion-button>
                            </div>
                        </ion-card-content>
                    </ion-card>

                    <!-- Active MQTT Sessions -->
                    <ion-card class="half-card">
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="globeOutline"></ion-icon>
                                Sessions
                            </ion-card-title>
                        </ion-card-header>
                        <ion-card-content class="sessions-content">
                            <ion-list v-if="activeUsers.length > 0" lines="none">
                                <ion-item v-for="user in activeUsers.slice(0, 2)" :key="user.user_id" class="session-item">
                                    <div slot="start" class="item-avatar item-avatar-sm">{{ user.user_id.charAt(0).toUpperCase() }}</div>
                                    <ion-label>
                                        <h3>{{ user.user_id }}</h3>
                                        <p>{{ user.subscribed_topics.length }} topics</p>
                                    </ion-label>
                                    <ion-chip slot="end" :color="user.is_connected ? 'success' : 'danger'" size="small">
                                        {{ user.is_connected ? 'On' : 'Off' }}
                                    </ion-chip>
                                </ion-item>
                            </ion-list>
                            <div v-else class="empty-state-sm">
                                <ion-icon :icon="cloudOfflineOutline" color="medium"></ion-icon>
                                <p>No active sessions</p>
                            </div>
                        </ion-card-content>
                    </ion-card>
                </div>
            </div>

            <!-- Quick Actions FAB -->
            <ion-fab slot="fixed" vertical="bottom" horizontal="end">
                <ion-fab-button color="primary">
                    <ion-icon :icon="flashOutline"></ion-icon>
                </ion-fab-button>
                <ion-fab-list side="top">
                    <ion-fab-button @click="reloadConfigurations" color="medium" title="Reload Config">
                        <ion-icon :icon="refreshOutline"></ion-icon>
                    </ion-fab-button>
                    <ion-fab-button @click="openMQTTTest" color="tertiary" title="MQTT Test">
                        <ion-icon :icon="terminalOutline"></ion-icon>
                    </ion-fab-button>
                    <ion-fab-button @click="showCommandModal = true" color="secondary" title="Send Command">
                        <ion-icon :icon="sendOutline"></ion-icon>
                    </ion-fab-button>
                    <ion-fab-button @click="showPublishModal = true" color="primary" title="Publish Data">
                        <ion-icon :icon="addCircleOutline"></ion-icon>
                    </ion-fab-button>
                </ion-fab-list>
            </ion-fab>

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
                    <ion-button @click="publishSensorData" :disabled="!isValidPublishData"
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
                    <ion-button @click="sendDeviceCommand" :disabled="!isValidCommandData"
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
                    <ion-button @click="saveSettings" class="ion-margin-top">
                        <ion-icon :icon="saveOutline" slot="start"></ion-icon>
                        Save Settings
                    </ion-button>
                </ion-content>
            </ion-modal>

        </ion-content>

        <!-- Custom Toast Notifications -->
        <div class="toast-container">
            <transition-group name="toast" tag="div" class="toast-stack">
                <div v-for="toast in toasts" :key="toast.id"
                    class="custom-toast" :class="`toast-${toast.color}`">
                    <div class="toast-icon-wrap">
                        <ion-icon :icon="toast.icon" class="toast-icon"></ion-icon>
                    </div>
                    <span class="toast-message">{{ toast.message }}</span>
                    <button class="toast-close" @click="removeToast(toast.id)" aria-label="Dismiss">
                        <ion-icon :icon="closeOutline"></ion-icon>
                    </button>
                </div>
            </transition-group>
        </div>
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
    IonFab, IonFabButton, IonFabList,
    alertController
} from '@ionic/vue';
import {
    refreshOutline, settingsOutline, checkmarkCircleOutline, closeCircleOutline,
    hardwareChipOutline, peopleOutline, barChartOutline, shieldCheckmarkOutline,
    thermometerOutline, wifiOutline, informationCircleOutline, cloudOfflineOutline,
    layersOutline, lockClosedOutline, flashOutline, addCircleOutline, sendOutline,
    terminalOutline, closeOutline, saveOutline, warningOutline,
    alertCircleOutline, checkmarkCircle, closeCircle, wifi,
    globeOutline, logOutOutline, chevronForwardOutline,
    waterOutline, speedometerOutline, moveOutline, businessOutline
} from 'ionicons/icons';

import webSocketService from '@/services/websocket';
import apiService from '@/services/api';
import { useFactoryStore } from '@/stores/factory';
import { useAuthStore } from '@/stores/auth';

// Store and router
const factoryStore = useFactoryStore();
const authStore = useAuthStore();
const router = useRouter();

// Logout
const handleLogout = () => {
    webSocketService.disconnect();
    authStore.logout();
    router.replace('/login');
};

// Reactive State
const isLoading = ref(false);
const isRefreshing = ref(false);
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
    userId: authStore.username || authStore.user?.username || '',
    wsUrl: `ws://${window.location.host}/ws/ws`,
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

// Per-device summary derived from latestSensorData
const deviceSummaries = computed(() => {
    const map = new Map();
    latestSensorData.value.forEach(r => {
        if (!r.device_id || r.device_id === 'unknown') return;
        if (!map.has(r.device_id)) {
            map.set(r.device_id, { id: r.device_id, count: 0, types: new Set(), lastTs: null });
        }
        const d = map.get(r.device_id);
        d.count++;
        if (r.sensor_type && r.sensor_type !== 'unknown') d.types.add(r.sensor_type);
        if (!d.lastTs || r.timestamp > d.lastTs) d.lastTs = r.timestamp;
    });
    return Array.from(map.values()).map(d => ({ ...d, types: Array.from(d.types) }));
});

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

// Custom toast system
const toasts = ref([]);

const removeToast = (id) => {
    toasts.value = toasts.value.filter(t => t.id !== id);
};

const showToast = (message, color = 'primary') => {
    const iconMap = {
        success: checkmarkCircleOutline,
        danger: alertCircleOutline,
        warning: warningOutline,
        primary: informationCircleOutline,
    };
    const id = Date.now() + Math.random();
    toasts.value.push({ id, message, color, icon: iconMap[color] || informationCircleOutline });
    setTimeout(() => removeToast(id), 3500);
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
        // Request initial data now that we know the backend is ready
        requestSystemStatus();
        requestUsersList();
        requestSystemInfo();
        // Fetch historical sensor readings from DB
        fetchInitialSensorData();
        hasData.value = true;
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
    // Extract device_id (string) and sensor_type from topic: sf/sensors/DEVICE_ID/SENSOR_TYPE
    let topicDeviceId = null;
    let topicSensorType = null;
    if (data.topic) {
        const parts = data.topic.split('/');
        if (parts.length >= 3 && parts[0] === 'sf' && parts[1] === 'sensors') {
            topicDeviceId = parts[2] || null;       // string device identifier
            topicSensorType = parts[3] || null;     // e.g. 'temperature'
        }
    }

    const payload = data.data || {};
    // Prefer string topic device_id over payload.device_id (which may be an integer FK)
    const deviceId = topicDeviceId || (payload.device_id ? String(payload.device_id) : null) || 'unknown';
    const sensorType = payload.sensor_type || topicSensorType || 'unknown';

    // Drop the reading entirely if we have no useful identifiers
    if (deviceId === 'unknown' || sensorType === 'unknown') return;

    const sensorReading = {
        id: Date.now() + Math.random(),
        device_id: deviceId,
        sensor_type: sensorType,
        value: payload.value,
        unit: payload.unit || '',
        timestamp: payload.timestamp || new Date().toISOString(),
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

    // Auto-discover devices from sensor data (deviceId is always a valid string here)
    if (!devices.value.includes(sensorReading.device_id)) {
        devices.value.push(sensorReading.device_id);
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

// Fetch historical sensor readings from REST API
const fetchInitialSensorData = async () => {
    try {
        const response = await apiService.getLatestReadings(20);
        const readings = response.data.readings || [];
        // Drop any stale WebSocket-sourced entries that have unknown fields
        latestSensorData.value = latestSensorData.value.filter(
            s => s.sensor_type !== 'unknown' && s.device_id !== 'unknown'
        );
        // Map REST API field names to the shape handleSensorData uses
        readings.forEach(r => {
            const reading = {
                id: r.id,
                device_id: r.device_identifier || String(r.device_id),
                sensor_type: r.sensor_type_name || String(r.sensor_type_id),
                value: r.value,
                unit: r.unit,
                timestamp: r.timestamp,
                topic: r.mqtt_topic,
                qos: r.qos,
                retain: r.retain
            };
            // Only add if not already present (avoid duplicates with real-time data)
            if (!latestSensorData.value.some(s => s.id === reading.id)) {
                latestSensorData.value.push(reading);
            }
            // Auto-discover devices
            if (reading.device_id && !devices.value.includes(reading.device_id)) {
                devices.value.push(reading.device_id);
            }
        });
        // Sort newest-first
        latestSensorData.value.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        // Keep only last 50
        if (latestSensorData.value.length > 50) {
            latestSensorData.value = latestSensorData.value.slice(0, 50);
        }
        if (readings.length > 0) hasData.value = true;
    } catch (err) {
        console.error('Failed to fetch initial sensor data:', err);
    }
};

// WebSocket-based refresh that requests all current data
const refreshData = () => {
    if (!isConnected.value) {
        showToast('Connect to WebSocket first', 'warning');
        return;
    }

    isRefreshing.value = true;

    // Request all data via WebSocket
    requestSystemStatus();
    requestUsersList();
    requestSystemInfo();

    // Also refresh historical sensor readings from DB
    fetchInitialSensorData();

    hasData.value = true;

    // Brief visual feedback — data arrives async via WebSocket
    setTimeout(() => { isRefreshing.value = false; }, 800);
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
        const token = authStore.token || localStorage.getItem('access_token');
        const userId = authStore.username || authStore.user?.username || settings.value.userId;
        await webSocketService.connect(settings.value.wsUrl, userId, token);

        // Subscribe to all necessary topics for real-time updates
        webSocketService.subscribeMQTT([
            'sf/+/+/status',        // User and backend status
            'sf/sensors/#',         // All sensor data
            'sf/commands/#',        // All commands
            'sf/backend/status'     // Backend status
        ], 1);

        showToast('Connected to Smart Factory system', 'success');

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

const SENSOR_META = {
    temperature: { icon: thermometerOutline, bg: 'rgba(194, 68, 80, 0.12)',  fg: '#b84050' },
    humidity:    { icon: waterOutline,        bg: 'rgba(56, 120, 220, 0.12)', fg: '#3472c0' },
    pressure:    { icon: speedometerOutline,  bg: 'rgba(180, 140, 10, 0.13)', fg: '#9a7800' },
    motion:      { icon: moveOutline,         bg: 'rgba(38, 180, 100, 0.12)', fg: '#28a060' },
};
const SENSOR_META_DEFAULT = { icon: hardwareChipOutline, bg: 'rgba(130, 130, 140, 0.12)', fg: '#7a7a8a' };

const getSensorMeta = (type) => SENSOR_META[type] || SENSOR_META_DEFAULT;

// Device strip helpers
const getDeviceIcon = (types) => getSensorMeta(types[0]).icon;
const getDeviceAvatarStyle = (types) => {
    const m = getSensorMeta(types[0]);
    return { background: m.bg, color: m.fg };
};

// Readings strip helpers
const getSensorIcon = (type) => getSensorMeta(type).icon;
const getSensorPillStyle = (type) => {
    const m = getSensorMeta(type);
    return { background: m.bg, color: m.fg };
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
    // Always use authenticated user's identity, not saved settings
    settings.value.userId = authStore.username || authStore.user?.username || settings.value.userId;
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
/* ── Toolbar logo ────────────────────────────────────────── */
.toolbar-logo {
  font-size: 22px;
  color: rgba(255, 255, 255, 0.9);
  margin-left: 4px;
}

/* ── Toolbar connection chip ─────────────────────────────── */
.connection-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  border-radius: 20px;
  padding: 3px 9px 3px 7px;
  margin-right: 6px;
  cursor: pointer;
  white-space: nowrap;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
}
.connection-chip ion-icon { font-size: 13px; }
.connection-chip-connected    { background: rgba(45, 211, 111, 0.30); }
.connection-chip-connecting   { background: rgba(255, 196, 9, 0.30); }
.connection-chip-disconnected { background: rgba(235, 68, 90, 0.60); }

/* ── Alerts banner ───────────────────────────────────────── */
.alerts-banner {
  padding: 4px 0;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.alert-level {
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.alert-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  margin-left: auto;
}

.alert-message {
  margin: 0 0 6px;
  font-weight: 500;
  font-size: 14px;
}

.alert-details {
  background: rgba(255, 255, 255, 0.15);
  padding: 8px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 11px;
  max-height: 80px;
  overflow-y: auto;
}

/* ── Dashboard content: collapse Ionic card margins ─────── */
.dashboard-content {
  display: flex;
  flex-direction: column;
}
.dashboard-content > ion-card {
  margin: 6px 12px;
}
.dashboard-content > .cards-row {
  margin: 4px 0 6px;
}
.dashboard-content > .cards-row .half-card {
  margin: 0 8px;
}
.dashboard-content > .cards-row .half-card:first-child {
  margin-right: 4px;
}
.dashboard-content > .cards-row .half-card:last-child {
  margin-left: 4px;
}

/* ── Toolbar inline stats ────────────────────────────────── */
.toolbar-stats {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 4px;
}

.toolbar-stat {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 3px 8px;
  white-space: nowrap;
}

.toolbar-stat ion-icon {
  font-size: 14px;
}

.toolbar-stat-alert {
  background: rgba(235, 68, 90, 0.85);
  color: #fff;
}

/* ── Cards row (side by side) ────────────────────────────── */
.cards-row {
  display: flex;
  gap: 0;
  align-items: stretch;
}

.half-card {
  flex: 1;
  min-width: 0;
}

.half-card ion-card-header {
  padding: 8px 12px 4px;
}

.half-card ion-card-title {
  font-size: 14px;
}

.half-card ion-card-content {
  padding: 4px 10px 8px;
}

/* ── Sessions list ───────────────────────────────────────── */
.sessions-content {
  padding-top: 0;
}

.session-item {
  --padding-start: 0;
  --inner-padding-end: 0;
  --min-height: 36px;
}

.session-item ion-label h3 {
  font-size: 12px;
}

.session-item ion-label p {
  font-size: 11px;
}

.empty-state-sm {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
  color: var(--ion-color-medium);
  font-size: 12px;
}

.item-avatar-sm {
  width: 30px;
  height: 30px;
  font-size: 13px;
}

/* ── Device strip ────────────────────────────────────────── */
.device-strip-card {
  margin-bottom: 0;
}

.device-strip-card ion-card-header {
  padding-bottom: 4px;
}

.device-strip-card ion-card-content {
  padding-bottom: 10px;
}

.device-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 6px;
  scrollbar-width: none;
}
.device-scroll::-webkit-scrollbar { display: none; }

.device-card {
  flex: 0 0 auto;
  min-width: 170px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 8px 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.15s;
}
.device-card:active { transform: scale(0.97); }

.device-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 17px;
}

.device-info {
  flex: 1;
  min-width: 0;
}

.device-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--ion-color-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-types {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 3px;
}

.device-type-badge {
  font-size: 9px;
  font-weight: 600;
  border-radius: 8px;
  padding: 1px 5px;
  text-transform: capitalize;
}

.device-age {
  font-size: 9px;
  color: var(--ion-color-medium);
  flex-shrink: 0;
  white-space: nowrap;
}

/* ── Sensor readings ─────────────────────────────────────── */
.sensor-scroll-card {
  margin-bottom: 0;
}

.sensor-scroll-card ion-card-header {
  padding-bottom: 4px;
}

.sensor-scroll-card ion-card-content {
  padding-bottom: 10px;
}

.reading-count-badge {
  margin-left: 8px;
  vertical-align: middle;
}

.view-all-btn {
  margin-left: auto;
  --color: var(--ion-color-primary);
  font-size: 13px;
}

.sensor-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.sensor-scroll::-webkit-scrollbar {
  display: none;
}

.sensor-card {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  padding: 12px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: box-shadow 0.15s ease;
  flex: 0 0 150px;
}

.sensor-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.sensor-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sensor-type-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px 3px 6px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  max-width: 70%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.sensor-type-pill ion-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.sensor-age {
  font-size: 10px;
  color: var(--ion-color-medium);
  white-space: nowrap;
}

.sensor-card-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--ion-color-dark);
  line-height: 1.1;
  letter-spacing: -0.5px;
}

.sensor-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--ion-color-medium);
  margin-left: 3px;
}

.sensor-card-bottom {
  display: flex;
  align-items: center;
  gap: 5px;
  padding-top: 4px;
  border-top: 1px solid var(--ion-color-light-shade);
}

.device-icon {
  font-size: 12px;
  color: var(--ion-color-medium);
  flex-shrink: 0;
}

.sensor-device {
  font-size: 11px;
  color: var(--ion-color-medium);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ── MQTT user list ──────────────────────────────────────── */
.user-status {
  margin-top: 2px;
}

/* ── Security status ─────────────────────────────────────── */
.security-item {
  text-align: center;
  padding: 6px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.security-item h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--ion-color-dark);
  display: flex;
  align-items: center;
  gap: 4px;
}

.security-item p {
  margin: 0;
  font-size: 11px;
  color: var(--ion-color-medium);
}

.security-btn {
  margin-top: 2px;
  align-self: center;
  --padding-top: 4px;
  --padding-bottom: 4px;
}

/* ── FAB labels ──────────────────────────────────────────── */
ion-fab-list ion-fab-button {
  --box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* ── Custom toast notifications ──────────────────────────── */
.toast-container {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 99999;
  width: calc(100% - 48px);
  max-width: 360px;
  pointer-events: none;
}

.toast-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.custom-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 10px 10px;
  border-radius: 40px;
  background: rgba(22, 22, 26, 0.88);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 4px 28px rgba(0, 0, 0, 0.30), 0 1px 6px rgba(0, 0, 0, 0.18);
  pointer-events: all;
  width: 100%;
  box-sizing: border-box;
}

.toast-primary  { --toast-accent: #6eb4ff; --toast-glow: rgba(110,180,255,0.20); }
.toast-success  { --toast-accent: #4cd964; --toast-glow: rgba(76,217,100,0.20); }
.toast-warning  { --toast-accent: #ffd60a; --toast-glow: rgba(255,214,10,0.20); }
.toast-danger   { --toast-accent: #ff453a; --toast-glow: rgba(255,69,58,0.20); }

.toast-icon-wrap {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--toast-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toast-icon {
  font-size: 16px;
  color: var(--toast-accent);
}

.toast-message {
  flex: 1;
  font-size: 13.5px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.95);
  line-height: 1.35;
}

.toast-close {
  background: none;
  border: none;
  padding: 4px;
  margin: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.40);
  font-size: 16px;
  flex-shrink: 0;
  border-radius: 50%;
  transition: color 0.15s;
}
.toast-close:hover { color: rgba(255, 255, 255, 0.75); }

/* Slide-up / spring animation */
.toast-enter-active {
  animation: toast-in 0.32s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.toast-leave-active {
  animation: toast-out 0.2s ease both;
  position: absolute;
  width: 100%;
}

@keyframes toast-in {
  from { opacity: 0; transform: translateY(20px) scale(0.94); }
  to   { opacity: 1; transform: translateY(0)    scale(1); }
}

@keyframes toast-out {
  from { opacity: 1; transform: scale(1); }
  to   { opacity: 0; transform: scale(0.92); }
}
</style>