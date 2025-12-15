# app/routes/websocket_router.py
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.mqtt.user_client import get_user_mqtt_manager
from app.mqtt.emqx_auth import get_emqx_auth_manager
from app.websocket.manager import get_websocket_manager
from app.security.auth_security import decode_access_token
from app.routes.acl_router import get_user
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """WebSocket endpoint with per-user MQTT connections and EMQX authentication"""

    subprotocol = websocket.headers.get("sec-websocket-protocol")

    if not subprotocol:
        await websocket.close(
            code=1008, reason="Invalid or missing security subprotocol"
        )
        return

    parts = [p.strip() for p in subprotocol.split(",")]
    if len(parts) != 2:
        return await websocket.close(code=1008, reason="Invalid security subprotocol")

    _, token = parts

    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    payload = decode_access_token(token)

    if payload is None:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    # user_id is actually username
    user_id = payload["sub"]

    user = await get_user(user_id, db)

    if user is None:
        await websocket.close(code=1008, reason="User does not exist")
        return

    if not user.is_active:
        await websocket.close(code=1008, reason="User is inactive")
        return

    # Connect with websocket manager
    ws_manager = get_websocket_manager()
    await ws_manager.connect(websocket, user_id)

    mqtt_manager = get_user_mqtt_manager()
    if not mqtt_manager:
        await websocket.close(code=1011, reason="MQTT manager not available")
        return

    # Get or create MQTT credentials for this user (persistent)
    from app.security.mqtt_credentials import MQTTCredentialManager

    try:
        mqtt_username, mqtt_password = (
            await MQTTCredentialManager.get_or_create_mqtt_credentials(user_id, db)
        )
        logger.info(f"Retrieved MQTT credentials for user {user_id}: {mqtt_username}")
    except Exception as e:
        logger.error(f"Failed to get MQTT credentials for user {user_id}: {e}")
        await websocket.close(code=1011, reason="Failed to get MQTT credentials")
        return

    # Create MQTT client for this user with their unique credentials
    try:
        user_mqtt_client = mqtt_manager.create_user_client(
            user_id=user_id,
            websocket=websocket,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
        logger.info(
            f"User {user_id} connected via WebSocket with dedicated MQTT client (username: {mqtt_username})"
        )

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_status",
                    "status": "connected",
                    "user_id": user_id,
                    "mqtt_username": mqtt_username,
                    "message": "WebSocket and MQTT session established",
                    "mqtt_broker": f"{mqtt_manager.broker_host}:{mqtt_manager.broker_port}",
                }
            )
        )

    except Exception as e:
        logger.error(f"Failed to create MQTT client for user {user_id}: {e}")
        await websocket.close(code=1011, reason="Failed to create MQTT session")
        return

    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_user_message(user_id, message, user_mqtt_client, websocket)
            except json.JSONDecodeError:
                logger.warning(f"User {user_id} sent invalid JSON: {data}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Clean up: remove user's MQTT client
        mqtt_manager.remove_user_client(user_id)
        logger.info(f"Cleaned up MQTT session for user {user_id}")

        # Note: We keep MQTT credentials in EMQX for faster reconnection
        # They will be reused on next connection
        logger.info(f"MQTT credentials kept for future reconnection: {mqtt_username}")


async def handle_user_message(
    user_id: str, message: dict, mqtt_client, websocket: WebSocket
):
    """Handle messages from user's WebSocket"""
    message_type = message.get("type")

    if message_type == "ping":
        # Respond to ping
        await websocket.send_text(
            json.dumps(
                {
                    "type": "pong",
                    "timestamp": message.get("timestamp"),
                    "user_id": user_id,
                }
            )
        )

    elif message_type == "subscribe":
        # Subscribe to MQTT topics
        topics = message.get("topics", [])
        qos = message.get("qos")
        for topic in topics:
            mqtt_client.subscribe(topic, qos)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "subscription_ack",
                    "topics": topics,
                    "message": f"Subscribed to {len(topics)} MQTT topics",
                    "current_subscriptions": mqtt_client.subscribed_topics,
                }
            )
        )

    elif message_type == "unsubscribe":
        # Unsubscribe from MQTT topics
        topics = message.get("topics", [])
        for topic in topics:
            mqtt_client.unsubscribe(topic)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "unsubscription_ack",
                    "topics": topics,
                    "message": f"Unsubscribed from {len(topics)} MQTT topics",
                    "current_subscriptions": mqtt_client.subscribed_topics,
                }
            )
        )

    elif message_type == "publish":
        # Publish to MQTT
        topic = message.get("topic")
        payload = message.get("payload")
        retain = message.get("retain")
        qos = message.get("qos")

        if not topic or payload is None:
            await websocket.send_text(
                json.dumps(
                    {"type": "error", "message": "Missing topic or payload for publish"}
                )
            )
            return

        await mqtt_client.publish(topic, payload, qos, retain)

    elif message_type == "get_status":
        # Get user's MQTT status
        manager = get_user_mqtt_manager()
        if manager:
            total_users = manager.get_connection_count()
            broker_info = f"{manager.broker_host}:{manager.broker_port}"
        else:
            total_users = 0
            broker_info = "unknown"

        await websocket.send_text(
            json.dumps(
                {
                    "type": "status",
                    "user_id": user_id,
                    "qos": mqtt_client.qos,
                    "mqtt_connected": mqtt_client.is_connected,
                    "subscribed_topics": mqtt_client.subscribed_topics,
                    "total_users": total_users,
                    "broker": broker_info,
                }
            )
        )

    elif message_type == "get_all_users":
        # Get list of all connected users (admin feature)
        manager = get_user_mqtt_manager()
        if manager:
            active_users = manager.get_active_users()
        else:
            active_users = []

        await websocket.send_text(
            json.dumps(
                {
                    "type": "users_list",
                    "users": active_users,
                    "count": len(active_users),
                }
            )
        )

    elif message_type == "get_system_info":
        # Get system information (ACL and SS info)
        from app.managers.db_acl_manager import get_acl_manager
        from app.managers.db_ss_manager import get_ss_manager

        acl_mgr = get_acl_manager()
        ss_mgr = get_ss_manager()

        system_info = {
            "type": "system_info",
            "acl_info": await acl_mgr.get_acl_info() if acl_mgr else None,
            "ss_info": await ss_mgr.get_ss_info() if ss_mgr else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await websocket.send_text(json.dumps(system_info))

    elif message_type == "reload_acl":
        # Reload ACL configuration
        from app.managers.db_acl_manager import get_acl_manager

        acl_mgr = get_acl_manager()
        if acl_mgr:
            await acl_mgr.reload()
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "system_alert",
                        "level": "info",
                        "message": "ACL configuration reloaded successfully",
                        "details": {"reloaded_by": user_id},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "ACL manager not available"})
            )

    elif message_type == "reload_ss":
        # Reload SS configuration
        from app.managers.db_ss_manager import get_ss_manager

        ss_mgr = get_ss_manager()
        if ss_mgr:
            await ss_mgr.reload()
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "system_alert",
                        "level": "info",
                        "message": "SS configuration reloaded successfully",
                        "details": {"reloaded_by": user_id},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "SS manager not available"})
            )

    else:
        logger.warning(f"Unknown message type from user {user_id}: {message_type}")
        await websocket.send_text(
            json.dumps(
                {"type": "error", "message": f"Unknown message type: {message_type}"}
            )
        )
