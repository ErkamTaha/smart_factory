from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import asyncio

from app.config import settings
from app.mqtt.client import init_mqtt_client, get_mqtt_client
from app.mqtt.user_client_manager import init_user_mqtt_manager, get_user_mqtt_manager
from app.websocket.manager import get_websocket_manager
from app.security.acl_manager import init_acl_manager, get_acl_manager
from app.routes import iot

# Import WebSocket and ACL routes
try:
    from app.routes import websocket_per_user
    PER_USER_MQTT_AVAILABLE = True
    print("✅ Per-user MQTT routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import per-user MQTT routes: {e}")
    PER_USER_MQTT_AVAILABLE = False
    websocket_per_user = None

try:
    from app.routes import acl
    ACL_ROUTES_AVAILABLE = True
    print("✅ ACL routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ACL routes: {e}")
    ACL_ROUTES_AVAILABLE = False
    acl = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    
    # Get main event loop
    main_loop = asyncio.get_running_loop()
    
    # Initialize ACL Manager
    try:
        acl_mgr = init_acl_manager("acl_config.json")
        logger.info("ACL manager initialized successfully")
        logger.info(f"ACL Info: {acl_mgr.get_acl_info()}")
    except Exception as e:
        logger.error(f"Failed to initialize ACL manager: {e}")
    
    # Initialize shared MQTT client (for system/broadcast)
    ws_manager = get_websocket_manager()
    try:
        # UPDATED: Added QoS parameter
        # QoS 1 is recommended for backend - reliable delivery with possible duplicates
        mqtt = init_mqtt_client(
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            qos=1  # NEW: Default QoS for shared MQTT client
        )
        mqtt.set_websocket_manager(ws_manager)
        mqtt.connect()
        
        # UPDATED: Subscribe with specific QoS based on importance
        # Sensor data - QoS 1 (important but duplicates are OK)
        mqtt.subscribe(
            f"{settings.mqtt_topic_prefix}/sensors/#", 
            iot.handle_sensor_message,
            qos=1  # NEW: Reliable delivery for sensor data
        )
        
        # Optional: Monitor all user status updates
        # Useful for logging user connections/disconnections
        def on_user_status(topic, data):
            user_id = data.get("user_id", "unknown")
            status = data.get("status", "unknown")
            reason = data.get("reason", "")
            
            if status == "offline" and reason == "unexpected_disconnect":
                logger.warning(f"⚠️ User {user_id} disconnected unexpectedly")
            elif status == "online":
                logger.info(f"✓ User {user_id} connected")
            elif status == "offline" and reason == "graceful_disconnect":
                logger.info(f"User {user_id} disconnected gracefully")
        
        mqtt.subscribe("sf/users/+/status", on_user_status, qos=1)
        
        logger.info("Shared MQTT client initialized successfully with QoS 1")
        logger.info("Last Will Testament configured on topic: factory/backend/status")
    except Exception as e:
        logger.error(f"Failed to initialize shared MQTT client: {e}")
    
    # Initialize per-user MQTT manager
    if PER_USER_MQTT_AVAILABLE:
        try:
            # UPDATED: Added QoS parameter
            # QoS 1 is recommended for users - good balance of reliability and performance
            user_mqtt_mgr = init_user_mqtt_manager(
                broker_host=settings.mqtt_broker_host,
                broker_port=settings.mqtt_broker_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                qos=1  # NEW: Default QoS for all user clients
            )
            user_mqtt_mgr.set_main_loop(main_loop)
            logger.info("Per-user MQTT manager initialized successfully with QoS 1")
            logger.info("User Last Will Testament configured on topics: factory/users/{user_id}/status")
        except Exception as e:
            logger.error(f"Failed to initialize per-user MQTT manager: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop ACL file watcher
    acl_mgr = get_acl_manager()
    if acl_mgr:
        acl_mgr.stop_watching()
    
    # Disconnect shared MQTT client
    # UPDATED: Now publishes graceful offline status before disconnecting
    mqtt = get_mqtt_client()
    if mqtt is not None:
        mqtt.disconnect()  # Now includes graceful offline status publish
        logger.info("Shared MQTT client disconnected gracefully")
    
    # Disconnect all user MQTT clients
    # UPDATED: Each user now publishes graceful offline status
    if PER_USER_MQTT_AVAILABLE:
        user_mqtt_mgr = get_user_mqtt_manager()
        if user_mqtt_mgr:
            user_mqtt_mgr.disconnect_all()  # Each user publishes offline status
            logger.info("All user MQTT clients disconnected gracefully")
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Smart Factory API",
    description="Backend API with per-user MQTT sessions, ACL, QoS, and Last Will Testament support",
    version="2.1.0",  # Updated version to reflect new features
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(iot.router)

# Include per-user WebSocket router
if PER_USER_MQTT_AVAILABLE and websocket_per_user is not None:
    app.include_router(websocket_per_user.router, prefix="/ws")
    print("✅ Per-user MQTT WebSocket router included at /ws/ws")
    logger.info("Per-user MQTT WebSocket endpoints available at /ws/ws")
else:
    print("❌ Per-user MQTT WebSocket router not included")
    logger.warning("Per-user MQTT functionality is not available")

# Include ACL management router
if ACL_ROUTES_AVAILABLE and acl is not None:
    app.include_router(acl.router)
    print("✅ ACL management router included at /api/acl")
    logger.info("ACL management endpoints available at /api/acl")
else:
    print("❌ ACL management router not included")

# Root endpoint
@app.get("/")
async def root():
    user_mqtt_mgr = get_user_mqtt_manager()
    acl_mgr = get_acl_manager()
    mqtt = get_mqtt_client()
    
    return {
        "message": "Smart Factory API is running",
        "status": "healthy",
        "mqtt_connected": mqtt is not None,
        "mqtt_qos": mqtt.qos if mqtt else None,  # NEW: Show default QoS
        "per_user_mqtt_enabled": PER_USER_MQTT_AVAILABLE,
        "acl_enabled": acl_mgr is not None,
        "active_user_sessions": user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0,
        "features": {
            "qos_support": True,  # NEW
            "last_will_testament": True,  # NEW
            "status_monitoring": True  # NEW
        }
    }

@app.get("/api/health")
async def health_check():
    mqtt = get_mqtt_client()
    user_mqtt_mgr = get_user_mqtt_manager()
    acl_mgr = get_acl_manager()
    
    return {
        "status": "ok",
        "service": "Smart Factory Backend",
        "mqtt_status": "connected" if mqtt is not None else "disconnected",
        "mqtt_qos": mqtt.qos if mqtt else None,  # NEW: Show QoS level
        "mqtt_lwt_topic": "sf/backend/status",  # NEW: Show LWT topic
        "per_user_mqtt_enabled": PER_USER_MQTT_AVAILABLE,
        "per_user_mqtt_qos": user_mqtt_mgr.qos if user_mqtt_mgr else None,  # NEW
        "acl_enabled": acl_mgr is not None,
        "acl_info": acl_mgr.get_acl_info() if acl_mgr else None,
        "active_user_sessions": user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0
    }

@app.get("/api/users")
async def get_active_users():
    """Get list of users with active MQTT sessions (now includes QoS info)"""
    user_mqtt_mgr = get_user_mqtt_manager()
    if not user_mqtt_mgr:
        return {"users": [], "count": 0}
    
    # UPDATED: get_active_users() now includes QoS for each user
    return {
        "users": user_mqtt_mgr.get_active_users(),  # Now includes "qos" field
        "count": user_mqtt_mgr.get_connection_count()
    }

# NEW ENDPOINT: Monitor status topics
@app.get("/api/status/backend")
async def get_backend_status():
    """Get current backend MQTT status"""
    mqtt = get_mqtt_client()
    if not mqtt:
        return {"status": "not_initialized"}
    
    return {
        "client_id": "smart_factory_backend",
        "connected": mqtt.client.is_connected() if hasattr(mqtt.client, 'is_connected') else True,
        "qos": mqtt.qos,
        "status_topic": "sf/backend/status",
        "lwt_configured": True,
        "broker": f"{mqtt.broker_host}:{mqtt.broker_port}"
    }

# NEW ENDPOINT: Get user status
@app.get("/api/status/users/{user_id}")
async def get_user_status(user_id: str):
    """Get specific user's MQTT status"""
    user_mqtt_mgr = get_user_mqtt_manager()
    if not user_mqtt_mgr:
        return {"error": "Per-user MQTT not available"}
    
    user_client = user_mqtt_mgr.get_user_client(user_id)
    if not user_client:
        return {"error": "User not found", "user_id": user_id}
    
    return {
        "user_id": user_id,
        "connected": user_client.is_connected,
        "qos": user_client.qos,
        "subscribed_topics": user_client.subscribed_topics,
        "status_topic": f"sf/users/{user_id}/status",
        "lwt_configured": True,
        "broker": f"{user_client.broker_host}:{user_client.broker_port}"
    }

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )