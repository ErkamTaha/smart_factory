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
            <ion-card class="filter-card">
                <ion-card-content>
                    <div class="filter-row">
                        <ion-select
                            v-model="selectedDevice"
                            label="Device"
                            label-placement="floating"
                            placeholder="All Devices"
                            interface="popover"
                            @ionChange="applyFilters"
                            class="filter-select"
                        >
                            <ion-select-option value="">All Devices</ion-select-option>
                            <ion-select-option v-for="device in deviceNames" :key="device" :value="device">
                                {{ device }}
                            </ion-select-option>
                        </ion-select>

                        <ion-select
                            v-model="selectedSensorType"
                            label="Sensor Type"
                            label-placement="floating"
                            placeholder="All Types"
                            interface="popover"
                            @ionChange="applyFilters"
                            class="filter-select"
                        >
                            <ion-select-option value="">All Types</ion-select-option>
                            <ion-select-option v-for="type in sensorTypes" :key="type" :value="type">
                                {{ type }}
                            </ion-select-option>
                        </ion-select>

                        <ion-button fill="outline" size="small" @click="clearFilters" class="clear-btn">
                            <ion-icon :icon="closeOutline" slot="icon-only"></ion-icon>
                        </ion-button>
                    </div>
                </ion-card-content>
            </ion-card>

            <!-- Loading indicator -->
            <div v-if="isLoading && readings.length === 0" class="page-loading">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading readings...</p>
            </div>

            <!-- Readings list -->
            <ion-card v-else-if="filteredReadings.length > 0">
                <ion-card-header>
                    <ion-card-title>
                        <ion-icon :icon="thermometerOutline"></ion-icon>
                        Sensor Readings
                        <ion-chip color="primary" style="margin-left:auto">
                            {{ filteredReadings.length }}{{ hasMore ? '+' : '' }}
                        </ion-chip>
                    </ion-card-title>
                </ion-card-header>
                <ion-card-content style="padding: 0">
                    <ion-list lines="full">
                        <ion-item v-for="reading in filteredReadings" :key="reading.id">
                            <div slot="start" class="sensor-avatar" :class="getSensorClass(reading.sensor_type)">
                                <ion-icon :icon="getSensorIcon(reading.sensor_type)"></ion-icon>
                            </div>
                            <ion-label>
                                <h3>{{ reading.device_name || reading.device_id }}</h3>
                                <p>
                                    <strong>{{ reading.sensor_type }}</strong>
                                    &nbsp;·&nbsp;
                                    <span class="reading-value">{{ reading.value }} {{ reading.unit }}</span>
                                </p>
                                <p class="text-muted">{{ formatTimestamp(reading.timestamp) }}</p>
                            </ion-label>
                            <ion-chip slot="end" :color="getSensorColor(reading.sensor_type)" outline>
                                {{ reading.value }} {{ reading.unit }}
                            </ion-chip>
                        </ion-item>
                    </ion-list>
                </ion-card-content>
            </ion-card>

            <!-- Empty state -->
            <ion-card v-else-if="!isLoading">
                <ion-card-content>
                    <div class="empty-state">
                        <ion-icon :icon="cloudOfflineOutline" size="large"></ion-icon>
                        <p>No readings found</p>
                        <p v-if="selectedDevice || selectedSensorType" class="text-muted">
                            Try clearing your filters
                        </p>
                        <ion-button @click="refreshData" fill="outline">Refresh</ion-button>
                    </div>
                </ion-card-content>
            </ion-card>

            <!-- Load more -->
            <div v-if="filteredReadings.length > 0 && hasMore" class="load-more-container">
                <ion-button fill="outline" @click="loadMore" :disabled="isLoading">
                    <ion-spinner v-if="isLoading" name="crescent" slot="start"></ion-spinner>
                    Load More
                </ion-button>
            </div>

            <div v-if="filteredReadings.length > 0 && !hasMore" class="end-label">
                All readings loaded
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
    refreshOutline, cloudOfflineOutline, thermometerOutline,
    closeOutline, waterOutline, speedometerOutline, moveOutline
} from 'ionicons/icons';
import apiService from '@/services/api';

