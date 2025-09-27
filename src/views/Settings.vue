<template>
    <ion-page>
        <ion-header>
            <ion-toolbar>
                <ion-buttons slot="start">
                    <ion-back-button default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>Settings</ion-title>
            </ion-toolbar>
        </ion-header>

        <ion-content>
            <!-- API Configuration -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>API Configuration</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item>
                            <ion-input v-model="apiUrl" label="Backend URL"
                                placeholder="http://localhost:8000"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-toggle v-model="autoRefresh" @ionChange="toggleAutoRefresh">
                                Auto Refresh Data
                            </ion-toggle>
                        </ion-item>
                        <ion-item v-if="autoRefresh">
                            <ion-select v-model="refreshInterval" label="Refresh Interval"
                                @selection-change="updateRefreshInterval">
                                <ion-select-option :value="5000">5 seconds</ion-select-option>
                                <ion-select-option :value="10000">10 seconds</ion-select-option>
                                <ion-select-option :value="30000">30 seconds</ion-select-option>
                                <ion-select-option :value="60000">1 minute</ion-select-option>
                            </ion-select>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="saveApiSettings">
                        Save API Settings
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Connection Status -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>Connection Status</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item>
                            <ion-icon :icon="serverOutline" slot="start"></ion-icon>
                            <ion-label>
                                <h3>Backend Connection</h3>
                                <p>{{ isConnected ? 'Connected' : 'Disconnected' }}</p>
                            </ion-label>
                            <ion-chip slot="end" :color="isConnected ? 'success' : 'danger'">
                                {{ isConnected ? 'Online' : 'Offline' }}
                            </ion-chip>
                        </ion-item>
                        <ion-item>
                            <ion-icon :icon="wifiOutline" slot="start"></ion-icon>
                            <ion-label>
                                <h3>MQTT Status</h3>
                                <p>{{ mqttStatus || 'Unknown' }}</p>
                            </ion-label>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" fill="outline" @click="testConnection">
                        Test Connection
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Data Management -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>Data Management</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item>
                            <ion-label>
                                <h3>Total Devices</h3>
                                <p>{{ deviceCount }} devices connected</p>
                            </ion-label>
                        </ion-item>
                        <ion-item>
                            <ion-label>
                                <h3>Total Readings</h3>
                                <p>{{ totalReadings }} sensor readings</p>
                            </ion-label>
                        </ion-item>
                    </ion-list>
                    <div class="button-group">
                        <ion-button expand="block" @click="refreshAllData" :disabled="isLoading">
                            <ion-icon :icon="refreshOutline" slot="start"></ion-icon>
                            Refresh All Data
                        </ion-button>
                        <ion-button expand="block" fill="outline" color="warning" @click="showClearDataAlert">
                            <ion-icon :icon="trashOutline" slot="start"></ion-icon>
                            Clear Local Data
                        </ion-button>
                    </div>
                </ion-card-content>
            </ion-card>

            <!-- App Information -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>App Information</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item>
                            <ion-label>
                                <h3>App Version</h3>
                                <p>1.0.0</p>
                            </ion-label>
                        </ion-item>
                        <ion-item>
                            <ion-label>
                                <h3>Framework</h3>
                                <p>Ionic Vue with JavaScript</p>
                            </ion-label>
                        </ion-item>
                        <ion-item>
                            <ion-label>
                                <h3>Last Updated</h3>
                                <p>{{ lastUpdated }}</p>
                            </ion-label>
                        </ion-item>
                    </ion-list>
                </ion-card-content>
            </ion-card>

            <!-- Clear Data Alert -->
            <ion-alert :is-open="showClearAlert" header="Clear Local Data"
                message="Are you sure you want to clear all local data? This action cannot be undone."
                :buttons="clearDataButtons" @didDismiss="showClearAlert = false"></ion-alert>

            <!-- Toast for feedback -->
            <ion-toast :is-open="showToast" :message="toastMessage" :duration="3000"
                @didDismiss="showToast = false"></ion-toast>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons,
    IonButton, IonBackButton, IonIcon, IonCard, IonCardContent,
    IonCardHeader, IonCardTitle, IonList, IonItem, IonLabel,
    IonChip, IonInput, IonToggle, IonSelect, IonSelectOption,
    IonAlert, IonToast
} from '@ionic/vue';
import {
    serverOutline, wifiOutline, refreshOutline, trashOutline
} from 'ionicons/icons';
import { useIotStore } from '@/stores/iot';
import apiService from '@/services/api';

