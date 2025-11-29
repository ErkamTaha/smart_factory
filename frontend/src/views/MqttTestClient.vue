<template>
    <ion-page>
        <ion-header>
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button default-href="/"></ion-back-button>
                </ion-buttons>
                <ion-title>MQTT Test & Management</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="activeTab = 'mqtt'" :class="{ 'active-tab': activeTab === 'mqtt' }">
                        MQTT
                    </ion-button>
                    <ion-button @click="activeTab = 'acl'" :class="{ 'active-tab': activeTab === 'acl' }">
                        ACL
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content :fullscreen="true" class="ion-padding">
            <!-- MQTT Test Tab -->
            <div v-if="activeTab === 'mqtt'">
                <!-- Connection Status Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            <ion-chip :color="statusColor">
                                <ion-label>{{ connectionStatus }}</ion-label>
                            </ion-chip>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-label position="stacked">User ID</ion-label>
                                        <ion-input v-model="userId" placeholder="alice, bob, charlie..."
                                            :disabled="isConnected"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-label position="stacked">WebSocket URL</ion-label>
                                        <ion-input v-model="wsUrl" placeholder="ws://localhost:8000/ws/ws"
                                            :disabled="isConnected"></ion-input>
                                    </ion-item>
                                </ion-col>
                            </ion-row>
                            <ion-row>
                                <ion-col size="6">
                                    <ion-button expand="block" @click="connect" :disabled="isConnected">
                                        <ion-icon :icon="powerOutline" slot="start"></ion-icon>
                                        Connect
                                    </ion-button>
                                </ion-col>
                                <ion-col size="6">
                                    <ion-button expand="block" color="danger" @click="disconnect"
                                        :disabled="!isConnected">
                                        <ion-icon :icon="closeCircleOutline" slot="start"></ion-icon>
                                        Disconnect
                                    </ion-button>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                    </ion-card-content>
                </ion-card>

                <!-- Subscribe & Publish Grid -->
                <ion-grid>
                    <ion-row>
                        <!-- Subscribe Section -->
                        <ion-col size="12" size-lg="6">
                            <ion-card>
                                <ion-card-header>
                                    <ion-card-title>ðŸ“¥ Subscribe</ion-card-title>
                                </ion-card-header>
                                <ion-card-content>
                                    <ion-item>
                                        <ion-label position="stacked">Topic</ion-label>
                                        <ion-input v-model="subscribeTopic" placeholder="sf/sensors/#"></ion-input>
                                    </ion-item>

                                    <ion-item>
                                        <ion-label position="stacked">QoS Level</ion-label>
                                        <ion-select v-model="subscribeQos" interface="popover">
                                            <ion-select-option :value="0">QoS 0</ion-select-option>
                                            <ion-select-option :value="1">QoS 1</ion-select-option>
                                            <ion-select-option :value="2">QoS 2</ion-select-option>
                                        </ion-select>
                                    </ion-item>

                                    <ion-button expand="block" @click="subscribe" :disabled="!isConnected"
                                        class="ion-margin-top">
                                        <ion-icon :icon="addCircleOutline" slot="start"></ion-icon>
                                        Subscribe
                                    </ion-button>

                                    <!-- Active Subscriptions -->
                                    <div v-if="subscribedTopics.length > 0" class="ion-margin-top">
                                        <ion-label class="subscriptions-label">Active Subscriptions:</ion-label>
                                        <ion-chip v-for="topic in subscribedTopics" :key="topic" color="primary">
                                            <ion-label>{{ topic }}</ion-label>
                                            <ion-icon :icon="closeCircleOutline" @click="unsubscribe(topic)"></ion-icon>
                                        </ion-chip>
                                    </div>
                                </ion-card-content>
                            </ion-card>
                        </ion-col>

                        <!-- Publish Section -->
                        <ion-col size="12" size-lg="6">
                            <ion-card>
                                <ion-card-header>
                                    <ion-card-title>ðŸ“¤ Publish</ion-card-title>
                                </ion-card-header>
                                <ion-card-content>
                                    <ion-item>
                                        <ion-label position="stacked">Topic</ion-label>
                                        <ion-input v-model="publishTopic"
                                            placeholder="sf/sensors/temperature"></ion-input>
                                    </ion-item>

                                    <ion-item>
                                        <ion-label position="stacked">Payload (JSON)</ion-label>
                                        <ion-textarea v-model="publishPayload" :rows="3"
                                            placeholder='{"value": 25.5}'></ion-textarea>
                                    </ion-item>

                                    <ion-grid class="ion-no-padding">
                                        <ion-row>
                                            <ion-col size="8">
                                                <ion-item>
                                                    <ion-label position="stacked">QoS</ion-label>
                                                    <ion-select v-model="publishQos" interface="popover">
                                                        <ion-select-option :value="0">QoS 0</ion-select-option>
                                                        <ion-select-option :value="1">QoS 1</ion-select-option>
                                                        <ion-select-option :value="2">QoS 2</ion-select-option>
                                                    </ion-select>
                                                </ion-item>
                                            </ion-col>
                                            <ion-col size="4">
                                                <ion-item lines="none">
                                                    <ion-label position="stacked">Retain</ion-label>
                                                    <ion-toggle v-model="publishRetain"
                                                        class="ion-margin-top"></ion-toggle>
                                                </ion-item>
                                            </ion-col>
                                        </ion-row>
                                    </ion-grid>

                                    <ion-button expand="block" @click="publish" :disabled="!isConnected"
                                        class="ion-margin-top">
                                        <ion-icon :icon="sendOutline" slot="start"></ion-icon>
                                        Publish
                                    </ion-button>
                                </ion-card-content>
                            </ion-card>
                        </ion-col>
                    </ion-row>
                </ion-grid>

                <!-- Quick Actions -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>âš¡ Quick Actions</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="6" size-md="3">
                                    <ion-button expand="block" fill="outline" @click="subscribeToUserStatuses"
                                        :disabled="!isConnected">
                                        User Statuses
                                    </ion-button>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <ion-button expand="block" fill="outline" @click="subscribeToSensors"
                                        :disabled="!isConnected">
                                        All Sensors
                                    </ion-button>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <ion-button expand="block" fill="outline" @click="subscribeToBackendStatus"
                                        :disabled="!isConnected">
                                        Backend Status
                                    </ion-button>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <ion-button expand="block" fill="outline" @click="publishTestSensorData"
                                        :disabled="!isConnected">
                                        Test Publish
                                    </ion-button>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                    </ion-card-content>
                </ion-card>

                <!-- Messages Log -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            ðŸ’¬ Messages ({{ messages.length }})
                            <ion-button size="small" fill="clear" @click="clearMessages" class="ion-float-right">
                                <ion-icon :icon="trashOutline"></ion-icon>
                            </ion-button>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <div class="messages-container">
                            <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.type]">
                                <div class="message-header">
                                    <span class="timestamp">{{ msg.timestamp }}</span>
                                    <ion-row>
                                        <ion-chip v-if="msg.qos !== undefined" size="small" color="secondary">
                                            QoS {{ msg.qos }}
                                        </ion-chip>
                                        <ion-chip v-if="msg.retain == true" size="small" color="secondary">
                                            Retained
                                        </ion-chip>
                                    </ion-row>
                                </div>
                                <div v-if="msg.topic" class="topic">{{ msg.topic }}</div>
                                <div class="payload">{{ msg.payload }}</div>
                            </div>
                            <div v-if="messages.length === 0" class="no-messages">
                                <ion-icon :icon="chatbubbleEllipsesOutline" size="large"></ion-icon>
                                <p>No messages yet. Connect and subscribe to see messages.</p>
                            </div>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- ACL Management Tab -->
            <div v-if="activeTab === 'acl'">
                <!-- ACL Info Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            ðŸ”’ ACL Information
                            <ion-button size="small" fill="clear" @click="loadAclInfo" class="ion-float-right">
                                <ion-icon :icon="refreshOutline"></ion-icon>
                            </ion-button>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid v-if="aclInfo">
                            <ion-row>
                                <ion-col size="6" size-md="3">
                                    <div class="stat-card">
                                        <div class="stat-value">{{ aclInfo.total_users }}</div>
                                        <div class="stat-label">Total Users</div>
                                    </div>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <div class="stat-card">
                                        <div class="stat-value">{{ aclInfo.total_roles }}</div>
                                        <div class="stat-label">Total Roles</div>
                                    </div>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <div class="stat-card">
                                        <div class="stat-value">{{ aclInfo.default_policy }}</div>
                                        <div class="stat-label">Default Policy</div>
                                    </div>
                                </ion-col>
                                <ion-col size="6" size-md="3">
                                    <div class="stat-card">
                                        <div class="stat-value">{{ aclInfo.version }}</div>
                                        <div class="stat-label">Version</div>
                                    </div>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                    </ion-card-content>
                </ion-card>

                <!-- Create User Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>âž• Create New User</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-item>
                            <ion-label position="stacked">User ID</ion-label>
                            <ion-input v-model="newUser.userId" placeholder="john_doe"></ion-input>
                        </ion-item>

                        <ion-item>
                            <ion-label position="stacked">Roles</ion-label>
                            <ion-select v-model="newUser.roles" multiple placeholder="Select roles">
                                <ion-select-option v-for="role in availableRoles" :key="role" :value="role">
                                    {{ role }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>

                        <ion-button expand="block" @click="createUser" class="ion-margin-top">
                            <ion-icon :icon="personAddOutline" slot="start"></ion-icon>
                            Create User
                        </ion-button>
                    </ion-card-content>
                </ion-card>

                <!-- Available Roles Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>ðŸ‘¥ Available Roles</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item v-for="(roleData, roleName) in rolesData" :key="roleName">
                                <ion-label>
                                    <h2>{{ roleName }}</h2>
                                    <p>{{ roleData.description }}</p>
                                    <ion-chip v-for="(perm, idx) in roleData.permissions" :key="idx" color="tertiary"
                                        size="small">
                                        {{ perm.pattern }}: {{ perm.allow.join(', ') }}
                                    </ion-chip>
                                </ion-label>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>

                <!-- Users List Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>
                            ðŸ‘¤ Users ({{ usersList.length }})
                            <ion-button size="small" fill="clear" @click="loadUsers" class="ion-float-right">
                                <ion-icon :icon="refreshOutline"></ion-icon>
                            </ion-button>
                        </ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item v-for="user in usersList" :key="user.user_id">
                                <ion-label>
                                    <h2>{{ user.user_id }}</h2>
                                    <p>
                                        <ion-chip v-for="role in user.roles" :key="role" color="primary" size="small">
                                            {{ role }}
                                        </ion-chip>
                                    </p>
                                </ion-label>
                                <ion-button slot="end" fill="clear" @click="showUserDetails(user)">
                                    <ion-icon :icon="informationCircleOutline"></ion-icon>
                                </ion-button>
                                <ion-button slot="end" fill="clear" color="danger" @click="deleteUser(user.user_id)">
                                    <ion-icon :icon="trashOutline"></ion-icon>
                                </ion-button>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>

                <!-- Permission Checker Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>ðŸ” Check Permissions</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-item>
                            <ion-label position="stacked">User ID</ion-label>
                            <ion-input v-model="permCheck.userId" placeholder="alice"></ion-input>
                        </ion-item>

                        <ion-item>
                            <ion-label position="stacked">Topic</ion-label>
                            <ion-input v-model="permCheck.topic" placeholder="sf/sensors/temperature"></ion-input>
                        </ion-item>

                        <ion-item>
                            <ion-label position="stacked">Action</ion-label>
                            <ion-select v-model="permCheck.action">
                                <ion-select-option value="subscribe">Subscribe</ion-select-option>
                                <ion-select-option value="publish">Publish</ion-select-option>
                            </ion-select>
                        </ion-item>

                        <ion-button expand="block" @click="checkPermission" class="ion-margin-top">
                            <ion-icon :icon="checkmarkCircleOutline" slot="start"></ion-icon>
                            Check Permission
                        </ion-button>

                        <div v-if="permCheckResult" class="ion-margin-top">
                            <ion-chip :color="permCheckResult.allowed ? 'success' : 'danger'">
                                <ion-icon
                                    :icon="permCheckResult.allowed ? checkmarkCircleOutline : closeCircleOutline"></ion-icon>
                                <ion-label>{{ permCheckResult.allowed ? 'ALLOWED' : 'DENIED' }}</ion-label>
                            </ion-chip>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
    IonPage,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonCard,
    IonCardHeader,
    IonCardTitle,
    IonCardContent,
    IonItem,
    IonLabel,
    IonInput,
    IonTextarea,
    IonButton,
    IonChip,
    IonSelect,
    IonSelectOption,
    IonToggle,
    IonList,
    IonButtons,
    IonBackButton,
    IonGrid,
    IonRow,
    IonCol,
    IonIcon,
    alertController,
    toastController,
} from '@ionic/vue';
import {
    powerOutline,
    closeCircleOutline,
    addCircleOutline,
    sendOutline,
    trashOutline,
    chatbubbleEllipsesOutline,
    refreshOutline,
    personAddOutline,
    informationCircleOutline,
    checkmarkCircleOutline,
} from 'ionicons/icons';
import webSocketService from '@/services/websocket';

