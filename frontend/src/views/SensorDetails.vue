<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button color="light" default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>Sensor Details</ion-title>
                <ion-buttons slot="end">
                    <ion-button color="light" title="Refresh" @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content>
            <div v-if="isLoading" class="page-loading">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading sensor data...</p>
            </div>

            <div v-else>
                <!-- Latest Readings -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            <ion-icon :icon="thermometerOutline"></ion-icon>
                            Latest Sensor Readings
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list v-if="factoryStore.latestSensorData.length > 0">
                            <ion-item v-for="reading in factoryStore.latestSensorData" :key="reading.id">
                                <ion-icon :icon="getIconForSensorType(reading.sensor_type)" slot="start"></ion-icon>
                                <ion-label>
                                    <h3>{{ reading.sensor_type }} — {{ reading.device_id }}</h3>
                                    <p>{{ reading.value }} {{ reading.unit }}</p>
                                    <p class="text-muted">{{ formatTimestamp(reading.timestamp) }}</p>
                                </ion-label>
                                <ion-chip slot="end" :color="getSensorColor(reading.sensor_type)">
                                    {{ reading.value }}
                                </ion-chip>
                            </ion-item>
                        </ion-list>
                        <div v-else class="empty-state">
                            <ion-icon :icon="cloudOffline" size="large"></ion-icon>
                            <p>No sensor readings available</p>
                            <ion-button @click="refreshData" fill="outline">Refresh</ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons,
    IonButton, IonBackButton, IonIcon, IonCard, IonCardContent,
    IonCardHeader, IonCardTitle, IonList, IonItem, IonLabel,
    IonChip, IonSpinner
} from '@ionic/vue';
import {
    refreshOutline, thermometerOutline, waterOutline, speedometerOutline,
    cloudOffline, hardwareChip
} from 'ionicons/icons';
import { useFactoryStore } from '@/stores/factory';

const factoryStore = useFactoryStore();

const isLoading = computed(() => factoryStore.isLoading);

const refreshData = async () => {
    await factoryStore.loadLatestData();
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
    };
    return colors[sensorType] || 'medium';
};

const getIconForSensorType = (sensorType) => {
    const icons = {
        temperature: thermometerOutline,
        humidity: waterOutline,
        pressure: speedometerOutline,
    };
    return icons[sensorType] || hardwareChip;
};

onMounted(() => {
    refreshData();
});
</script>

<style scoped>
/* page-loading, empty-state, text-muted are in global.css */
</style>