// Store
const iotStore = useIotStore();

// Reactive data
const apiUrl = ref('http://localhost:8000');
const autoRefresh = ref(false);
const refreshInterval = ref(30000);
const showClearAlert = ref(false);
const showToast = ref(false);
const toastMessage = ref('');
const refreshTimer = ref(null);
const mqttStatus = ref('Unknown');

// Computed properties
const isConnected = computed(() => iotStore.isConnected);
const deviceCount = computed(() => iotStore.deviceCount);
const totalReadings = computed(() => iotStore.totalReadings);
const isLoading = computed(() => iotStore.isLoading);
const lastUpdated = computed(() => new Date().toLocaleString());

// Alert buttons
const clearDataButtons = [
    {
        text: 'Cancel',
        role: 'cancel'
    },
    {
        text: 'Clear Data',
        role: 'destructive',
        handler: () => {
            clearLocalData();
        }
    }
];

// Methods
const saveApiSettings = () => {
    try {
        // Update API base URL
        apiService.updateBaseURL(apiUrl.value);

        // Save to localStorage
        localStorage.setItem('apiUrl', apiUrl.value);
        localStorage.setItem('autoRefresh', autoRefresh.value.toString());
        localStorage.setItem('refreshInterval', refreshInterval.value.toString());

        showToastMessage('Settings saved successfully');
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToastMessage('Failed to save settings');
    }
};

const loadSettings = () => {
    try {
        const savedApiUrl = localStorage.getItem('apiUrl');
        const savedAutoRefresh = localStorage.getItem('autoRefresh');
        const savedRefreshInterval = localStorage.getItem('refreshInterval');

        if (savedApiUrl) {
            apiUrl.value = savedApiUrl;
            apiService.updateBaseURL(savedApiUrl);
        }

        if (savedAutoRefresh) {
            autoRefresh.value = savedAutoRefresh === 'true';
        }

        if (savedRefreshInterval) {
            refreshInterval.value = parseInt(savedRefreshInterval);
        }

        if (autoRefresh.value) {
            startAutoRefresh();
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
};

const testConnection = async () => {
    try {
        const health = await iotStore.checkConnection();
        mqttStatus.value = health.mqtt_status || 'Unknown';
        showToastMessage('Connection test completed');
    } catch (error) {
        showToastMessage('Connection test failed');
    }
};

const refreshAllData = async () => {
    try {
        await iotStore.refreshAll();
        showToastMessage('Data refreshed successfully');
    } catch (error) {
        showToastMessage('Failed to refresh data');
    }
};

const clearLocalData = () => {
    try {
        // Clear store data
        iotStore.devices = [];
        iotStore.sensorData = {};
        iotStore.latestData = [];

        showToastMessage('Local data cleared');
    } catch (error) {
        showToastMessage('Failed to clear data');
    }
};

const showClearDataAlert = () => {
    showClearAlert.value = true;
};

const showToastMessage = (message) => {
    toastMessage.value = message;
    showToast.value = true;
};

const toggleAutoRefresh = () => {
    if (autoRefresh.value) {
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
};

const updateRefreshInterval = () => {
    if (autoRefresh.value) {
        stopAutoRefresh();
        startAutoRefresh();
    }
};

const startAutoRefresh = () => {
    if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
    }

    refreshTimer.value = setInterval(async () => {
        try {
            await iotStore.refreshAll();
        } catch (error) {
            console.error('Auto refresh failed:', error);
        }
    }, refreshInterval.value);
};

const stopAutoRefresh = () => {
    if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
    }
};

// Lifecycle
onMounted(() => {
    loadSettings();
    testConnection();
});

onUnmounted(() => {
    stopAutoRefresh();
});
</script>

<style scoped>
.button-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
}
</style>