// State
const activeTab = ref('mqtt');
const userId = ref('alice');
const wsUrl = ref('ws://localhost:8000/ws/ws');
const isConnected = ref(false);
const connectionStatus = ref('Disconnected');

// Subscribe state
const subscribeTopic = ref('sf/sensors/#');
const subscribeQos = ref(1);
const subscribedTopics = ref([]);

// Publish state
const publishTopic = ref('sf/sensors/temperature');
const publishPayload = ref('{\n  "value": 25.5,\n  "unit": "C"\n}');
const publishQos = ref(1);
const publishRetain = ref(false);

// Messages
const messages = ref([]);

// ACL State
const aclInfo = ref(null);
const usersList = ref([]);
const rolesData = ref({});
const availableRoles = ref([]);

const newUser = ref({
    userId: '',
    roles: [],
});

const permCheck = ref({
    userId: '',
    topic: '',
    action: 'subscribe',
});

const permCheckResult = ref(null);

// API Base URL
const API_BASE = 'http://localhost:8000';

// Computed
const statusColor = computed(() => {
    if (isConnected.value) return 'success';
    if (connectionStatus.value === 'Connecting...') return 'warning';
    return 'danger';
});

// Methods
const addMessage = (type, content) => {
    const msg = {
        timestamp: new Date().toLocaleTimeString(),
        type,
        payload: content.payload || content.topic || '',
        ...content,
    };
    messages.value.push(msg);

    if (messages.value.length > 100) {
        messages.value.shift();
    }
};

