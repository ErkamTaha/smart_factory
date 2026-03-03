<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button color="light" default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>
                    <div class="toolbar-title">
                        <ion-icon :icon="shieldCheckmarkOutline"></ion-icon>
                        Sensor Security
                    </div>
                </ion-title>
                <ion-buttons slot="end">
                    <ion-button color="light" title="Refresh" @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content class="ion-padding">
            <!-- SS Status Card -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>
                        <ion-icon :icon="shieldCheckmarkOutline"></ion-icon>
                        Sensor Security Status
                    </ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-grid v-if="ssInfo">
                        <ion-row>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ sensors.length }}</h2>
                                    <p>All Sensors</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ activeSensors }}</h2>
                                    <p>Active Sensors</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ ssInfo.total_types }}</h2>
                                    <p>Sensor Types</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ activeAlertCount }}</h2>
                                    <p>Active Alerts</p>
                                </div>
                            </ion-col>
                        </ion-row>
                    </ion-grid>
                </ion-card-content>
            </ion-card>

            <!-- Tabs for Sensors and Alerts -->
            <ion-segment v-model="activeTab" class="tab-segment" @ion-change="onSegmentChange">
                <ion-segment-button value="sensors">
                    <ion-label>Sensors</ion-label>
                </ion-segment-button>
                <ion-segment-button value="alerts">
                    <ion-label>Alerts</ion-label>
                </ion-segment-button>
                <ion-segment-button value="config">
                    <ion-label>Configuration</ion-label>
                </ion-segment-button>
            </ion-segment>

            <!-- Sensors Tab -->
            <div v-show="activeTab === 'sensors'">
                <!-- Add Sensor Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Add New Sensor</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <!-- Row 1: Sensor ID + Sensor Type -->
                        <ion-grid class="form-grid">
                            <ion-row>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-input v-model="newSensor.sensorId" label="Sensor ID"
                                            placeholder="e.g., temp_sensor_01"
                                            label-placement="stacked"
                                            @ion-input="onNewSensorIdInput"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-select v-model="newSensor.sensorType" label="Sensor Type"
                                            placeholder="Select type" label-placement="stacked"
                                            interface="popover">
                                            <ion-select-option v-for="type in sensorTypeOptions" :key="type" :value="type">
                                                {{ type }}
                                            </ion-select-option>
                                        </ion-select>
                                    </ion-item>
                                </ion-col>
                            </ion-row>

                            <!-- Row 2: Topic Pattern + Active -->
                            <ion-row>
                                <ion-col size="12" size-md="9">
                                    <ion-item>
                                        <ion-input v-model="newSensor.pattern" label="Topic Pattern"
                                            label-placement="stacked"
                                            :helper-text="patternAutoFilled ? 'Auto-generated — edit to customise' : 'Custom pattern'"
                                            @ion-input="patternAutoFilled = false"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="3" class="toggle-col">
                                    <ion-item lines="none">
                                        <ion-label>Active</ion-label>
                                        <ion-toggle v-model="newSensor.is_active" slot="end"></ion-toggle>
                                    </ion-item>
                                </ion-col>
                            </ion-row>
                        </ion-grid>

                        <!-- Sensor Limits Configuration -->
                        <div class="limits-section">
                            <h4>Sensor Limits</h4>
                            <div v-for="(limit, index) in newSensor.limits" :key="index" class="limit-edit">
                                <ion-grid>
                                    <ion-row>
                                        <ion-col size="12" size-md="3">
                                            <ion-item>
                                                <ion-input v-model="limit.name" label="Name"
                                                    placeholder="e.g., normal" label-placement="stacked"></ion-input>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="6" size-md="2">
                                            <ion-item>
                                                <ion-input v-model.number="limit.upper_limit" type="number"
                                                    label="Upper" label-placement="stacked"></ion-input>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="6" size-md="2">
                                            <ion-item>
                                                <ion-input v-model.number="limit.lower_limit" type="number"
                                                    label="Lower" label-placement="stacked"></ion-input>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="6" size-md="2">
                                            <ion-item>
                                                <ion-select v-model="limit.unit" label="Unit"
                                                    placeholder="Select" label-placement="stacked"
                                                    interface="popover">
                                                    <ion-select-option v-for="unit in getUnitOptionsWithCurrent(newSensor.sensorType, limit.unit)" :key="unit" :value="unit">
                                                        {{ unit }}
                                                    </ion-select-option>
                                                </ion-select>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="4" size-md="2">
                                            <ion-item lines="none">
                                                <ion-label>Selected</ion-label>
                                                <ion-toggle v-model="limit.is_selected" slot="end"></ion-toggle>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="2" size-md="1" class="del-col">
                                            <ion-button fill="clear" color="danger" @click="removeLimitConfig(index)">
                                                <ion-icon :icon="trashOutline"></ion-icon>
                                            </ion-button>
                                        </ion-col>
                                    </ion-row>
                                </ion-grid>
                            </div>
                            <ion-button @click="addLimitConfig" fill="outline" size="small">
                                <ion-icon :icon="addOutline" slot="start"></ion-icon>
                                Add Limit
                            </ion-button>
                        </div>

                        <div v-if="addError" class="inline-error">{{ addError }}</div>
                        <ion-button @click="createSensor" :disabled="!isValidNewSensor" class="ion-margin-top">
                            <ion-icon :icon="addCircleOutline" slot="start"></ion-icon>
                            Add Sensor
                        </ion-button>
                    </ion-card-content>
                </ion-card>

                <!-- Sensors List -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Sensors ({{ sensors.length }})</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-searchbar v-model="sensorSearchTerm" placeholder="Search sensors..."
                            @ion-input="filterSensors"></ion-searchbar>

                        <ion-list>
                            <ion-item v-for="sensor in filteredSensors" :key="sensor.sensor_id" class="sensor-item">
                                <ion-label>
                                    <h2><strong>{{ sensor.sensor_id }}</strong></h2>
                                    <p><strong>Pattern:</strong> {{ sensor.pattern }}</p>
                                    <p><strong>Type:</strong> {{ sensor.sensor_type }}</p>
                                    <p>
                                        <ion-chip :color="sensor.is_active ? 'success' : 'danger'" size="small">
                                            {{ sensor.is_active ? 'Active' : 'Inactive' }}
                                        </ion-chip>
                                        <ion-chip v-if="sensor.selected_limit" color="primary" size="small">
                                            <strong class="limit-name">
                                                {{
                                                    sensor.selected_limit.name.charAt(0).toUpperCase()
                                                    + sensor.selected_limit.name.slice(1)
                                                }}
                                            </strong>
                                            ({{ sensor.selected_limit.lower_limit }}),
                                            ({{ sensor.selected_limit.upper_limit }}),
                                            {{ sensor.selected_limit.unit }}
                                        </ion-chip>

                                    </p>
                                </ion-label>
                                <ion-button slot="end" fill="clear" @click="editSensor(sensor)">
                                    <ion-icon :icon="createOutline"></ion-icon>
                                </ion-button>
                                <ion-button slot="end" fill="clear" @click="viewSensorDetails(sensor)">
                                    <ion-icon :icon="eyeOutline"></ion-icon>
                                </ion-button>
                                <ion-button slot="end" fill="clear" color="danger"
                                    @click="deleteSensor(sensor.sensor_id)">
                                    <ion-icon :icon="banOutline"></ion-icon>
                                </ion-button>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Alert Testing Tab -->
            <div v-show="activeTab === 'alerts'">
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Test Sensor Alerts</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="12" size-md="4">
                                    <ion-item>
                                        <ion-select v-model="alertTest.sensorId" label="Sensor"
                                            placeholder="Select sensor" label-placement="stacked">
                                            <ion-select-option v-for="sensor in sensors" :key="sensor.sensor_id"
                                                :value="sensor.sensor_id">
                                                {{ sensor.sensor_id }}
                                            </ion-select-option>
                                        </ion-select>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="6" size-md="4">
                                    <ion-item>
                                        <ion-input v-model="alertTest.value" type="number" label="Test Value"
                                            label-placement="stacked"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="6" size-md="4">
                                    <ion-item>
                                        <ion-input v-model="alertTest.unit" label="Unit" placeholder="e.g., C"
                                            label-placement="stacked"></ion-input>
                                    </ion-item>
                                </ion-col>
                            </ion-row>
                        </ion-grid>

                        <ion-button @click="testSensorAlert" :disabled="!isValidAlertTest"
                            class="ion-margin-top">
                            <ion-icon :icon="warningOutline" slot="start"></ion-icon>
                            Test Alert
                        </ion-button>

                        <div v-if="alertTestResult" class="alert-result ion-margin-top">
                            <ion-card :color="alertTestResult.alert ? 'warning' : 'success'">
                                <ion-card-content>
                                    <div class="result-header">
                                        <ion-icon
                                            :icon="alertTestResult.alert ? warningOutline : checkmarkCircleOutline"></ion-icon>
                                        <h3>{{ alertTestResult.alert ? 'ALERT TRIGGERED' : 'NO ALERT' }}</h3>
                                    </div>
                                    <p><strong>Sensor:</strong> {{ alertTestResult.sensor_id }}</p>
                                    <p><strong>Value:</strong> {{ alertTestResult.value }} {{ alertTestResult.unit }}
                                    </p>
                                    <p v-if="alertTestResult.alert_type"><strong>Alert Type:</strong> {{
                                        alertTestResult.alert_type }}</p>
                                </ion-card-content>
                            </ion-card>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Alerts Display -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            System Alerts ({{ filteredAlerts.length }})
                        </ion-card-title>
                    </ion-card-header>

                    <ion-card-content>
                        <!-- Search bar -->
                        <ion-searchbar v-model="alertSearchTerm" placeholder="Search alerts..."
                            @ion-input="filterAlerts"></ion-searchbar>

                        <ion-list>
                            <ion-item v-for="alert in filteredAlerts" :key="alert.id" class="alert-item">
                                <ion-icon :icon="warningOutline" :color="alert.is_resolved ? 'success' : 'danger'"
                                    slot="start"></ion-icon>

                                <ion-label>
                                    <h2><strong>{{ alert.message }}</strong></h2>

                                    <p><strong>Sensor ID:</strong> {{ alert.sensor_id || '-' }}</p>
                                    <p><strong>Type:</strong> {{ alert.alert_type }}</p>
                                    <p><strong>Triggered Value:</strong> {{ alert.triggered_value }} {{ alert.unit }}
                                    </p>
                                    <p><strong>Limit Value:</strong> {{ alert.limit_value }} {{ alert.unit }}</p>
                                    <p><strong>Triggered at:</strong> {{ formatAlertTime(alert.triggered_at) }}</p>

                                    <p>
                                        <ion-chip :color="alert.is_resolved ? 'success' : 'danger'" size="small">
                                            {{ alert.is_resolved ? 'Resolved' : 'Not Resolved' }}
                                        </ion-chip>

                                        <ion-chip v-if="alert.resolved_at" color="primary" size="small">
                                            {{ formatAlertTime(alert.resolved_at) }}
                                        </ion-chip>
                                    </p>
                                </ion-label>

                                <!-- Action buttons -->
                                <ion-button slot="end" fill="clear" @click="viewAlertDetails(alert)">
                                    <ion-icon :icon="eyeOutline"></ion-icon>
                                </ion-button>

                                <ion-button v-if="!alert.is_resolved" slot="end" fill="clear" color="danger"
                                    @click="resolveAlert(alert)">
                                    <ion-icon :icon="checkmarkDoneOutline" size="large"></ion-icon>
                                </ion-button>
                                <ion-button v-else slot="end" fill="clear" color="success" @click="revertAlert(alert)">
                                    <ion-icon :icon="refreshOutline" size="large"></ion-icon>
                                </ion-button>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>


            </div>

            <!-- Configuration Tab -->
            <div v-show="activeTab === 'config'">
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>SS Configuration</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="config-info">
                            <p><strong>Version:</strong> {{ ssInfo?.version || 'Unknown' }}</p>
                            <p><strong>Last Loaded:</strong> {{ formatDateTime(ssInfo?.last_loaded) }}</p>
                        </div>

                        <div class="config-actions">
                            <ion-button @click="reloadSS" fill="outline">
                                <ion-icon :icon="refreshOutline" slot="start"></ion-icon>
                                Reload Configuration
                            </ion-button>
                            <ion-button @click="exportConfig" fill="outline">
                                <ion-icon :icon="downloadOutline" slot="start"></ion-icon>
                                Export Config
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Sensor Types Configuration -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Sensor Types ({{ Object.keys(sensorTypes).length }})</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="type-grid">
                            <div v-for="(typeData, typeName) in sensorTypes" :key="typeName" class="type-card">
                                <div class="type-card-header">
                                    <span class="type-name">{{ typeName.charAt(0).toUpperCase() + typeName.slice(1) }}</span>
                                </div>
                                <p class="type-desc">{{ typeData.description || 'No description' }}</p>
                                <div v-if="typeData.properties?.common_units?.length" class="type-units">
                                    <span v-for="unit in typeData.properties.common_units" :key="unit" class="unit-chip">
                                        {{ unit }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Edit Sensor Modal -->
            <ion-modal :is-open="showEditModal" @will-dismiss="showEditModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Edit Sensor: {{ editingSensor?.sensor_id }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showEditModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>

                <ion-content class="ion-padding">
                    <div v-if="editingSensor">
                        <ion-list>
                            <ion-item>
                                <ion-input v-model="editingSensor.sensor_id" label="Sensor ID"
                                    label-placement="stacked" readonly></ion-input>
                            </ion-item>

                            <ion-item>
                                <ion-select v-model="editingSensor.sensor_type" label="Sensor Type"
                                    label-placement="stacked" interface="popover">
                                    <ion-select-option v-for="type in sensorTypeOptions" :key="type" :value="type">
                                        {{ type }}
                                    </ion-select-option>
                                </ion-select>
                            </ion-item>

                            <ion-item>
                                <ion-input v-model="editingSensor.pattern" label="Topic Pattern"
                                    label-placement="stacked"></ion-input>
                            </ion-item>

                            <ion-item>
                                <ion-label>Active</ion-label>
                                <ion-toggle v-model="editingSensor.is_active" slot="end"></ion-toggle>
                            </ion-item>
                        </ion-list>

                        <!-- Edit Limits -->
                        <div class="limits-section">
                            <h4>Sensor Limits</h4>

                            <div v-for="(limit, index) in editingSensor.limits" :key="index" class="limit-edit">
                                <!-- Header: name + delete -->
                                <div class="limit-edit-header">
                                    <ion-item class="limit-name-item" lines="none">
                                        <ion-input v-model="limit.name" label="Limit Name"
                                            placeholder="e.g., normal" label-placement="stacked"></ion-input>
                                    </ion-item>
                                    <ion-button fill="clear" color="danger" size="small"
                                        @click="removeEditLimitConfig(index)">
                                        <ion-icon :icon="trashOutline"></ion-icon>
                                    </ion-button>
                                </div>
                                <!-- Values row -->
                                <ion-grid class="limit-grid">
                                    <ion-row>
                                        <ion-col size="6">
                                            <ion-item>
                                                <ion-input v-model.number="limit.upper_limit" type="number"
                                                    label="Upper" label-placement="stacked"></ion-input>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="6">
                                            <ion-item>
                                                <ion-input v-model.number="limit.lower_limit" type="number"
                                                    label="Lower" label-placement="stacked"></ion-input>
                                            </ion-item>
                                        </ion-col>
                                    </ion-row>
                                    <ion-row>
                                        <ion-col size="6">
                                            <ion-item>
                                                <ion-select v-model="limit.unit" label="Unit"
                                                    placeholder="Select" label-placement="stacked"
                                                    interface="popover">
                                                    <ion-select-option v-for="unit in getUnitOptionsWithCurrent(editingSensor.sensor_type, limit.unit)" :key="unit" :value="unit">
                                                        {{ unit }}
                                                    </ion-select-option>
                                                </ion-select>
                                            </ion-item>
                                        </ion-col>
                                        <ion-col size="6">
                                            <ion-item lines="none">
                                                <ion-label>Selected</ion-label>
                                                <ion-toggle v-model="limit.is_selected" slot="end"></ion-toggle>
                                            </ion-item>
                                        </ion-col>
                                    </ion-row>
                                </ion-grid>
                            </div>

                            <ion-button @click="addEditLimitConfig" fill="outline" size="small">
                                <ion-icon :icon="addOutline" slot="start"></ion-icon>
                                Add Limit
                            </ion-button>
                        </div>
                    </div>
                    <div v-if="updateError" class="inline-error">
                        {{ updateError }}
                    </div>

                    <ion-button @click="updateSensor" class="ion-margin-top">
                        <ion-icon :icon="saveOutline" slot="start"></ion-icon>
                        Update Sensor
                    </ion-button>
                </ion-content>
            </ion-modal>


            <!-- Sensor Details Modal -->
            <ion-modal :is-open="showSensorDetailsModal" @will-dismiss="showSensorDetailsModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Sensor Details: {{ selectedSensor?.sensor_id }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showSensorDetailsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <div v-if="selectedSensor">
                        <!-- Basic Info -->
                        <ion-card>
                            <ion-card-header>
                                <ion-card-title>Basic Information</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <p><strong>Sensor ID:</strong> {{ selectedSensor.sensor_id }}</p>
                                <p><strong>Pattern:</strong> {{ selectedSensor.pattern }}</p>
                                <p><strong>Type:</strong> {{ selectedSensor.sensor_type }}</p>
                                <p><strong>Status:</strong>
                                    <ion-chip :color="selectedSensor.is_active ? 'success' : 'danger'" size="small">
                                        {{ selectedSensor.is_active ? 'Active' : 'Inactive' }}
                                    </ion-chip>
                                </p>
                                <p><strong>Created At:</strong> {{ formatDateTime(selectedSensor.created_at) }}</p>
                                <p><strong>Updated At:</strong> {{ formatDateTime(selectedSensor.updated_at) }}</p>
                            </ion-card-content>
                        </ion-card>

                        <!-- Limits -->
                        <ion-card v-if="selectedSensor.limits && selectedSensor.limits.length">
                            <ion-card-header>
                                <ion-card-title>Limits</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <div v-for="limit in selectedSensor.limits" :key="limit.id" class="limit-item">
                                    <p>
                                        <strong>{{ limit.name.charAt(0).toUpperCase() + limit.name.slice(1) }}</strong>
                                        <span v-if="limit.is_selected"
                                            style="color: var(--ion-color-primary);">(Selected)</span>
                                    </p>
                                    <p>Upper: {{ limit.upper_limit }} {{ limit.unit }}</p>
                                    <p>Lower: {{ limit.lower_limit }} {{ limit.unit }}</p>
                                    <p>Created: {{ formatDateTime(limit.created_at) }}</p>
                                    <p>Updated: {{ formatDateTime(limit.updated_at) }}</p>
                                    <div class="card-divider"></div>

                                </div>
                            </ion-card-content>
                        </ion-card>

                        <!-- Alerts -->
                        <ion-card v-if="selectedSensor.alerts && selectedSensor.alerts.length">
                            <ion-card-header>
                                <ion-card-title>Alerts</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <div v-for="alert in selectedSensor.alerts" :key="alert.id" class="alert-item">
                                    <p><strong>Message:</strong> {{ alert.message }}</p>
                                    <p><strong>Type:</strong> {{ alert.alert_type }}</p>
                                    <p><strong>Triggered Value:</strong> {{ alert.triggered_value }} {{ alert.unit }}
                                    </p>
                                    <p><strong>Limit Value:</strong> {{ alert.limit_value }} {{ alert.unit }}</p>
                                    <p><strong>Triggered At:</strong> {{ formatDateTime(alert.triggered_at) }}</p>
                                    <p v-if="alert.is_resolved"><strong>Resolved At:</strong> {{
                                        formatDateTime(alert.resolved_at) }}</p>
                                    <p><strong>MQTT Topic:</strong> {{ alert.mqtt_topic }}</p>
                                    <p><strong>Raw Data:</strong> {{ alert.raw_data }}</p>
                                    <p>
                                        <ion-chip :color="alert.is_resolved ? 'success' : 'danger'" size="small">
                                            {{ alert.is_resolved ? 'Resolved' : 'Not Resolved' }}
                                        </ion-chip>
                                    </p>
                                    <ion-button fill="clear" size="small" class="alert-actions"
                                        @click="viewAlertDetails(alert)">
                                        <ion-icon :icon="eyeOutline"></ion-icon> View
                                    </ion-button>
                                    <ion-button v-if="!alert.is_resolved" class="alert-actions" color="success"
                                        fill="solid" @click="resolveAlert(alert)" title="Resolve this alert">
                                        <ion-icon :icon="checkmarkDoneOutline"></ion-icon>
                                        Resolve
                                    </ion-button>

                                    <ion-button v-else color="warning" class="alert-actions" fill="solid"
                                        @click="revertAlert(alert)" title="Revert this alert">
                                        <ion-icon :icon="refreshOutline"></ion-icon>
                                        Revert
                                    </ion-button>

                                    <div class="card-divider"></div>

                                </div>
                            </ion-card-content>
                        </ion-card>
                    </div>
                </ion-content>
            </ion-modal>

            <!-- Alert Details Modal -->
            <ion-modal :is-open="showAlertDetailsModal" @will-dismiss="showAlertDetailsModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Alert Details: {{ selectedAlert?.id }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showAlertDetailsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>

                <ion-content class="ion-padding">
                    <div v-if="selectedAlert">
                        <!-- Basic Alert Information -->
                        <ion-card>
                            <ion-card-header>
                                <ion-card-title>Alert Information</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <p><strong>Alert ID:</strong> {{ selectedAlert.id }}</p>
                                <p><strong>Sensor ID:</strong> {{ selectedAlert.sensor_id }}</p>
                                <p><strong>Alert Type:</strong> {{ selectedAlert.alert_type }}</p>
                                <p><strong>Message:</strong> {{ selectedAlert.message }}</p>
                                <p><strong>Triggered Value:</strong> {{ selectedAlert.triggered_value }} {{
                                    selectedAlert.unit }}</p>
                                <p><strong>Limit Value:</strong> {{ selectedAlert.limit_value }} {{ selectedAlert.unit
                                }}</p>
                                <p><strong>MQTT Topic:</strong> {{ selectedAlert.mqtt_topic }}</p>
                                <p>
                                    <strong>Status:</strong>
                                    <ion-chip :color="selectedAlert.is_resolved ? 'success' : 'danger'" size="small">
                                        {{ selectedAlert.is_resolved ? 'Resolved' : 'Not Resolved' }}
                                    </ion-chip>
                                </p>
                                <p v-if="selectedAlert.resolved_at"><strong>Resolved At:</strong> {{
                                    formatAlertTime(selectedAlert.resolved_at) }}</p>
                                <p><strong>Triggered At:</strong> {{ formatAlertTime(selectedAlert.triggered_at) }}</p>
                            </ion-card-content>
                        </ion-card>

                        <!-- Raw Data Section -->
                        <ion-card v-if="selectedAlert.raw_data">
                            <ion-card-header>
                                <ion-card-title>Raw Data</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <pre>{{ selectedAlert.raw_data }}</pre>
                            </ion-card-content>
                        </ion-card>

                        <!-- Actions -->
                        <div class="alert-actions">
                            <ion-button v-if="!selectedAlert.is_resolved" color="success" fill="solid"
                                @click="resolveAlert(selectedAlert)" title="Resolve this alert">
                                <ion-icon :icon="checkmarkDoneOutline"></ion-icon>
                                Resolve
                            </ion-button>

                            <ion-button v-else color="warning" fill="solid" @click="revertAlert(selectedAlert)"
                                title="Revert this alert">
                                <ion-icon :icon="refreshOutline"></ion-icon>
                                Revert
                            </ion-button>
                        </div>

                    </div>
                </ion-content>
            </ion-modal>

        </ion-content>

        <!-- Toast notifications -->
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
import { ref, computed, onMounted, watch } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons, IonButton,
    IonBackButton, IonIcon, IonCard, IonCardContent, IonCardHeader, IonCardTitle,
    IonGrid, IonRow, IonCol, IonItem, IonLabel, IonInput, IonSelect, IonSelectOption,
    IonChip, IonList, IonSearchbar, IonSegment, IonSegmentButton, IonModal,
    IonToggle, alertController
} from '@ionic/vue';

import {
    refreshOutline, shieldCheckmarkOutline, warningOutline, addCircleOutline,
    createOutline, eyeOutline, trashOutline, checkmarkCircleOutline,
    closeOutline, saveOutline, addOutline, downloadOutline, checkmarkDoneOutline, banOutline,
    alertCircleOutline, informationCircleOutline
} from 'ionicons/icons';

import apiService from '@/services/api';

// State
const isLoading = ref(false);
const activeTab = ref('sensors');

// Data
const ssInfo = ref(null);
const sensors = ref([]);
const sensorTypes = ref({});
const alerts = ref([]);

// Search and filtering
const sensorSearchTerm = ref('');
const filteredSensors = ref([]);

const alertSearchTerm = ref('');
const filteredAlerts = ref([]);

// Modals
const showEditModal = ref(false);
const showSensorDetailsModal = ref(false);

const showAlertDetailsModal = ref(false);

// Forms
const newSensor = ref({
    sensorId: '',
    pattern: '',
    sensorType: '',
    is_active: true,
    limits: [{
        name: '',
        upper_limit: '',
        lower_limit: '',
        unit: '',
        is_selected: true
    }
    ]
});

const editingSensor = ref(null);
const selectedSensor = ref(null);

const selectedAlert = ref(null);

const addError = ref('');
const updateError = ref('');

const alertTest = ref({
    sensorId: '',
    value: '',
    unit: ''
});

const alertTestResult = ref(null);

// Auto-generate topic pattern from sensor ID
const patternAutoFilled = ref(true);
watch(() => newSensor.value.sensorId, (id) => {
    if (patternAutoFilled.value) {
        newSensor.value.pattern = id ? `sf/sensors/${id}` : '';
    }
});
const onNewSensorIdInput = () => {
    // Allow auto-fill to run via the watch; if pattern was manually set, preserve it
};

// Computed
const activeSensors = computed(() => {
    return sensors.value.filter(s => s.is_active).length;
});

const sensorTypeOptions = computed(() => Object.keys(sensorTypes.value));

const SENSOR_UNIT_MAP = {
    temperature: ['°C', '°F', 'K'],
    humidity:    ['%', 'g/m³'],
    pressure:    ['hPa', 'Pa', 'bar', 'psi', 'atm'],
    motion:      ['count', 'm/s', 'cm/s', 'km/h', 'mph'],
    light:       ['lux', 'cd/m²'],
    sound:       ['dB', 'dBA'],
    gas:         ['ppm', 'ppb', '%'],
    power:       ['V', 'mV', 'A', 'mA', 'W', 'kW'],
    distance:    ['m', 'cm', 'mm', 'in', 'ft'],
    speed:       ['m/s', 'km/h', 'mph'],
};
const COMMON_UNITS = ['°C', '°F', '%', 'hPa', 'Pa', 'm/s', 'km/h', 'lux', 'dB', 'ppm', 'V', 'A', 'W', 'm', 'cm', 'boolean'];

const getUnitOptions = (sensorType) => {
    if (!sensorType) return COMMON_UNITS;
    return SENSOR_UNIT_MAP[sensorType.toLowerCase()] || COMMON_UNITS;
};

// Always include the already-saved unit value so it's visible even if it predates the dropdown
const getUnitOptionsWithCurrent = (sensorType, currentUnit) => {
    const options = getUnitOptions(sensorType);
    if (currentUnit && !options.includes(currentUnit)) {
        return [currentUnit, ...options];
    }
    return options;
};

const activeAlerts = computed(() => {
    if (!alerts.value) return [];

    return alerts.value.filter(alert => alert.is_resolved == false);
});

const activeAlertCount = computed(() => {
    return activeAlerts.value.length;
});

const isValidNewSensor = computed(() => {
    return newSensor.value.sensorId.trim() &&
        newSensor.value.pattern.trim() &&
        newSensor.value.sensorType.trim();
});

const isValidAlertTest = computed(() => {
    return alertTest.value.sensorId &&
        alertTest.value.value !== '' &&
        alertTest.value.unit.trim();
});

const addSelectedLimitsCount = computed(() => {
    if (newSensor.value && Array.isArray(newSensor.value.limits)) {
        return newSensor.value.limits.filter(limit => limit.is_selected).length;
    }
    return 0;
});

const editSelectedLimitsCount = computed(() => {
    if (editingSensor.value && Array.isArray(editingSensor.value.limits)) {
        return editingSensor.value.limits.filter(limit => limit.is_selected).length;
    }
    return 0;
});

watch(editSelectedLimitsCount, (newCount) => {
    if (newCount <= 1) {
        updateError.value = ''; // clear error automatically
    }
});

watch(addSelectedLimitsCount, (newCount) => {
    if (newCount <= 1) {
        addError.value = ''; // clear error automatically
    }
});

// Methods
const toasts = ref([]);
const removeToast = (id) => { toasts.value = toasts.value.filter(t => t.id !== id); };
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

// Data loading methods
const loadSSInfo = async () => {
    try {
        const response = await apiService.getSSInfo();
        ssInfo.value = response.data;
    } catch (err) {
        console.error('Failed to load SS info:', err);
        showToast('Failed to load SS info', 'danger');
    }
};

const loadSensors = async () => {
    try {
        const response = await apiService.getAllSensors(false);
        sensors.value = response.data || [];
        filteredSensors.value = sensors.value;
    } catch (err) {
        console.error('Failed to load sensors:', err);
        showToast('Failed to load sensors', 'danger');
    }
};

const loadSensorTypes = async () => {
    try {
        const response = await apiService.getAllTypes();
        sensorTypes.value = response.data || {};
    } catch (err) {
        console.error('Failed to load types:', err);
        showToast('Failed to load types', 'danger');
    }
};

const loadAlerts = async () => {
    try {
        const response = await apiService.getAlerts();
        alerts.value = response.data || [];
    } catch (err) {
        console.error('Failed to load alerts:', err);
        showToast('Failed to load alerts', 'danger');
    }
};

const refreshData = async () => {
    isLoading.value = true;
    try {
        await Promise.all([
            loadSSInfo(),
            loadSensors(),
            loadSensorTypes(),
            loadAlerts()
        ]);
        showToast('Data refreshed', 'success');
    } catch (err) {
        showToast('Failed to refresh data', 'danger');
    } finally {
        isLoading.value = false;
    }
};

// Sensor management methods
const createSensor = async () => {
    try {
        if (addSelectedLimitsCount.value > 1) {
            addError.value = 'You cannot select more than 1 limit.';
            return;
        }
        const limitsArray = newSensor.value.limits.map(limit => ({
            name: limit.name,
            upper_limit: Number(limit.upper_limit),
            lower_limit: Number(limit.lower_limit),
            unit: limit.unit,
            is_selected: limit.is_selected
        }));

        const payload = {
            sensor_id: newSensor.value.sensorId,
            pattern: newSensor.value.pattern,
            sensor_type: newSensor.value.sensorType,
            is_active: newSensor.value.is_active,
            limits: limitsArray
        };
        await apiService.addSensor(
            payload
        );

        // Reset form
        newSensor.value = {
            sensorId: '',
            pattern: '',
            sensorType: '',
            is_active: true,
            limits: [{
                name: '',
                upper_limit: '',
                lower_limit: '',
                unit: '',
                is_selected: true
            }]
        };
        patternAutoFilled.value = true;

        await loadSensors();
        await loadSSInfo();
        showToast('Sensor created successfully', 'success');
    } catch (err) {
        showToast('Failed to create sensor', 'danger');
    }
};

