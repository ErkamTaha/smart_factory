from fastapi import WebSocket
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # Store active WebSocket connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept(subprotocol="access_token")
        self.active_connections[user_id] = websocket
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(
                f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Send message to a specific WebSocket connection"""
        try:
            if user_id not in self.active_connections:
                logger.warning(f"User {user_id} not connected")
                return

            websocket = self.active_connections[user_id]
            # Convert to JSON string if it's a dictionary
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)
            await websocket.send_text(message_str)
        except Exception as e:
            logger.error(f"Error sending personal message to user {user_id}: {e}")
            # Remove broken connection
            self.disconnect(user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected WebSocket clients"""
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        # Convert to JSON string if needed
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = str(message)

        # Send to all connections, remove broken ones
        broken_user_ids = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                broken_user_ids.append(user_id)

        # Clean up broken connections
        for broken_user_id in broken_user_ids:
            self.disconnect(broken_user_id)

    async def broadcast_sensor_data(
        self, topic: str, data: Dict[str, Any], qos, retain
    ):
        """Broadcast sensor data to all connected clients"""
        message = {
            "type": "sensor_data",
            "topic": topic,
            "data": data,
            "qos": qos,
            "retain": retain,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast(message)

    async def broadcast_device_status(
        self, device_id: str, status: str, details: Optional[Dict[str, Any]] = None
    ):
        """Broadcast device status updates"""
        message = {
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast(message)

    async def broadcast_system_alert(
        self, level: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        """Broadcast system alerts and notifications"""
        alert_message = {
            "type": "system_alert",
            "level": level,  # info, warning, error, critical
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast(alert_message)

    def get_connection_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self.active_connections)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance"""
    return websocket_manager
