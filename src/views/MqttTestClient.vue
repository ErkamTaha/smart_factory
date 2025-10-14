<template>
    <ion-page>
        <ion-header>
            <ion-toolbar color="primary">
                <ion-title>🏭 MQTT QoS & LWT Test Client</ion-title>
            </ion-toolbar>
        </ion-header>

        <ion-content :fullscreen="true" class="ion-padding">
            <!-- Connection Status -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>🔌 Connection</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-chip :color="statusColor">
                        <ion-label>{{ connectionStatus }}</ion-label>
                    </ion-chip>

                    <ion-item>
                        <ion-label position="stacked">User ID</ion-label>
                        <ion-input v-model="userId" placeholder="e.g., alice, bob, charlie"
                            :disabled="isConnected"></ion-input>
                    </ion-item>

                    <ion-item>
                        <ion-label position="stacked">WebSocket URL</ion-label>
                        <ion-input v-model="wsUrl" placeholder="ws://localhost:8000/ws/ws"
                            :disabled="isConnected"></ion-input>
                    </ion-item>

                    <ion-button expand="block" @click="connect" :disabled="isConnected" class="ion-margin-top">
                        Connect
                    </ion-button>
                    <ion-button expand="block" color="danger" @click="disconnect" :disabled="!isConnected">
                        Disconnect
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Subscribe Section -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>📥 Subscribe</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-item>
                        <ion-label position="stacked">Topic</ion-label>
                        <ion-input v-model="subscribeTopic" placeholder="e.g., sf/sensors/#"></ion-input>
                    </ion-item>

                    <ion-item>
                        <ion-label>QoS Level</ion-label>
                        <ion-select v-model="subscribeQos">
                            <ion-select-option :value="0">QoS 0 - At most once</ion-select-option>
                            <ion-select-option :value="1">QoS 1 - At least once</ion-select-option>
                            <ion-select-option :value="2">QoS 2 - Exactly once</ion-select-option>
                        </ion-select>
                    </ion-item>

                    <ion-button expand="block" @click="subscribe" :disabled="!isConnected" class="ion-margin-top">
                        Subscribe
                    </ion-button>

                    <ion-list v-if="subscribedTopics.length > 0" class="ion-margin-top">
                        <ion-list-header>
                            <ion-label>Active Subscriptions</ion-label>
                        </ion-list-header>
                        <ion-item v-for="topic in subscribedTopics" :key="topic">
                            <ion-label>{{ topic }}</ion-label>
                            <ion-button slot="end" size="small" color="danger" @click="unsubscribe(topic)">
                                Unsubscribe
                            </ion-button>
                        </ion-item>
                    </ion-list>
                </ion-card-content>
            </ion-card>

            <!-- Publish Section -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>📤 Publish</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-item>
                        <ion-label position="stacked">Topic</ion-label>
                        <ion-input v-model="publishTopic" placeholder="e.g., sf/sensors/temperature"></ion-input>
                    </ion-item>

                    <ion-item>
                        <ion-label position="stacked">Payload (JSON)</ion-label>
                        <ion-textarea v-model="publishPayload" :rows="4"
                            placeholder='{"value": 25.5, "unit": "C"}'></ion-textarea>
                    </ion-item>

                    <ion-item>
                        <ion-label>QoS Level</ion-label>
                        <ion-select v-model="publishQos">
                            <ion-select-option :value="0">QoS 0 - At most once</ion-select-option>
                            <ion-select-option :value="1">QoS 1 - At least once</ion-select-option>
                            <ion-select-option :value="2">QoS 2 - Exactly once</ion-select-option>
                        </ion-select>
                    </ion-item>

                    <ion-item>
                        <ion-label>Retain Message</ion-label>
                        <ion-toggle v-model="publishRetain"></ion-toggle>
                    </ion-item>

                    <ion-button expand="block" @click="publish" :disabled="!isConnected" class="ion-margin-top">
                        Publish
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Quick Actions -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>⚡ Quick Actions</ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-button expand="block" @click="subscribeToAllStatus" :disabled="!isConnected">
                        Monitor All Status Topics
                    </ion-button>
                    <ion-button expand="block" @click="subscribeToSensors" :disabled="!isConnected">
                        Monitor All Sensors (sf/sensors/#)
                    </ion-button>
                    <ion-button expand="block" @click="subscribeToBackendStatus" :disabled="!isConnected">
                        Monitor Backend Status
                    </ion-button>
                    <ion-button expand="block" @click="publishTestSensorData" :disabled="!isConnected">
                        Publish Test Sensor Data
                    </ion-button>
                </ion-card-content>
            </ion-card>

            <!-- Messages Log -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>
                        💬 Messages ({{ messages.length }})
                        <ion-button size="small" fill="outline" @click="clearMessages" class="ion-float-right">
                            Clear
                        </ion-button>
                    </ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <div class="messages-container">
                        <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.type]">
                            <div class="message-header">
                                <span class="timestamp">{{ msg.timestamp }}</span>
                                <ion-chip v-if="msg.qos !== undefined" size="small" color="primary">
                                    QoS {{ msg.qos }}
                                </ion-chip>
                            </div>
                            <div v-if="msg.topic" class="topic">{{ msg.topic }}</div>
                            <div class="payload">{{ msg.payload }}</div>
                        </div>
                        <div v-if="messages.length === 0" class="no-messages">
                            No messages yet. Connect and subscribe to topics to see messages.
                        </div>
                    </div>
                </ion-card-content>
            </ion-card>
        </ion-content>
    </ion-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
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
    IonListHeader,
    alertController,
    toastController,
} from '@ionic/vue';