const showToast = async (message, color = 'primary') => {
    const toast = await toastController.create({
        message,
        duration: 2000,
        color,
        position: 'bottom',
    });
    await toast.present();
};

// WebSocket event handlers
const handleConnectionStatus = (data) => {
    if (data.status === 'connected') {
        isConnected.value = true;
        connectionStatus.value = 'Connected';
        addMessage('system', { payload: `âœ“ Connected as ${data.user_id}` });
        showToast('Connected successfully', 'success');
    } else if (data.status === 'disconnected') {
        isConnected.value = false;
        connectionStatus.value = 'Disconnected';
        subscribedTopics.value = [];
        addMessage('system', { payload: 'âœ— Disconnected from WebSocket' });
        showToast('Disconnected', 'warning');
    } else if (data.status === 'error') {
        isConnected.value = false;
        connectionStatus.value = 'Error';
        addMessage('error', { payload: 'WebSocket error occurred' });
        showToast('Connection error', 'danger');
    }
};

const handleSensorData = (data) => {
    addMessage('received', {
        topic: data.topic,
        qos: data.qos,
        retain: data.retain,
        payload: JSON.stringify(data.data, null, 2),
    });
};

const handleMqttStatus = (data) => {
    addMessage('system', {
        payload: `MQTT Status: ${data.status} - ${data.message}`,
    });
};

const handleSystemAlert = (data) => {
    addMessage('system alert', {
        payload: `System alert: ${data.message}`,
    });
};

const handlePublishAck = (data) => {
    addMessage(data.status === 'success' ? 'sent' : 'error', {
        topic: data.topic,
        qos: data.qos,
        payload: `Publish ${data.status}`,
    });
};

const handleSubscriptionAck = (data) => {
    subscribedTopics.value = data.current_subscriptions || [];
    addMessage('system', {
        payload: `Subscribed to: ${data.topics?.join(', ')}`,
    });
};

const handleUnsubscriptionAck = (data) => {
    subscribedTopics.value = data.current_subscriptions || [];
    addMessage('system', {
        payload: `Unsubscribed from: ${data.topics?.join(', ')}`,
    });
};

const handlePermissionRevoked = (data) => {
    addMessage('error', {
        topic: data.topic,
        payload: `Permission revoked: ${data.message}`,
    });
    showToast(`Permission revoked for ${data.topic}`, 'danger');
};

// WebSocket connection methods
const connect = async () => {
    if (!userId.value.trim()) {
        showToast('Please enter a User ID', 'danger');
        return;
    }

    connectionStatus.value = 'Connecting...';
    addMessage('system', { payload: `Connecting as user: ${userId.value}` });

    try {
        await webSocketService.connect(wsUrl.value, userId.value);
    } catch (error) {
        connectionStatus.value = 'Error';
        addMessage('error', { payload: 'Failed to connect' });
        showToast('Failed to connect', 'danger');
    }
};

