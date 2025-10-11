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
from app.routes import iot

# Import both WebSocket route modules
try:
    from app.routes import websocket_per_user
    PER_USER_MQTT_AVAILABLE = True
    print("✅ Per-user MQTT routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import per-user MQTT routes: {e}")
    PER_USER_MQTT_AVAILABLE = False
    websocket_per_user = None

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
    
    # Initialize shared MQTT client (for system/broadcast)
    ws_manager = get_websocket_manager()
    try:
        mqtt = init_mqtt_client(
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password
        )
        mqtt.set_websocket_manager(ws_manager)
        mqtt.connect()
        mqtt.subscribe(f"{settings.mqtt_topic_prefix}/sensors/#", iot.handle_sensor_message)
        logger.info("Shared MQTT client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize shared MQTT client: {e}")
    
    # Initialize per-user MQTT manager
    if PER_USER_MQTT_AVAILABLE:
        try:
            user_mqtt_mgr = init_user_mqtt_manager(
                broker_host=settings.mqtt_broker_host,
                broker_port=settings.mqtt_broker_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password
            )
            user_mqtt_mgr.set_main_loop(main_loop)
            logger.info("Per-user MQTT manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize per-user MQTT manager: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Disconnect shared MQTT client
    mqtt = get_mqtt_client()
    if mqtt is not None:
        mqtt.disconnect()
    
    # Disconnect all user MQTT clients
    if PER_USER_MQTT_AVAILABLE:
        user_mqtt_mgr = get_user_mqtt_manager()
        if user_mqtt_mgr:
            user_mqtt_mgr.disconnect_all()
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Smart Factory API",
    description="Backend API with per-user MQTT sessions and WebSocket support",
    version="2.0.0",
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

# Root endpoint
@app.get("/")
async def root():
    user_mqtt_mgr = get_user_mqtt_manager()
    return {
        "message": "Smart Factory API is running",
        "status": "healthy",
        "mqtt_connected": get_mqtt_client() is not None,
        "per_user_mqtt_enabled": PER_USER_MQTT_AVAILABLE,
        "active_user_sessions": user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0
    }

@app.get("/api/health")
async def health_check():
    mqtt = get_mqtt_client()
    user_mqtt_mgr = get_user_mqtt_manager()
    
    return {
        "status": "ok",
        "service": "Smart Factory Backend",
        "mqtt_status": "connected" if mqtt is not None else "disconnected",
        "per_user_mqtt_enabled": PER_USER_MQTT_AVAILABLE,
        "active_user_sessions": user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0
    }

@app.get("/api/users")
async def get_active_users():
    """Get list of users with active MQTT sessions"""
    user_mqtt_mgr = get_user_mqtt_manager()
    if not user_mqtt_mgr:
        return {"users": [], "count": 0}
    
    return {
        "users": user_mqtt_mgr.get_active_users(),
        "count": user_mqtt_mgr.get_connection_count()
    }

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )