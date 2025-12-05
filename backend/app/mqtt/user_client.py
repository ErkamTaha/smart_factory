import paho.mqtt.client as mqtt
from typing import Dict, Optional, Callable, List, Any, Tuple
import json
import logging
import asyncio
from datetime import datetime, timezone
from fastapi import WebSocket
from app.security.db_acl_manager import get_acl_manager
from app.websocket.manager import get_websocket_manager
from app.security.db_ss_manager import get_ss_manager

logger = logging.getLogger(__name__)


class UserMQTTClient:
    """Individual MQTT client for a single user with ACL enforcement"""

    def __init__(
        self,
        user_id: str,
        broker_host: str,
        broker_port: int,
        websocket: WebSocket,
        main_loop,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 1,
    ):
        self.user_id = user_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.websocket = websocket
        self.main_loop = main_loop
        self.username = username
        self.password = password
        self.qos = qos  # Default QoS level

        # Create unique MQTT client ID for this user
        client_id = f"smart_factory_user_{user_id}_{id(self)}"
        self.client = mqtt.Client(client_id=client_id)

        self.subscribed_topics: List[str] = []
        self.is_connected = False

        # Setup Last Will and Testament for user disconnection
        # User disconnection is important - use QoS 1 and retain
        self.client.will_set(
            topic=f"sf/users/{user_id}/status",
            payload=json.dumps(
                {
                    "user_id": user_id,
                    "status": "offline",
                    "reason": "unexpected_disconnect",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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

        logger.info(f"Created MQTT client for user: {user_id} with QoS {qos}")

    def _check_acl_permission(self, topic: str, action: str) -> bool:
        """Check if user has permission using ACL"""
        acl = get_acl_manager()
        if not acl:
            logger.warning("ACL manager not available, allowing by default")
            return True

        return acl.check_permission(self.user_id, topic, action)

    def _check_ss_limit(
        self, sensor_id: str, value: str, unit: str
    ) -> Tuple[bool, Optional[str]]:
        """Check SS limit config for alert"""
        ss = get_ss_manager()
        if not ss:
            logger.warning("SS manager not available, can't check for alert")
            return False, None

        alert, alert_type = ss.check_limit_for_alert(sensor_id, value, unit)
        return alert, alert_type

    async def _broadcast_system_alert(
        self, level: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        # Broadcast system alert with global websocket client
        ws = get_websocket_manager()
        if not ws:
            logger.warning("Websocket manager not avaliable, can't broadcast alert.")
        await ws.broadcast_system_alert(level, message, details)

    def _get_sensor_info(self, sensor_id) -> Optional[Dict]:
        # Get sensor info
        ss = get_ss_manager()
        if not ss:
            logger.warning("SS manager not available, can't check for alert")
            return None
        return ss.get_sensor_info(sensor_id)

    def _on_connect(self, client, userdata, flags, rc):
        """Called when MQTT connection is established"""
        if rc == 0:
            self.is_connected = True
            logger.info(f"User {self.user_id} connected to MQTT broker")

            # Publish online status immediately after connecting (overrides LWT)
            online_status = json.dumps(
                {
                    "user_id": self.user_id,
                    "status": "online",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            client.publish(
                f"sf/users/{self.user_id}/status", online_status, qos=1, retain=True
            )
            logger.info(f"Published online status for user {self.user_id}")

            # Resubscribe to topics on reconnection (check permissions again)
            for topic in self.subscribed_topics[
                :
            ]:  # Copy list to avoid modification during iteration
                if self._check_acl_permission(topic, "subscribe"):
                    client.subscribe(topic, qos=self.qos)
                    logger.info(
                        f"User {self.user_id} resubscribed to: {topic} with QoS {self.qos}"
                    )
                else:
                    # Remove from subscribed list if permission revoked
                    self.subscribed_topics.remove(topic)
                    logger.warning(f"User {self.user_id} lost permission for: {topic}")
                    self._send_to_user(
                        {
                            "type": "permission_revoked",
                            "topic": topic,
                            "action": "subscribe",
                            "message": "Your subscription permission was revoked",
                        }
                    )

            # Notify user via WebSocket
            self._send_to_user(
                {
                    "type": "mqtt_status",
                    "status": "connected",
                    "message": "Your MQTT session is connected",
                    "qos": self.qos,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            self.is_connected = False
            logger.error(
                f"User {self.user_id} failed to connect to MQTT broker. RC: {rc}"
            )
            self._send_to_user(
                {
                    "type": "mqtt_status",
                    "status": "error",
                    "message": f"MQTT connection failed with code {rc}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def _on_disconnect(self, client, userdata, rc):
        """Called when MQTT connection is lost"""
        self.is_connected = False
        logger.warning(f"User {self.user_id} disconnected from MQTT broker. RC: {rc}")

        self._send_to_user(
            {
                "type": "mqtt_status",
                "status": "disconnected",
                "message": "MQTT connection lost",
                "return_code": rc,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _on_message(self, client, userdata, msg):
        """Called when MQTT message is received"""
        topic = msg.topic
        payload = msg.payload.decode()
        qos = msg.qos
        retain = msg.retain

        logger.info(f"User {self.user_id} received message on {topic} (QoS {qos})")

        # Double-check permission (in case ACL changed)
        if not self._check_acl_permission(topic, "subscribe"):
            logger.warning(
                f"User {self.user_id} received message but permission revoked for {topic}"
            )
            # Unsubscribe automatically
            self.unsubscribe(topic)
            return

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = payload

        # Send to user's WebSocket
        self._send_to_user(
            {
                "type": "sensor_data",
                "topic": topic,
                "data": data,
                "qos": qos,
                "retain": retain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _send_to_user(self, message: Dict[str, Any]):
        """Safely send message to user's WebSocket from MQTT thread"""
        if self.main_loop and self.websocket:
            try:
                coro = self.websocket.send_text(json.dumps(message))
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)
            except Exception as e:
                logger.error(f"Error sending to user {self.user_id}: {e}")

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            logger.info(f"User {self.user_id} MQTT loop started")
        except Exception as e:
            logger.error(f"Error connecting user {self.user_id} to MQTT: {e}")
            raise

    def disconnect(self):
        """Disconnect from MQTT broker gracefully"""
        try:
            # Publish offline status before disconnecting (graceful shutdown)
            offline_status = json.dumps(
                {
                    "user_id": self.user_id,
                    "status": "offline",
                    "reason": "graceful_disconnect",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            self.client.publish(
                f"sf/users/{self.user_id}/status", offline_status, qos=1, retain=True
            )
            logger.info(f"Published offline status for user {self.user_id} (graceful)")

            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info(f"User {self.user_id} disconnected from MQTT")
        except Exception as e:
            logger.error(f"Error disconnecting user {self.user_id} from MQTT: {e}")

    def subscribe(self, topic: str, qos: Optional[int] = None) -> Dict[str, Any]:
        """
        Subscribe to MQTT topic with ACL check
        """
        # Check ACL permission
        if not self._check_acl_permission(topic, "subscribe"):
            logger.warning(f"User {self.user_id} denied subscription to: {topic}")
            return {
                "success": False,
                "reason": "Permission denied by ACL",
                "topic": topic,
            }

        subscribe_qos = qos if qos is not None else self.qos

        if topic not in self.subscribed_topics:
            self.subscribed_topics.append(topic)
            self.client.subscribe(topic, qos=subscribe_qos)
            logger.info(
                f"User {self.user_id} subscribed to: {topic} with QoS {subscribe_qos}"
            )
            return {"success": True, "topic": topic, "qos": subscribe_qos}

        return {"success": False, "reason": "Already subscribed", "topic": topic}

    def unsubscribe(self, topic: str) -> Dict[str, Any]:
        """Unsubscribe from MQTT topic"""
        if topic in self.subscribed_topics:
            self.subscribed_topics.remove(topic)
            self.client.unsubscribe(topic)
            logger.info(f"User {self.user_id} unsubscribed from: {topic}")
            return {"success": True, "topic": topic}
        return {"success": False, "reason": "Not subscribed", "topic": topic}

    async def publish(
        self, topic: str, payload, qos: Optional[int] = None, retain: bool = False
    ) -> Dict[str, Any]:
        """
        Publish message to MQTT topic with ACL and SS check
        """
        # Check ACL permission
        if not self._check_acl_permission(topic, "publish"):
            logger.warning(f"User {self.user_id} denied publish to: {topic}")
            self._send_to_user(
                {
                    "type": "publish_ack",
                    "topic": topic,
                    "status": "error",
                    "reason": "Permission denied by ACL",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return {"success": False, "reason": "Permission denied by ACL"}

        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        publish_qos = qos if qos is not None else self.qos

        # Check sensor limits for alert (only if payload is sensor data)
        alert = False
        alert_type = None

        try:
            logger.info(
                f"DEBUG: Checking payload for sensor data. Payload type: {type(payload)}, payload: {payload}"
            )

            # Parse payload if it's a JSON string
            parsed_payload = payload
            if isinstance(payload, str):
                try:
                    parsed_payload = json.loads(payload)
                    logger.info(f"DEBUG: Parsed JSON string to dict: {parsed_payload}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse payload as JSON: {e}")
                    parsed_payload = payload  # Keep original if parsing fails

            # Only check sensor limits if the payload looks like sensor data
            if (
                isinstance(parsed_payload, dict)
                and "value" in parsed_payload
                and "unit" in parsed_payload
            ):
                logger.info(f"DEBUG: Payload is sensor data, proceeding with SS check")

                # Extract sensor ID from topic
                parts = topic.split("/")
                logger.info(f"DEBUG: Topic parts: {parts}")

                if len(parts) >= 3:
                    # For topics like "sf/sensors/test_device_001" or "sf/sensors/test_device_001/temperature"
                    # The sensor ID should be the 3rd part (index 2)
                    if len(parts) >= 3 and parts[0] == "sf" and parts[1] == "sensors":
                        sensor_id = parts[
                            2
                        ]  # Extract device ID from sf/sensors/DEVICE_ID/...
                    else:
                        sensor_id = parts[-1]  # Fallback to last part

                    sensor_value = parsed_payload["value"]
                    sensor_unit = parsed_payload["unit"]

                    logger.info(
                        f"DEBUG: Extracted - sensor_id: '{sensor_id}', value: {sensor_value}, unit: '{sensor_unit}'"
                    )

                    alert, alert_type = self._check_ss_limit(
                        sensor_id, sensor_value, sensor_unit
                    )

                    logger.info(
                        f"SS Check Result - Alert: {alert}, alert_type: {alert_type}, "
                        f"sensor_id: {sensor_id}, sensor_value: {sensor_value}, sensor_unit: {sensor_unit}"
                    )

                    if alert:
                        alert_message = f"Sensor {sensor_id} exceeded {alert_type} limit with value: {sensor_value} {sensor_unit}."
                        logger.info(f"DEBUG: Broadcasting alert: {alert_message}")
                        await self._broadcast_system_alert(
                            "warning",
                            alert_message,
                            {
                                "topic": topic,
                                "sensor_id": sensor_id,
                                "value": sensor_value,
                                "unit": sensor_unit,
                                "alert_type": alert_type,
                                "qos": publish_qos,
                                "retain": retain,
                            },
                        )
                    else:
                        logger.info(f"DEBUG: No alert triggered for sensor {sensor_id}")
                else:
                    logger.warning(
                        f"Topic {topic} doesn't have enough parts to extract sensor ID (parts: {parts})"
                    )
            else:
                logger.info(
                    f"Payload is not sensor data or missing required fields. Type: {type(payload)}, keys: {list(payload.keys()) if isinstance(payload, dict) else 'N/A'}"
                )

        except Exception as e:
            logger.error(
                f"Error checking sensor limits for user {self.user_id}, topic {topic}: {e}"
            )
            # Continue with publish even if SS check fails

        # Publish the message
        result = self.client.publish(topic, payload_str, qos=publish_qos, retain=retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(
                f"User {self.user_id} published to {topic} (QoS {publish_qos}, retain={retain})"
            )

            # Notify user of successful publish
            self._send_to_user(
                {
                    "type": "publish_ack",
                    "topic": topic,
                    "status": "success",
                    "qos": publish_qos,
                    "retain": retain,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return {"success": True, "topic": topic, "qos": publish_qos}
        else:
            logger.error(f"User {self.user_id} failed to publish to {topic}")
            self._send_to_user(
                {
                    "type": "publish_ack",
                    "topic": topic,
                    "status": "error",
                    "return_code": result.rc,
                    "qos": publish_qos,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return {"success": False, "reason": f"MQTT error code {result.rc}"}


class UserMQTTClientManager:
    """Manages MQTT clients for multiple users"""

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 1,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.qos = qos  # Default QoS for all user clients
        self.user_clients: Dict[str, UserMQTTClient] = {}
        self.main_loop = None

        logger.info(f"UserMQTTClientManager initialized with default QoS {qos}")

    def set_main_loop(self, loop):
        """Set the main event loop for WebSocket communication"""
        self.main_loop = loop
        logger.info("Main event loop set for UserMQTTClientManager")

    def create_user_client(
        self, user_id: str, websocket: WebSocket, qos: Optional[int] = None
    ) -> UserMQTTClient:
        """
        Create and connect MQTT client for a user
        """
        # If user already has a client, disconnect it first
        if user_id in self.user_clients:
            logger.warning(f"User {user_id} already has an MQTT client, replacing it")
            self.remove_user_client(user_id)

        client_qos = qos if qos is not None else self.qos

        # Create new client
        client = UserMQTTClient(
            user_id=user_id,
            broker_host=self.broker_host,
            broker_port=self.broker_port,
            websocket=websocket,
            main_loop=self.main_loop,
            username=self.username,
            password=self.password,
            qos=client_qos,
        )

        # Connect to MQTT broker
        client.connect()

        # Store client
        self.user_clients[user_id] = client

        logger.info(
            f"Created and connected MQTT client for user: {user_id} with QoS {client_qos}"
        )
        return client

    def get_user_client(self, user_id: str) -> Optional[UserMQTTClient]:
        """Get MQTT client for a user"""
        return self.user_clients.get(user_id)

    def remove_user_client(self, user_id: str):
        """Remove and disconnect MQTT client for a user"""
        if user_id in self.user_clients:
            client = self.user_clients[user_id]
            client.disconnect()
            del self.user_clients[user_id]
            logger.info(f"Removed MQTT client for user: {user_id}")

    def get_active_users(self) -> List[Dict[str, Any]]:
        """Get list of users with active MQTT connections"""
        return [
            {
                "user_id": user_id,
                "is_connected": client.is_connected,
                "subscribed_topics": client.subscribed_topics,
                "qos": client.qos,
                "broker": f"{self.broker_host}:{self.broker_port}",
            }
            for user_id, client in self.user_clients.items()
        ]

    def get_connection_count(self) -> int:
        """Get number of active user MQTT connections"""
        return len(self.user_clients)

    def disconnect_all(self):
        """Disconnect all user MQTT clients"""
        logger.info("Disconnecting all user MQTT clients")
        for user_id in list(self.user_clients.keys()):
            self.remove_user_client(user_id)


# Global manager instance
user_mqtt_manager: Optional[UserMQTTClientManager] = None


def get_user_mqtt_manager() -> Optional[UserMQTTClientManager]:
    """Get global user MQTT manager instance"""
    return user_mqtt_manager


def init_user_mqtt_manager(
    broker_host: str,
    broker_port: int,
    username: Optional[str] = None,
    password: Optional[str] = None,
    qos: int = 1,
) -> UserMQTTClientManager:
    """
    Initialize global user MQTT manager
    """
    global user_mqtt_manager
    user_mqtt_manager = UserMQTTClientManager(
        broker_host, broker_port, username, password, qos
    )
    return user_mqtt_manager