const disconnect = () => {
    webSocketService.disconnect();
};

// MQTT operations
const subscribe = () => {
    if (!subscribeTopic.value.trim()) {
        showToast('Please enter a topic', 'danger');
        return;
    }

    webSocketService.subscribeMQTT(subscribeTopic.value, subscribeQos.value);
    addMessage('system', {
        payload: `Subscribing to: ${subscribeTopic.value} (QoS ${subscribeQos.value})`,
    });
};

const unsubscribe = (topic) => {
    webSocketService.unsubscribeMQTT(topic);
    addMessage('system', {
        payload: `Unsubscribing from: ${topic}`,
    });
};

const publish = async () => {
    if (!publishTopic.value.trim() || !publishPayload.value.trim()) {
        showToast('Please enter topic and payload', 'danger');
        return;
    }

    try {
        JSON.parse(publishPayload.value);
    } catch {
        const alert = await alertController.create({
            header: 'Invalid JSON',
            message: 'Payload is not valid JSON. Send anyway?',
            buttons: [
                { text: 'Cancel', role: 'cancel' },
                { text: 'Send', handler: () => performPublish() },
            ],
        });
        await alert.present();
        return;
    }

    performPublish();
};

const performPublish = () => {
    webSocketService.publishMQTT(
        publishTopic.value,
        publishPayload.value,
        publishQos.value,
        publishRetain.value
    );
    addMessage('sent', {
        topic: publishTopic.value,
        qos: publishQos.value,
        payload: publishPayload.value,
    });
};

// Quick Actions
const subscribeToUserStatuses = () => {
    subscribeTopic.value = 'sf/+/+/status';
    subscribeQos.value = 1;
    subscribe();
};

const subscribeToSensors = () => {
    subscribeTopic.value = 'sf/sensors/#';
    subscribeQos.value = 1;
    subscribe();
};

const subscribeToBackendStatus = () => {
    subscribeTopic.value = 'sf/backend/status';
    subscribeQos.value = 1;
    subscribe();
};

const publishTestSensorData = () => {
    const testData = {
        device_id: 'test_device_001',
        sensor_type: 'temperature',
        value: Math.floor(Math.random() * 100),
        unit: 'C',
        timestamp: new Date().toISOString(),
    };

    publishTopic.value = 'sf/sensors/test_device_001/temperature';
    publishPayload.value = JSON.stringify(testData, null, 2);
    publishQos.value = 1;
    performPublish();
};

const clearMessages = () => {
    messages.value = [];
    addMessage('system', { payload: 'Messages cleared' });
};

// ACL Methods
const loadAclInfo = async () => {
    try {
        const response = await fetch(`${API_BASE}/api/acl/info`);
        aclInfo.value = await response.json();
        showToast('ACL info loaded', 'success');
    } catch (error) {
        showToast('Failed to load ACL info', 'danger');
    }
};

const loadRoles = async () => {
    try {
        const response = await fetch(`${API_BASE}/api/acl/roles`);
        const data = await response.json();
        rolesData.value = data.roles;
        availableRoles.value = Object.keys(data.roles);
    } catch (error) {
        showToast('Failed to load roles', 'danger');
    }
};

const loadUsers = async () => {
    try {
        const response = await fetch(`${API_BASE}/api/acl/users`);
        const data = await response.json();
        usersList.value = data.users;
    } catch (error) {
        showToast('Failed to load users', 'danger');
    }
};

const createUser = async () => {
    if (!newUser.value.userId || newUser.value.roles.length === 0) {
        showToast('Please enter user ID and select at least one role', 'danger');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/acl/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: newUser.value.userId,
                roles: newUser.value.roles,
                custom_permissions: [],
            }),
        });

        if (response.ok) {
            showToast(`User ${newUser.value.userId} created successfully`, 'success');
            newUser.value = { userId: '', roles: [] };
            loadUsers();
            loadAclInfo();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to create user', 'danger');
        }
    } catch (error) {
        showToast('Failed to create user', 'danger');
    }
};

const deleteUser = async (userId) => {
    const alert = await alertController.create({
        header: 'Delete User',
        message: `Are you sure you want to delete user "${userId}"?`,
        buttons: [
            { text: 'Cancel', role: 'cancel' },
            {
                text: 'Delete',
                role: 'destructive',
                handler: async () => {
                    try {
                        const response = await fetch(`${API_BASE}/api/acl/users/${userId}`, {
                            method: 'DELETE',
                        });

                        if (response.ok) {
                            showToast(`User ${userId} deleted`, 'success');
                            loadUsers();
                            loadAclInfo();
                        } else {
                            showToast('Failed to delete user', 'danger');
                        }
                    } catch (error) {
                        showToast('Failed to delete user', 'danger');
                    }
                },
            },
        ],
    });
    await alert.present();
};

const showUserDetails = async (user) => {
    const alert = await alertController.create({
        header: `User: ${user.user_id}`,
        message: `
      <strong>Roles:</strong> ${user.roles.join(', ')}<br><br>
      <strong>Permissions:</strong> ${user.permissions.length} permission(s)
    `,
        buttons: ['OK'],
    });
    await alert.present();
};

const checkPermission = async () => {
    if (!permCheck.value.userId || !permCheck.value.topic || !permCheck.value.action) {
        showToast('Please fill all fields', 'danger');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/acl/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: permCheck.value.userId,
                topic: permCheck.value.topic,
                action: permCheck.value.action,
            }),
        });

        if (response.ok) {
            permCheckResult.value = await response.json();
        } else {
            showToast('Failed to check permission', 'danger');
        }
    } catch (error) {
        showToast('Failed to check permission', 'danger');
    }
};

