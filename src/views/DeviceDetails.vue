<template>
    <ion-page>
        <ion-header>
            <ion-toolbar>
                <ion-buttons slot="start">
                    <ion-back-button default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>{{ deviceId }}</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="refreshDeviceData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content>
            <div v-if="isLoading" class="loading-container">
                <ion-spinner name="crescent"></ion-spinner>
                <p>Loading device data...</p>
            </div>

            <div v-else>
                <!-- Device info card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Device Information</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item>
                                <ion-label>
                                    <h3>Device ID</h3>
                                    <p>{{ deviceId }}</p>
                                </ion-label>
                            </ion-item>
                            <ion-item>
                                <ion-label>
                                    <h3>Sensor Types</h3>
                                    <p>{{ sensorTypes.join(', ') || 'None' }}</p>
                                </ion-label>
                            </ion-item>
                            <ion-item>
                                <ion-label>
                                    <h3>Total Readings</h3>
                                    <p>{{ deviceData.length }}</p>
                                </ion-label>
                            </ion-item>
                            <ion-item v-if="latestReading">
                                <ion-label>
                                    <h3>Last Updated</h3>
                                    <p>{{ formatTimestamp(latestReading.timestamp) }}</p>
                                </ion-label>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>

                <!-- Sensor readings -->
                <ion-card v-if="deviceData.length > 0">
                    <ion-card-header>
                        <ion-card-title>Recent Readings</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item v-for="reading in deviceData"
                                :key="`${reading.sensor_type}-${reading.timestamp}`">
                                <ion-icon :icon="getIconForSensorType(reading.sensor_type)" slot="start"></ion-icon>
                                <ion-label>
                                    <h3>{{ reading.sensor_type }}</h3>
                                    <p>{{ reading.value }} {{ reading.unit }}</p>
                                    <p class="timestamp">{{ formatTimestamp(reading.timestamp) }}</p>
                                </ion-label>
                                <ion-chip slot="end" :color="getSensorColor(reading.sensor_type)">
                                    {{ reading.value }}
                                </ion-chip>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>

                <!-- Empty state -->
                <ion-card v-else>
                    <ion-card-content>
                        <div class="empty-state">
                            <ion-icon :icon="cloudOffline" size="large"></ion-icon>
                            <p>No data found for this device</p>
                            <ion-button @click="refreshDeviceData" fill="outline">
                                Refresh
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Send command section -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Send Command</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item>
                                <ion-input v-model="commandToSend" label="Command"
                                    placeholder="e.g., get_status, restart, calibrate"></ion-input>
                            </ion-item>
                        </ion-list>
                        <ion-button expand="block" @click="sendCommand" :disabled="!commandToSend.trim()">
                            <ion-icon :icon="send" slot="start"></ion-icon>
                            Send Command
                        </ion-button>
                    </ion-card-content>
                </ion-card>
            </div>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted, defineProps } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons,
    IonButton, IonBackButton, IonIcon, IonCard, IonCardContent,
    IonCardHeader, IonCardTitle, IonList, IonItem, IonLabel,
    IonChip, IonSpinner, IonInput
} from '@ionic/vue';
import {
    refreshOutline, thermometerOutline, waterOutline, speedometerOutline,
    cloudOffline, send, hardwareChip
} from 'ionicons/icons';
import { useIotStore } from '@/stores/iot';

// Props
const props = defineProps({
    id: {
        type: String,
        required: true
    }
});

// Store
const iotStore = useIotStore();

// Reactive data
const commandToSend = ref('');
const deviceId = ref(props.id);

// Computed properties
const deviceData = computed(() => iotStore.getDeviceData(deviceId.value));
const sensorTypes = computed(() => iotStore.getDeviceSensorTypes(deviceId.value));
const isLoading = computed(() => iotStore.isLoading);
const latestReading = computed(() => {
    const data = deviceData.value;
    return data.length > 0 ? data[0] : null;
});

// Methods
const refreshDeviceData = async () => {
    try {
        await iotStore.fetchDeviceData(deviceId.value, 20);
    } catch (error) {
        console.error('Failed to refresh device data:', error);
    }
};

const sendCommand = async () => {
    try {
        await iotStore.sendCommand({
            device_id: deviceId.value,
            command: commandToSend.value.trim()
        });
        commandToSend.value = '';
        // Show success feedback (you could add a toast here)
        console.log('Command sent successfully');
    } catch (error) {
        console.error('Failed to send command:', error);
    }
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
        voltage: 'success',
        current: 'tertiary',
        default: 'medium'
    };
    return colors[sensorType] || colors.default;
};

const getIconForSensorType = (sensorType) => {
    const icons = {
        temperature: thermometerOutline,
        humidity: waterOutline,
        pressure: speedometerOutline,
        voltage: hardwareChip,
        current: hardwareChip,
        default: hardwareChip
    };
    return icons[sensorType] || icons.default;
};

// Lifecycle
onMounted(() => {
    refreshDeviceData();
});
</script>

<style scoped>
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--ion-color-medium);
}

.timestamp {
    font-size: 0.7rem;
    color: var(--ion-color-medium);
}
</style>