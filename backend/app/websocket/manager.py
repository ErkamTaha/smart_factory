from fastapi import WebSocket
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # Store active WebSocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Send message to a specific WebSocket connection"""
        try:
            if user_id in self.active_connections:
                websocket = self.active_connections[user_id]
            # Convert to JSON string if it's a dictionary
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)
            await websocket.send_json(message_str)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Remove broken connection
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected WebSocket clients"""
        if not self.active_connections:
            logger.warning("No connections")
            return

        # Convert to JSON string if needed
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = str(message)

        # Send to all connections, remove broken ones
        broken_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                broken_connections.append(connection)

        # Clean up broken connections
        for broken_connection in broken_connections:
            self.disconnect(broken_connection)

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
