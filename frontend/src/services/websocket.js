class WebSocketService {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.messageHandlers = new Map();
        this.isConnecting = false;
        this.isManuallyDisconnected = false;
        this.currentUserId = null;
        this.currentUrl = null;
    }

    connect(url, userId) {
        return new Promise((resolve, reject) => {
            if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
                console.log('WebSocket already connected or connecting');
                resolve();
                return;
            }

            this.isConnecting = true;
            this.isManuallyDisconnected = false;
            this.currentUserId = userId;
            this.currentUrl = url;

            // Add user_id to URL
            const urlWithUser = `${url}?user_id=${userId}`;

            try {
                console.log(`Connecting to WebSocket: ${urlWithUser}`);
                this.ws = new WebSocket(urlWithUser);

                this.ws.onopen = (event) => {
                    console.log('WebSocket connected successfully as user:', userId);
                    this.isConnecting = false;
                    this.reconnectAttempts = 0;
                    this.reconnectDelay = 1000;

                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        console.log('WebSocket message received:', message);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket connection closed:', event.code, event.reason);
                    this.isConnecting = false;

                    // Notify handlers about disconnection
                    this.notifyHandlers('connection_status', {
                        status: 'disconnected',
                        event: 'close',
                        code: event.code,
                        reason: event.reason
                    });

                    // Auto-reconnect if not manually disconnected
                    if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.isConnecting = false;

                    // Notify handlers about error
                    this.notifyHandlers('connection_status', {
                        status: 'error',
                        event: 'error',
                        error: error
                    });

                    reject(error);
                };

            } catch (error) {
                console.error('Failed to create WebSocket connection:', error);
                this.isConnecting = false;
                reject(error);
            }
        });
    }

    disconnect() {
        this.isManuallyDisconnected = true;
        this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect

        if (this.ws) {
            this.ws.close(1000, 'Manual disconnect');
            this.ws = null;
        }

        this.currentUserId = null;
        this.currentUrl = null;
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);

        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

        setTimeout(() => {
            if (!this.isManuallyDisconnected && this.currentUrl && this.currentUserId) {
                this.connect(this.currentUrl, this.currentUserId);
            }
        }, delay);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
                this.ws.send(messageStr);
                console.log('WebSocket message sent:', message);
            } catch (error) {
                console.error('Error sending WebSocket message:', error);
            }
        } else {
            console.warn('WebSocket not connected, cannot send message:', message);
        }
    }

    handleMessage(message) {
        const messageType = message.type;

        if (messageType) {
            this.notifyHandlers(messageType, message);
        }

        // Handle specific message types
        switch (messageType) {
            case 'pong':
                console.log('Received pong from server');
                break;

            case 'connection_status':
                console.log('Connection status:', message);
                break;

            case 'sensor_data':
                console.log('Received sensor data:', message.topic, message.data);
                break;

            case 'mqtt_status':
                console.log('MQTT status:', message.status, message.message);
                break;

            case 'publish_ack':
                console.log('Publish acknowledgment:', message.topic, message.status);
                break;

            case 'subscription_ack':
                console.log('Subscription acknowledgment:', message.topics);
                break;

            case 'unsubscription_ack':
                console.log('Unsubscription acknowledgment:', message.topics);
                break;

            case 'permission_revoked':
                console.warn('Permission revoked:', message.topic, message.message);
                break;

            case 'system_alert':
                console.log('System alert:', message.level, message.message);
                break;

            case 'device_status':
                console.log('Device status:', message);
                break;

            case 'mqtt_publish':
                console.log('MQTT publish event:', message);
                break;

            default:
                console.log('Unhandled message type:', messageType, message);
        }
    }

    notifyHandlers(type, data) {
        const handlers = this.messageHandlers.get(type);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in message handler for type ${type}:`, error);
                }
            });
        }
    }

    // Subscribe to specific message types
    on(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, []);
        }
        this.messageHandlers.get(messageType).push(handler);
        console.log(`Subscribed to WebSocket message type: ${messageType}`);
    }

    // Unsubscribe from message types
    off(messageType, handler) {
        const handlers = this.messageHandlers.get(messageType);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }

            // Remove empty arrays
            if (handlers.length === 0) {
                this.messageHandlers.delete(messageType);
            }
        }
    }

    // Get connection status
    getConnectionStatus() {
        if (!this.ws) return 'disconnected';

        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    // MQTT-specific methods

    // Subscribe to MQTT topics
    subscribeMQTT(topics, qos = 1) {
        this.send({
            type: 'subscribe',
            topics: Array.isArray(topics) ? topics : [topics],
            qos: qos
        });
    }

    // Unsubscribe from MQTT topics
    unsubscribeMQTT(topics) {
        this.send({
            type: 'unsubscribe',
            topics: Array.isArray(topics) ? topics : [topics]
        });
    }

    // Publish to MQTT topic
    publishMQTT(topic, payload, qos = 1, retain = false) {
        this.send({
            type: 'publish',
            topic: topic,
            payload: payload,
            qos: qos,
            retain: retain
        });
    }

    // Get MQTT status
    getMQTTStatus() {
        this.send({
            type: 'get_status'
        });
    }

    // Get all connected users
    getAllUsers() {
        this.send({
            type: 'get_all_users'
        });
    }

    // Send ping
    ping() {
        this.send({
            type: 'ping',
            timestamp: new Date().toISOString()
        });
    }

    // Get current user ID
    getUserId() {
        return this.currentUserId;
    }
}

// Export singleton instance
export const webSocketService = new WebSocketService();
export default webSocketService;