const editSensor = (sensor) => {
    // Deep-clone limits so edits don't mutate the sensors list
    const limits = (sensor.limits && sensor.limits.length)
        ? sensor.limits.map(l => ({
            ...l,
            name: l.name || 'default',
            unit: l.unit ?? '',
            upper_limit: l.upper_limit ?? '',
            lower_limit: l.lower_limit ?? '',
        }))
        : [{ name: '', upper_limit: '', lower_limit: '', unit: '', is_selected: true }];

    editingSensor.value = { ...sensor, limits };
    showEditModal.value = true;
};

const updateSensor = async () => {
    try {
        if (editSelectedLimitsCount.value > 1) {
            updateError.value = 'You cannot select more than 1 limit.';
            return; // stop the update
        }

        const cleanPayload = JSON.parse(JSON.stringify({
            pattern: editingSensor.value.pattern || '',
            sensor_type: editingSensor.value.sensor_type || '',
            is_active: editingSensor.value.is_active,
            limits: editingSensor.value.limits || []
        }));

        await apiService.updateSensor(editingSensor.value.sensor_id, cleanPayload);

        showEditModal.value = false;
        editingSensor.value = null;
        await loadSensors();
        showToast('Sensor updated successfully', 'success');
    } catch (err) {
        showToast('Failed to update sensor', 'danger');
    }
};

const deleteSensor = async (sensorId) => {
    const alert = await alertController.create({
        header: 'Delete Sensor',
        message: `Delete "${sensorId}"? This cannot be undone.`,
        buttons: [
            { text: 'Cancel', role: 'cancel' },
            { text: 'Delete', role: 'destructive' },
        ]
    });
    await alert.present();

    const { role } = await alert.onDidDismiss();
    if (role !== 'destructive') return;

    try {
        await apiService.deleteSensor(sensorId);
        await loadSensors();
        await loadSSInfo();
        showToast('Sensor deleted successfully', 'success');
    } catch (err) {
        showToast('Failed to delete sensor', 'danger');
    }
};

const viewSensorDetails = (sensor) => {
    selectedSensor.value = sensor;
    showSensorDetailsModal.value = true;
};

const viewAlertDetails = (alert) => {
    selectedAlert.value = alert;
    showAlertDetailsModal.value = true;
};

// Alert testing methods
const testSensorAlert = async () => {
    try {
        const response = await apiService.checkAlert(
            {
                sensor_id: alertTest.value.sensorId,
                value: alertTest.value.value,
                unit: alertTest.value.unit
            }
        );
        alertTestResult.value = response.data;
        loadAlerts();
    } catch (err) {
        showToast('Failed to test alert', 'danger');
    }
};

// Limit configuration methods
const addLimitConfig = () => {
    newSensor.value.limits.push({
        name: `config_${newSensor.value.limits.length + 1}`,
        upper_limit: '',
        lower_limit: '',
        unit: '',
        is_selected: false
    });
};

const removeLimitConfig = (index) => {
    if (newSensor.value.limits.length > 1) {
        newSensor.value.limits.splice(index, 1);
    }
};

const addEditLimitConfig = () => {
    if (editingSensor.value) {
        editingSensor.value.limits[(editingSensor.value.limits).length] = {
            name: '',
            upper_limit: '',
            lower_limit: '',
            unit: '',
            is_selected: false
        };
    }
};

const removeEditLimitConfig = (index) => {
    if (editingSensor.value && (editingSensor.value.limits).length > 1) {
        editingSensor.value.limits.splice(index, 1);
    }
};

// Utility methods
const filterAlerts = () => {
    const term = alertSearchTerm.value.toLowerCase();
    filteredAlerts.value = alerts.value.filter(alert =>
        (alert.message && alert.message.toLowerCase().includes(term)) ||
        (alert.sensor_id && alert.sensor_id.toLowerCase().includes(term)) ||
        (alert.alert_type && alert.alert_type.toLowerCase().includes(term))
    );
};

watch(alerts, () => filterAlerts(), { immediate: true });

const formatAlertTime = (timestamp) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString();
};

const resolveAlert = async (alert) => {
    try {
        if (alert.is_resolved) return;
        const response = await apiService.resolveAlert(alert.id);
        if (response.data) {
            // Update alert details modal ref
            if (selectedAlert.value?.id === alert.id) {
                selectedAlert.value = { ...selectedAlert.value, is_resolved: true, resolved_at: new Date().toISOString() };
            }
            // Update sensor details modal alerts list
            if (selectedSensor.value?.alerts) {
                const idx = selectedSensor.value.alerts.findIndex(a => a.id === alert.id);
                if (idx >= 0) {
                    selectedSensor.value.alerts[idx] = {
                        ...selectedSensor.value.alerts[idx],
                        is_resolved: true,
                        resolved_at: new Date().toISOString()
                    };
                }
            }
            loadSensors();
            loadAlerts();
            showToast('Alert resolved', 'success');
        }
    } catch (err) {
        showToast('Failed to resolve alert', 'danger');
    }
};

const revertAlert = async (alert) => {
    try {
        if (!alert.is_resolved) return;
        const response = await apiService.revertAlert(alert.id);
        if (response.data) {
            // Update alert details modal ref
            if (selectedAlert.value?.id === alert.id) {
                selectedAlert.value = { ...selectedAlert.value, is_resolved: false, resolved_at: null };
            }
            // Update sensor details modal alerts list
            if (selectedSensor.value?.alerts) {
                const idx = selectedSensor.value.alerts.findIndex(a => a.id === alert.id);
                if (idx >= 0) {
                    selectedSensor.value.alerts[idx] = {
                        ...selectedSensor.value.alerts[idx],
                        is_resolved: false,
                        resolved_at: null
                    };
                }
            }
            loadSensors();
            loadAlerts();
            showToast('Alert reverted', 'success');
        }
    } catch (err) {
        showToast('Failed to revert alert', 'danger');
    }
};