// Lifecycle
onMounted(() => {
    // Register WebSocket event handlers
    webSocketService.on('connection_status', handleConnectionStatus);
    webSocketService.on('sensor_data', handleSensorData);
    webSocketService.on('mqtt_status', handleMqttStatus);
    webSocketService.on('publish_ack', handlePublishAck);
    webSocketService.on('subscription_ack', handleSubscriptionAck);
    webSocketService.on('unsubscription_ack', handleUnsubscriptionAck);
    webSocketService.on('permission_revoked', handlePermissionRevoked);
    webSocketService.on('system_alert', handleSystemAlert);

    // Load ACL data
    loadAclInfo();
    loadRoles();
    loadUsers();
});

onUnmounted(() => {
    // Unregister WebSocket event handlers
    webSocketService.off('connection_status', handleConnectionStatus);
    webSocketService.off('sensor_data', handleSensorData);
    webSocketService.off('mqtt_status', handleMqttStatus);
    webSocketService.off('publish_ack', handlePublishAck);
    webSocketService.off('subscription_ack', handleSubscriptionAck);
    webSocketService.off('unsubscription_ack', handleUnsubscriptionAck);
    webSocketService.off('permission_revoked', handlePermissionRevoked);
    webSocketService.off('system_alert', handleSystemAlert);
});
</script>

<style scoped>
.active-tab {
    --background: rgba(255, 255, 255, 0.2);
}

/* Fix ion-item spacing for stacked labels */
ion-item {
    --padding-top: 8px;
    --padding-bottom: 8px;
    --inner-padding-end: 0;
}

ion-item ion-label[position="stacked"] {
    margin-bottom: 8px;
    font-weight: 500;
    font-size: 0.875rem;
}

ion-item ion-input,
ion-item ion-textarea,
ion-item ion-select {
    margin-top: 4px;
}

/* Ensure toggle has proper spacing */
ion-toggle {
    margin-top: 8px;
}

.messages-container {
    max-height: 400px;
    overflow-y: auto;
    background: var(--ion-color-light);
    border-radius: 8px;
    padding: 12px;
}

.message {
    background: white;
    border-left: 4px solid var(--ion-color-primary);
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message.sent {
    border-left-color: var(--ion-color-success);
}

.message.received {
    border-left-color: var(--ion-color-tertiary);
}

.message.system {
    border-left-color: var(--ion-color-warning);
}

.message.error {
    border-left-color: var(--ion-color-danger);
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.timestamp {
    font-size: 0.85em;
    color: var(--ion-color-medium);
    font-family: monospace;
}

.topic {
    font-weight: 600;
    color: var(--ion-color-primary);
    margin-bottom: 8px;
    font-family: monospace;
}

.payload {
    font-family: monospace;
    font-size: 0.9em;
    white-space: pre-wrap;
    word-break: break-all;
    color: var(--ion-color-dark);
}

.no-messages {
    text-align: center;
    padding: 60px 20px;
    color: var(--ion-color-medium);
}

.no-messages ion-icon {
    font-size: 64px;
    opacity: 0.5;
}

.no-messages p {
    margin-top: 16px;
    font-size: 0.95em;
}

.subscriptions-label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--ion-color-dark);
}

.stat-card {
    background: var(--ion-color-light);
    padding: 20px;
    border-radius: 8px;
    text-align: center;
}

.stat-value {
    font-size: 2em;
    font-weight: bold;
    color: var(--ion-color-primary);
    margin-bottom: 8px;
}

.stat-label {
    font-size: 0.9em;
    color: var(--ion-color-medium);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

ion-chip {
    margin: 4px;
    cursor: pointer;
}

ion-card {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

ion-card-title {
    font-size: 1.2em;
}

@media (max-width: 768px) {
    .stat-value {
        font-size: 1.5em;
    }

    .messages-container {
        max-height: 300px;
    }
}
</style>