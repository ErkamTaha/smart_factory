<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar>
                <ion-title>Smart Factory Dashboard</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content :fullscreen="true">
            <!-- Header with connection status -->
            <div class="status-header">
                <ion-chip :color="isConnected ? 'success' : 'danger'">
                    <ion-icon :icon="isConnected ? checkmarkCircle : closeCircle"></ion-icon>
                    <ion-label>{{ isConnected ? 'Connected' : 'Disconnected' }}</ion-label>
                </ion-chip>
            </div>

            <!-- Loading indicator -->
            <div v-if="isLoading" class="loading-container">
                <ion-spinner name="crescent"></ion-spinner>
                <p>Loading data...</p>
            </div>

            <!-- Error message -->
            <ion-alert :is-open="!!error" header="Error" :message="error" :buttons="['OK']"
                @didDismiss="clearError"></ion-alert>

            <!-- Main content -->
            <div v-if="!isLoading">
                <!-- Stats cards -->
                <div class="stats-grid">
                    <ion-card>
                        <ion-card-content>
                            <div class="stat-item">
                                <h2>{{ deviceCount }}</h2>
                                <p>Active Devices</p>
                                <ion-icon :icon="hardwareChip" class="stat-icon"></ion-icon>
                            </div>
                        </ion-card-content>
                    </ion-card>

                    <ion-card>
                        <ion-card-content>
                            <div class="stat-item">
                                <h2>{{ totalReadings }}</h2>
                                <p>Total Readings</p>
                                <ion-icon :icon="barChart" class="stat-icon"></ion-icon>
                            </div>
                        </ion-card-content>
                    </ion-card>

                    <ion-card>
                        <ion-card-content>
                            <div class="stat-item">
                                <h2>{{ latestData.length }}</h2>
                                <p>Recent Updates</p>
                                <ion-icon :icon="time" class="stat-icon"></ion-icon>
                            </div>
                        </ion-card-content>
                    </ion-card>
                </div>

                <!-- Devices list -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Connected Devices</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list v-if="devices.length > 0">
                            <ion-item v-for="device in devices" :key="device" button @click="viewDeviceDetails(device)">
                                <ion-icon :icon="thermometerOutline" slot="start"></ion-icon>
                                <ion-label>
                                    <h3>{{ device }}</h3>
                                    <p>{{ getDeviceSensorTypes(device).join(', ') }}</p>
                                </ion-label>
                                <ion-chip slot="end" color="primary">
                                    {{ getDeviceData(device).length }} readings
                                </ion-chip>
                            </ion-item>
                        </ion-list>
                        <div v-else class="empty-state">
                            <ion-icon :icon="cloudOffline" size="large"></ion-icon>
                            <p>No devices found</p>
                            <ion-button @click="refreshData" fill="outline">
                                Refresh
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Latest readings -->
                <ion-card v-if="latestData.length > 0">
                    <ion-card-header>
                        <ion-card-title>Latest Sensor Readings</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item v-for="reading in latestData.slice(0, 5)"
                                :key="`${reading.device_id}-${reading.sensor_type}-${reading.timestamp}`">
                                <ion-avatar slot="start">
                                    <div class="device-avatar">{{ reading.device_id.charAt(0).toUpperCase() }}</div>
                                </ion-avatar>
                                <ion-label>
                                    <h3>{{ reading.device_id }}</h3>
                                    <p>{{ reading.sensor_type }}: {{ reading.value }} {{ reading.unit }}</p>
                                    <p class="timestamp">{{ formatTimestamp(reading.timestamp) }}</p>
                                </ion-label>
                                <ion-chip slot="end" :color="getSensorColor(reading.sensor_type)">
                                    {{ reading.value }}
                                </ion-chip>
                            </ion-item>
                        </ion-list>
                        <ion-button expand="block" fill="outline" @click="viewAllReadings">
                            View All Readings
                        </ion-button>
                    </ion-card-content>
                </ion-card>

                <!-- Quick actions -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Quick Actions</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="action-buttons">
                            <ion-button expand="block" @click="showPublishModal = true">
                                <ion-icon :icon="add" slot="start"></ion-icon>
                                Publish Data
                            </ion-button>
                            <ion-button expand="block" fill="outline" @click="showCommandModal = true">
                                <ion-icon :icon="send" slot="start"></ion-icon>
                                Send Command
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
                            <ion-button @click="showPublishModal = false">Close</ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content>
                    <ion-list>
                        <ion-item>
                            <ion-input v-model="newData.device_id" label="Device ID"
                                placeholder="e.g., sensor_001"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="newData.sensor_type" label="Sensor Type"
                                placeholder="e.g., temperature"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model.number="newData.value" type="number" label="Value"
                                placeholder="e.g., 23.5"></ion-input>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="newData.unit" label="Unit" placeholder="e.g., celsius"></ion-input>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="publishSensorData" :disabled="!isValidData" class="ion-margin">
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
                            <ion-button @click="showCommandModal = false">Close</ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content>
                    <ion-list>
                        <ion-item>
                            <ion-select v-model="newCommand.device_id" label="Device" placeholder="Select device">
                                <ion-select-option v-for="device in devices" :key="device" :value="device">
                                    {{ device }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>
                        <ion-item>
                            <ion-input v-model="newCommand.command" label="Command"
                                placeholder="e.g., get_status"></ion-input>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="sendDeviceCommand" :disabled="!isValidCommand"
                        class="ion-margin">
                        Send Command
                    </ion-button>
                </ion-content>
            </ion-modal>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons, IonButton,
    IonIcon, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonList,
    IonItem, IonLabel, IonChip, IonSpinner, IonAlert, IonAvatar, IonModal,
    IonInput, IonSelect, IonSelectOption
} from '@ionic/vue';
import {
    refreshOutline, checkmarkCircle, closeCircle, hardwareChip, barChart,
    time, thermometerOutline, cloudOffline, add, send
} from 'ionicons/icons';
import { useIotStore } from '@/stores/iot';