const filterSensors = () => {
    const term = sensorSearchTerm.value.toLowerCase();
    if (term) {
        filteredSensors.value = sensors.value.filter(sensor =>
            sensor.sensor_id.toLowerCase().includes(term) ||
            sensor.sensor_type.toLowerCase().includes(term) ||
            sensor.pattern.toLowerCase().includes(term)
        );
    } else {
        filteredSensors.value = sensors.value;
    }
};

const onSegmentChange = (event) => {
    activeTab.value = event.detail.value;
    alertTestResult.value = null; // Reset alert test result when switching tabs
};

const reloadSS = async () => {
    try {
        await apiService.reloadSS();
        await refreshData();
        showToast('SS configuration reloaded', 'success');
    } catch (err) {
        showToast('Failed to reload SS', 'danger');
    }
};

const exportConfig = () => {
    // Create a simplified export of the current configuration
    const config = {
        sensors: sensors.value,
        info: ssInfo.value,
        timestamp: new Date().toISOString()
    };

    const dataStr = JSON.stringify(config, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

    const exportFileDefaultName = `ss_config_export_${new Date().toISOString().split('T')[0]}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();

    showToast('Configuration exported', 'success');
};

const formatDateTime = (timestamp) => {
    return timestamp ? new Date(timestamp).toLocaleString() : 'Unknown';
};

// Lifecycle
onMounted(() => {
    refreshData();
});
</script>

<style scoped>
/* stat-item, inline-error, card-divider, action-row are in global.css */

.alert-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.alert-item h2 {
  font-size: 14px;
  margin: 0 0 4px;
  line-height: 1.3;
}

.alert-item p {
  margin: 2px 0;
  font-size: 13px;
  color: var(--ion-color-medium);
}

.limit-name {
  margin-right: 4px;
}

.limits-section {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--ion-color-light);
  border-radius: 10px;
}

.limits-section h4 {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--ion-color-medium);
}

.limit-edit {
  margin-bottom: 10px;
  padding: 8px 12px 12px;
  background: white;
  border-radius: 8px;
}

.limit-edit-header {
  display: flex;
  align-items: flex-end;
  gap: 4px;
}

.limit-name-item {
  flex: 1;
  --padding-start: 0;
  --inner-padding-end: 0;
}

.limit-grid {
  padding: 0;
}

.alert-result .result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.alert-result h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.config-info {
  background: var(--ion-color-light);
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 16px;
}

.config-info p {
  margin: 6px 0;
  font-family: monospace;
  font-size: 13px;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.type-card {
  background: var(--ion-color-light);
  border-radius: 10px;
  padding: 12px 14px;
}

.type-card-header {
  margin-bottom: 6px;
}

.type-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ion-color-dark);
}

.type-desc {
  font-size: 12px;
  color: var(--ion-color-medium);
  margin: 0 0 8px;
  line-height: 1.4;
}

.type-units {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.unit-chip {
  font-size: 11px;
  background: var(--ion-color-primary);
  color: #ffffff;
  border-radius: 4px;
  padding: 2px 6px;
  font-weight: 500;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-segment {
  margin: 10px 16px 0;
}

.form-grid {
  padding: 0;
}

.toggle-col {
  display: flex;
  align-items: center;
}

.del-col {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Toast notifications ──────────────────────────────────── */
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
  box-shadow: 0 4px 28px rgba(0,0,0,0.30), 0 1px 6px rgba(0,0,0,0.18);
  pointer-events: all;
  width: 100%;
  box-sizing: border-box;
}
.toast-primary { --toast-accent: #6eb4ff; --toast-glow: rgba(110,180,255,0.20); }
.toast-success { --toast-accent: #4cd964; --toast-glow: rgba(76,217,100,0.20); }
.toast-warning { --toast-accent: #ffd60a; --toast-glow: rgba(255,214,10,0.20); }
.toast-danger  { --toast-accent: #ff453a; --toast-glow: rgba(255,69,58,0.20); }
.toast-icon-wrap {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--toast-glow);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.toast-icon { font-size: 16px; color: var(--toast-accent); }
.toast-message {
  flex: 1; font-size: 13.5px; font-weight: 500;
  color: rgba(255,255,255,0.95); line-height: 1.35;
}
.toast-close {
  background: none; border: none; padding: 4px; margin: 0; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: rgba(255,255,255,0.40); font-size: 16px; flex-shrink: 0;
  border-radius: 50%; transition: color 0.15s;
}
.toast-close:hover { color: rgba(255,255,255,0.75); }
.toast-enter-active { animation: toast-in 0.32s cubic-bezier(0.34,1.56,0.64,1) both; }
.toast-leave-active { animation: toast-out 0.2s ease both; position: absolute; width: 100%; }
@keyframes toast-in  { from { opacity:0; transform: translateY(20px) scale(0.94); } to { opacity:1; transform: translateY(0) scale(1); } }
@keyframes toast-out { from { opacity:1; transform: scale(1); } to { opacity:0; transform: scale(0.92); } }
</style>