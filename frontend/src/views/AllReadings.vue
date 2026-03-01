<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button color="light" default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>All Readings</ion-title>
                <ion-buttons slot="end">
                    <ion-button color="light" title="Refresh" @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content>
            <!-- Filter section -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>Filters</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item>
                            <ion-select v-model="selectedDevice" label="Device" placeholder="All Devices"
                                @selection-change="applyFilters">
                                <ion-select-option value="">All Devices</ion-select-option>
                                <ion-select-option v-for="device in devices" :key="device" :value="device">
                                    {{ device }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>
                        <ion-item>
                            <ion-select v-model="selectedSensorType" label="Sensor Type" placeholder="All Types"
                                @selection-change="applyFilters">
                                <ion-select-option value="">All Types</ion-select-option>
                                <ion-select-option v-for="type in allSensorTypes" :key="type" :value="type">
                                    {{ type }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" fill="outline" @click="clearFilters">
                        Clear Filters
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Loading indicator -->
            <div v-if="isLoading" class="page-loading">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading readings...</p>
            </div>

            <!-- Readings list -->
            <ion-card v-else-if="filteredReadings.length > 0">
                <ion-card-header>
                    <ion-card-title>
                        <ion-icon :icon="thermometerOutline"></ion-icon>
                        Sensor Readings
                        <ion-chip color="primary" style="margin-left:auto">{{ filteredReadings.length }}</ion-chip>
                    </ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-list>
                        <ion-item v-for="reading in filteredReadings"
                            :key="`${reading.device_id}-${reading.sensor_type}-${reading.timestamp}`">
                            <div slot="start" class="item-avatar">{{ reading.device_id.charAt(0).toUpperCase() }}</div>
                            <ion-label>
                                <h3>{{ reading.device_id }}</h3>
                                <p><strong>{{ reading.sensor_type }}</strong>: {{ reading.value }} {{ reading.unit }}</p>
                                <p class="text-muted">{{ formatTimestamp(reading.timestamp) }}</p>
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
                        <p>No readings found</p>
                        <p v-if="selectedDevice || selectedSensorType" class="filter-info">
                            Try adjusting your filters or refresh the data
                        </p>
                        <ion-button @click="refreshData" fill="outline">
                            Refresh Data
                        </ion-button>
                    </div>
                </ion-card-content>
            </ion-card>

            <!-- Load more button -->
            <div v-if="filteredReadings.length > 0" class="load-more-container">
                <ion-button expand="block" fill="outline" @click="loadMoreData" :disabled="isLoading">
                    Load More Data
                </ion-button>
            </div>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons,
    IonButton, IonBackButton, IonIcon, IonCard, IonCardContent,
    IonCardHeader, IonCardTitle, IonList, IonItem, IonLabel,
    IonChip, IonSpinner, IonSelect, IonSelectOption
} from '@ionic/vue';
import {
    refreshOutline, cloudOffline, thermometerOutline
} from 'ionicons/icons';
import { useIotStore } from '@/stores/iot';

// Store
const iotStore = useIotStore();

// Reactive data
const selectedDevice = ref('');
const selectedSensorType = ref('');

// Computed properties
const devices = computed(() => iotStore.devices);
const latestData = computed(() => iotStore.latestData);
const isLoading = computed(() => iotStore.isLoading);

const allSensorTypes = computed(() => {
    const types = new Set();
    latestData.value.forEach(reading => {
        types.add(reading.sensor_type);
    });
    return Array.from(types).sort();
});

const filteredReadings = computed(() => {
    let readings = [...latestData.value];

    if (selectedDevice.value) {
        readings = readings.filter(reading => reading.device_id === selectedDevice.value);
    }

    if (selectedSensorType.value) {
        readings = readings.filter(reading => reading.sensor_type === selectedSensorType.value);
    }

    return readings;
});

// Methods
const refreshData = async () => {
    try {
        await iotStore.fetchLatestData(50); // Get more data for this view
    } catch (error) {
        console.error('Failed to refresh data:', error);
    }
};

const loadMoreData = async () => {
    try {
        // Load more data with higher limit
        await iotStore.fetchLatestData(100);
    } catch (error) {
        console.error('Failed to load more data:', error);
    }
};

const applyFilters = () => {
    // Filters are automatically applied through computed property
    console.log('Filters applied:', {
        device: selectedDevice.value,
        sensorType: selectedSensorType.value
    });
};

const clearFilters = () => {
    selectedDevice.value = '';
    selectedSensorType.value = '';
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

// Lifecycle
onMounted(() => {
    refreshData();
});
</script>

<style scoped>
/* page-loading, empty-state, item-avatar, text-muted are in global.css */
.load-more-container {
  padding: 8px 16px 16px;
}
</style>