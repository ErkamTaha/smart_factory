import paho.mqtt.client as mqtt
from typing import Callable, Dict, List, Optional, Union
import json
import logging
import asyncio
import threading
import ssl
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 1,
        tls_enabled: bool = False,
        ca_certs: Optional[str] = None,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.qos = qos  # Default QoS level for this client
        self.tls_enabled = tls_enabled
        self.ca_certs = ca_certs
        self.client = mqtt.Client(client_id="smart_factory_backend")
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.websocket_manager = None  # Will be set from main.py
        self.main_loop = None  # Will store the main event loop

        # Setup Last Will and Testament
        # Backend going offline is critical - use QoS 1 and retain
        self.client.will_set(
            topic="sf/backend/status",
            payload=json.dumps(
                {
                    "status": "offline",
                    "client_id": "smart_factory_backend",
                    "reason": "unexpected_disconnect",
                    "timestamp": None,  # Broker will use current time when publishing LWT
                }
            ),
            qos=1,
            retain=True,
        )

        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)

        # Configure TLS if enabled

        if tls_enabled and broker_port == 8883:

            try:

                self.client.tls_set(
                    ca_certs=ca_certs,
                    certfile=None,
                    keyfile=None,
                    tls_version=ssl.PROTOCOL_TLS,
                )

                # Don't verify hostname for self-signed certs

                self.client.tls_insecure_set(True)

                logger.info(
                    f"TLS enabled for backend MQTT client with ca_certs: {ca_certs}"
                )

            except Exception as e:

                logger.error(f"Failed to setup TLS for backend MQTT client: {e}")

                raise

    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager for broadcasting"""
        self.websocket_manager = websocket_manager
        # Store the main event loop for later use
        try:
            self.main_loop = asyncio.get_running_loop()
            logger.info("WebSocket manager connected to MQTT client")
        except RuntimeError:
            logger.warning(
                "No running event loop found, WebSocket broadcasting may not work"
            )

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
            logger.info(
                f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}"
            )

            # Publish online status immediately after connecting (overrides LWT)
            # Use retained message so new subscribers see it immediately
            online_status = json.dumps(
                {
                    "status": "online",
                    "client_id": "smart_factory_backend",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            client.publish("sf/backend/status", online_status, qos=1, retain=True)
            logger.info("Published backend online status")

            # Resubscribe to topics on reconnection with QoS
            # Create a copy of keys to avoid RuntimeError if dict changes during iteration
            for topic in list(self.subscriptions.keys()):
                client.subscribe(topic, qos=self.qos)
                logger.info(f"Subscribed to topic: {topic} with QoS {self.qos}")

            # Safely broadcast connection status via WebSocket
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "info",
                        "MQTT broker connected",
                        {"broker": f"{self.broker_host}:{self.broker_port}"},
                    )
                )
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            # Safely broadcast connection failure
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "error", "MQTT broker connection failed", {"return_code": rc}
                    )
                )

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
        # Safely broadcast disconnection via WebSocket
        if self.websocket_manager:
            self._safe_broadcast(
                self.websocket_manager.broadcast_system_alert(
                    "warning", "MQTT broker disconnected", {"return_code": rc}
                )
            )

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos
        retain = msg.retain

        logger.info(f"Received message on topic {topic} (QoS {qos}): {payload}")

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = payload

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
        """Disconnect from MQTT broker gracefully"""
        # Publish offline status before disconnecting (graceful shutdown)
        offline_status = json.dumps(
            {
                "status": "offline",
                "client_id": "smart_factory_backend",
                "reason": "graceful_shutdown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.client.publish("sf/backend/status", offline_status, qos=1, retain=True)
        logger.info("Published backend offline status (graceful shutdown)")

        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")

    def publish(
        self,
        topic: str,
        payload: Union[dict, str],
        qos: Optional[int] = None,
        retain: bool = False,
    ):
        """
        Publish message to topic
        """
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        # Use provided QoS or fall back to client default
        publish_qos = qos if qos is not None else self.qos

        result = self.client.publish(topic, payload_str, qos=publish_qos, retain=retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(
                f"Published to {topic} (QoS {publish_qos}, retain={retain}): {payload_str}"
            )

            # Safely broadcast publish event via WebSocket
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast(
                        {
                            "type": "mqtt_publish",
                            "topic": topic,
                            "payload": (
                                payload if isinstance(payload, dict) else payload_str
                            ),
                            "qos": publish_qos,
                            "retain": retain,
                            "status": "success",
                        }
                    )
                )
        else:
            logger.error(f"Failed to publish to {topic} (QoS {publish_qos})")

            # Safely broadcast publish failure
            if self.websocket_manager:
                self._safe_broadcast(
                    self.websocket_manager.broadcast_system_alert(
                        "error",
                        f"Failed to publish to MQTT topic: {topic}",
                        {"return_code": result.rc, "qos": publish_qos},
                    )
                )

        return result

    def subscribe(self, topic: str, callback: Callable, qos: Optional[int] = None):
        """
        Subscribe to topic with callback function
        """
        subscribe_qos = qos if qos is not None else self.qos

        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            self.client.subscribe(topic, qos=subscribe_qos)
            logger.info(f"Subscribed to topic: {topic} with QoS {subscribe_qos}")

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


def init_mqtt_client(
    broker_host: str,
    broker_port: int,
    username: Optional[str] = None,
    password: Optional[str] = None,
    qos: int = 1,
    tls_enabled: bool = False,
    ca_certs: Optional[str] = None,
) -> MQTTClient:
    global mqtt_client
    mqtt_client = MQTTClient(
        broker_host, broker_port, username, password, qos, tls_enabled, ca_certs
    )
    return mqtt_client