// State
const ws = ref<WebSocket | null>(null);
const userId = ref('alice');
const wsUrl = ref('ws://localhost:8000/ws/ws');
const isConnected = ref(false);
const connectionStatus = ref('Disconnected');

// Subscribe state
const subscribeTopic = ref('sf/sensors/#');
const subscribeQos = ref(1);
const subscribedTopics = ref<string[]>([]);

// Publish state
const publishTopic = ref('sf/sensors/temperature');
const publishPayload = ref('{\n  "value": 25.5,\n  "unit": "C",\n  "timestamp": "' + new Date().toISOString() + '"\n}');
const publishQos = ref(1);
const publishRetain = ref(false);

// Messages
interface Message {
    timestamp: string;
    type: 'sent' | 'received' | 'system' | 'error';
    topic?: string;
    payload: string;
    qos?: number;
}

const messages = ref<Message[]>([]);

// Computed
const statusColor = computed(() => {
    if (isConnected.value) return 'success';
    if (connectionStatus.value === 'Connecting...') return 'warning';
    return 'danger';
});

// Methods
const addMessage = (type: Message['type'], content: Partial<Message>) => {
    const msg: Message = {
        timestamp: new Date().toLocaleTimeString(),
        type,
        payload: content.payload || content.topic || '',
        ...content,
    };
    messages.value.push(msg);

    // Keep only last 100 messages
    if (messages.value.length > 100) {
        messages.value.shift();
    }
};

const showToast = async (message: string, color: string = 'primary') => {
    const toast = await toastController.create({
        message,
        duration: 2000,
        color,
        position: 'bottom',
    });
    await toast.present();
};

const connect = () => {
    if (!userId.value.trim()) {
        showToast('Please enter a User ID', 'danger');
        return;
    }

    connectionStatus.value = 'Connecting...';
    addMessage('system', { payload: `Connecting as user: ${userId.value}` });

    const url = `${wsUrl.value}?user_id=${userId.value}`;
    ws.value = new WebSocket(url);

    ws.value.onopen = () => {
        isConnected.value = true;
        connectionStatus.value = 'Connected';
        addMessage('system', { payload: `✓ Connected as ${userId.value}` });
        showToast('Connected successfully', 'success');
    };

    ws.value.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'sensor_data') {
                addMessage('received', {
                    topic: data.topic,
                    qos: data.qos,
                    payload: JSON.stringify(data.data, null, 2),
                });
            } else if (data.type === 'mqtt_status') {
                addMessage('system', {
                    payload: `MQTT Status: ${data.status} - ${data.message}`,
                });
                if (data.qos !== undefined) {
                    addMessage('system', {
                        payload: `Your QoS level: ${data.qos}`,
                    });
                }
            } else if (data.type === 'publish_ack') {
                addMessage(data.status === 'success' ? 'sent' : 'error', {
                    topic: data.topic,
                    qos: data.qos,
                    payload: `Publish ${data.status}`,
                });
            } else if (data.type === 'subscription_ack') {
                subscribedTopics.value = data.current_subscriptions || [];
                addMessage('system', {
                    payload: `Subscribed to: ${data.topics?.join(', ')}`,
                });
            } else if (data.type === 'unsubscription_ack') {
                subscribedTopics.value = data.current_subscriptions || [];
                addMessage('system', {
                    payload: `Unsubscribed from: ${data.topics?.join(', ')}`,
                });
            } else if (data.type === 'permission_revoked') {
                addMessage('error', {
                    topic: data.topic,
                    payload: `Permission revoked: ${data.message}`,
                });
                showToast(`Permission revoked for ${data.topic}`, 'danger');
            } else {
                addMessage('system', {
                    payload: JSON.stringify(data, null, 2),
                });
            }
        } catch (e) {
            addMessage('error', { payload: 'Failed to parse message: ' + event.data });
        }
    };

    ws.value.onerror = () => {
        addMessage('error', { payload: 'WebSocket error occurred' });
        showToast('WebSocket error', 'danger');
    };

    ws.value.onclose = () => {
        isConnected.value = false;
        connectionStatus.value = 'Disconnected';
        subscribedTopics.value = [];
        addMessage('system', { payload: '✗ Disconnected from WebSocket' });
        showToast('Disconnected', 'warning');
    };
};

const disconnect = () => {
    if (ws.value) {
        ws.value.close();
        ws.value = null;
    }
};

const subscribe = () => {
    if (!subscribeTopic.value.trim()) {
        showToast('Please enter a topic', 'danger');
        return;
    }

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(
            JSON.stringify({
                type: 'subscribe',
                topics: [subscribeTopic.value],
                qos: subscribeQos.value,
            })
        );
        addMessage('system', {
            payload: `Subscribing to: ${subscribeTopic.value} (QoS ${subscribeQos.value})`,
        });
    }
};

const unsubscribe = (topic: string) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(
            JSON.stringify({
                type: 'unsubscribe',
                topics: [topic],
            })
        );
        addMessage('system', {
            payload: `Unsubscribing from: ${topic}`,
        });
    }
};

const publish = async () => {
    if (!publishTopic.value.trim() || !publishPayload.value.trim()) {
        showToast('Please enter topic and payload', 'danger');
        return;
    }

    // Validate JSON
    try {
        JSON.parse(publishPayload.value);
    } catch {
        const alert = await alertController.create({
            header: 'Invalid JSON',
            message: 'Payload is not valid JSON. Send anyway?',
            buttons: [
                { text: 'Cancel', role: 'cancel' },
                {
                    text: 'Send',
                    handler: () => {
                        performPublish();
                    },
                },
            ],
        });
        await alert.present();
        return;
    }

    performPublish();
};

const performPublish = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(
            JSON.stringify({
                type: 'publish',
                topic: publishTopic.value,
                payload: publishPayload.value,
                qos: publishQos.value,
                retain: publishRetain.value,
            })
        );
        addMessage('sent', {
            topic: publishTopic.value,
            qos: publishQos.value,
            payload: publishPayload.value,
        });
    }
};

// Quick Actions
const subscribeToAllStatus = () => {
    subscribeTopic.value = 'factory/+/status';
    subscribeQos.value = 1;
    subscribe();
};

const subscribeToSensors = () => {
    subscribeTopic.value = 'sf/sensors/#';
    subscribeQos.value = 1;
    subscribe();
};

const subscribeToBackendStatus = () => {
    subscribeTopic.value = 'factory/backend/status';
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
</script>

<style scoped>
.messages-container {
    max-height: 500px;
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
    padding: 40px 20px;
    color: var(--ion-color-medium);
}

ion-chip {
    margin: 0;
    padding: 4px 8px;
    height: auto;
}
</style>