// Store and router
const iotStore = useIotStore();
const router = useRouter();

// Reactive references from store
const {
    devices, latestData, isLoading, error, isConnected,
    deviceCount, totalReadings
} = iotStore;

// Modal states
const showPublishModal = ref(false);
const showCommandModal = ref(false);

// Form data
const newData = ref({
    device_id: '',
    sensor_type: '',
    value: 0,
    unit: ''
});

const newCommand = ref({
    device_id: '',
    command: ''
});

// Computed
const isValidData = computed(() => {
    return newData.value.device_id &&
        newData.value.sensor_type &&
        newData.value.unit &&
        newData.value.value !== null;
});

const isValidCommand = computed(() => {
    return newCommand.value.device_id && newCommand.value.command;
});

// Methods
const refreshData = async () => {
    await iotStore.refreshAll();
};

const clearError = () => {
    iotStore.clearError();
};

const viewDeviceDetails = (deviceId) => {
    router.push(`/device/${deviceId}`);
};

const viewAllReadings = () => {
    router.push('/readings');
};

const getDeviceData = (deviceId) => {
    return iotStore.getDeviceData(deviceId);
};

const getDeviceSensorTypes = (deviceId) => {
    return iotStore.getDeviceSensorTypes(deviceId);
};

const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleString();
};

const getSensorColor = (sensorType) => {
    const colors = {
        temperature: 'danger',
        humidity: 'primary',
        pressure: 'warning',
        default: 'medium'
    };
    return colors[sensorType] || colors.default;
};

const publishSensorData = async () => {
    try {
        await iotStore.publishData(newData.value);
        showPublishModal.value = false;
        // Reset form
        newData.value = { device_id: '', sensor_type: '', value: 0, unit: '' };
    } catch (err) {
        console.error('Failed to publish data:', err);
    }
};

const sendDeviceCommand = async () => {
    try {
        await iotStore.sendCommand(newCommand.value);
        showCommandModal.value = false;
        // Reset form
        newCommand.value = { device_id: '', command: '' };
    } catch (err) {
        console.error('Failed to send command:', err);
    }
};

// Lifecycle
onMounted(() => {
    refreshData();
});
</script>

<style scoped>
.status-header {
    padding: 16px;
    background: var(--ion-color-light);
    text-align: center;
}

.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
    padding: 16px;
}

.stat-item {
    text-align: center;
    position: relative;
}

.stat-item h2 {
    margin: 0;
    font-size: 2rem;
    font-weight: bold;
}

.stat-item p {
    margin: 4px 0 0 0;
    font-size: 0.8rem;
    color: var(--ion-color-medium);
}

.stat-icon {
    position: absolute;
    top: 0;
    right: 0;
    font-size: 1.5rem;
    opacity: 0.3;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--ion-color-medium);
}

.device-avatar {
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

.timestamp {
    font-size: 0.7rem;
    color: var(--ion-color-medium);
}

.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
</style>