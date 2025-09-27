import paho.mqtt.client as mqtt
from typing import Callable, Dict, List, Optional, Union
import json
import logging

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
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            # Resubscribe to topics on reconnection
            for topic in self.subscriptions.keys():
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        logger.info(f"Received message on topic {topic}: {payload}")
        
        # Call all registered callbacks for this topic
        if topic in self.subscriptions:
            for callback in self.subscriptions[topic]:
                try:
                    # Try to parse as JSON, otherwise send as string
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        data = payload
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
            payload = json.dumps(payload)
        
        result = self.client.publish(topic, payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published to {topic}: {payload}")
        else:
            logger.error(f"Failed to publish to {topic}")
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