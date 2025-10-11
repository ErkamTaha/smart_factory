import paho.mqtt.client as mqtt
from typing import Callable, Dict, List, Optional, Union
import json
import logging
import asyncio
import threading

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, broker_host: str, broker_port: int, 
                 username: Optional[str] = None, password: Optional[str] = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = mqtt.Client(client_id="smart_factory_backend")
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.websocket_manager = None  # Will be set from main.py
        self.main_loop = None  # Will store the main event loop
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)
    
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager for broadcasting"""
        self.websocket_manager = websocket_manager
        # Store the main event loop for later use
        try:
            self.main_loop = asyncio.get_running_loop()
            logger.info("WebSocket manager connected to MQTT client")
        except RuntimeError:
            logger.warning("No running event loop found, WebSocket broadcasting may not work")
    
    def _safe_broadcast(self, coro):
        """Safely schedule a coroutine to run in the main event loop"""
        if self.main_loop and self.websocket_manager:
            try:
                # Schedule the coroutine to run in the main thread's event loop
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)
            except Exception as e:
                logger.error(f"Error scheduling WebSocket broadcast: {e}")
        else:
            if not self.websocket_manager:
                logger.debug("WebSocket manager not available, skipping broadcast")
            if not self.main_loop:
                logger.debug("Main event loop not available, skipping broadcast")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            # Resubscribe to topics on reconnection
            for topic in self.subscriptions.keys():
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
            
            # Safely broadcast connection status via WebSocket
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "info", 
                        "MQTT broker connected",
                        {"broker": f"{self.broker_host}:{self.broker_port}"}
                    )
                )
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            # Safely broadcast connection failure
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "error", 
                        "MQTT broker connection failed",
                        {"return_code": rc}
                    )
                )
    
    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
        # Safely broadcast disconnection via WebSocket
        if self.websocket_manager:
            self._safe_broadcast(
                self.websocket_manager.broadcast_system_alert(
                    "warning", 
                    "MQTT broker disconnected",
                    {"return_code": rc}
                )
            )
    
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        logger.info(f"Received message on topic {topic}: {payload}")
        
        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = payload
        
        # Safely broadcast to WebSocket clients (for real-time updates)
        if self.websocket_manager:
            self._safe_broadcast(
                self.websocket_manager.broadcast_sensor_data(topic, data)
            )
        
        # Call all registered callbacks for this topic (existing functionality)
        if topic in self.subscriptions:
            for callback in self.subscriptions[topic]:
                try:
                    callback(topic, data)
                except Exception as e:
                    logger.error(f"Error in callback for topic {topic}: {e}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")
    
    def publish(self, topic: str, payload: Union[dict, str]):
        """Publish message to topic"""
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)
        
        result = self.client.publish(topic, payload_str)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published to {topic}: {payload_str}")
            
            # Safely broadcast publish event via WebSocket
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast({
                        "type": "mqtt_publish",
                        "topic": topic,
                        "payload": payload if isinstance(payload, dict) else payload_str,
                        "status": "success"
                    })
                )
        else:
            logger.error(f"Failed to publish to {topic}")
            
            # Safely broadcast publish failure
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "error",
                        f"Failed to publish to MQTT topic: {topic}",
                        {"return_code": result.rc}
                    )
                )
        
        return result
    
    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic with callback function"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            self.client.subscribe(topic)
        
        self.subscriptions[topic].append(callback)
        logger.info(f"Added callback for topic: {topic}")
    
    def unsubscribe(self, topic: str):
        """Unsubscribe from topic"""
        if topic in self.subscriptions:
            del self.subscriptions[topic]
            self.client.unsubscribe(topic)
            logger.info(f"Unsubscribed from topic: {topic}")

# Global MQTT client instance
mqtt_client: Optional[MQTTClient] = None

def get_mqtt_client() -> Optional[MQTTClient]:
    """Get global MQTT client instance"""
    return mqtt_client

def init_mqtt_client(broker_host: str, broker_port: int, 
                     username: Optional[str] = None, password: Optional[str] = None) -> MQTTClient:
    """Initialize global MQTT client"""
    global mqtt_client
    mqtt_client = MQTTClient(broker_host, broker_port, username, password)
    return mqtt_client