// --- State ---
const readings = ref([]);
const isLoading = ref(false);
const limit = ref(50);
const hasMore = ref(true);

const selectedDevice = ref('');
const selectedSensorType = ref('');

// --- Derived lists for filters ---
const deviceNames = computed(() => {
    const names = new Set(readings.value.map(r => r.device_name || r.device_id).filter(Boolean));
    return Array.from(names).sort();
});

const sensorTypes = computed(() => {
    const types = new Set(readings.value.map(r => r.sensor_type).filter(Boolean));
    return Array.from(types).sort();
});

// --- Filtered view ---
const filteredReadings = computed(() => {
    let list = readings.value;
    if (selectedDevice.value) {
        list = list.filter(r => (r.device_name || r.device_id) === selectedDevice.value);
    }
    if (selectedSensorType.value) {
        list = list.filter(r => r.sensor_type === selectedSensorType.value);
    }
    return list;
});

// --- Data fetching ---
const fetchReadings = async (newLimit = limit.value) => {
    try {
        isLoading.value = true;
        const response = await apiService.getLatestData(newLimit);
        const raw = response.data?.readings || [];
        // Normalise field names to match what the template expects
        readings.value = raw.map(r => ({
            id: r.id,
            device_id: r.device_identifier || String(r.device_id),
            device_name: r.device_name || r.device_identifier || String(r.device_id),
            sensor_type: r.sensor_type_name || r.sensor_type || String(r.sensor_type_id),
            value: r.value,
            unit: r.unit,
            timestamp: r.timestamp,
        }));
        hasMore.value = raw.length >= newLimit;
    } catch (err) {
        console.error('Failed to load readings:', err);
    } finally {
        isLoading.value = false;
    }
};

const refreshData = () => {
    limit.value = 50;
    fetchReadings(50);
};

const loadMore = () => {
    limit.value += 50;
    fetchReadings(limit.value);
};

const applyFilters = () => { /* reactive */ };

const clearFilters = () => {
    selectedDevice.value = '';
    selectedSensorType.value = '';
};

// --- Helpers ---
const formatTimestamp = (ts) => {
    if (!ts) return '—';
    return new Date(ts).toLocaleString();
};

const getSensorColor = (type) => {
    const map = { temperature: 'danger', humidity: 'primary', pressure: 'warning', motion: 'success' };
    return map[type] || 'medium';
};

const getSensorClass = (type) => {
    return `sensor-avatar-${type || 'default'}`;
};

const getSensorIcon = (type) => {
    const map = {
        temperature: thermometerOutline,
        humidity: waterOutline,
        pressure: speedometerOutline,
        motion: moveOutline,
    };
    return map[type] || thermometerOutline;
};

onMounted(() => fetchReadings());
</script>

<style scoped>
.filter-card {
  margin: 12px 16px 0;
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.filter-select {
  flex: 1;
  min-width: 0;
}

.clear-btn {
  flex-shrink: 0;
}

.sensor-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin-right: 4px;
}

.sensor-avatar-temperature { background: rgba(235, 68, 90, 0.12); color: var(--ion-color-danger); }
.sensor-avatar-humidity    { background: rgba(56, 128, 255, 0.12); color: var(--ion-color-primary); }
.sensor-avatar-pressure    { background: rgba(255, 196, 9, 0.15);  color: var(--ion-color-warning); }
.sensor-avatar-motion      { background: rgba(45, 211, 111, 0.12); color: var(--ion-color-success); }
.sensor-avatar-default     { background: rgba(146, 148, 156, 0.15); color: var(--ion-color-medium); }

.reading-value {
  font-weight: 600;
}

.load-more-container {
  display: flex;
  justify-content: center;
  padding: 12px 16px 20px;
}

.end-label {
  text-align: center;
  font-size: 12px;
  color: var(--ion-color-medium);
  padding: 8px 0 20px;
}
</style>
