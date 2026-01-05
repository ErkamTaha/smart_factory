"""
Smart Factory Backend - Main Application Entry Point
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import asyncio
import os
from pathlib import Path

from app.database.database import init_database, test_connection
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.mqtt.emqx_auth import init_emqx_auth_manager, get_emqx_auth_manager
from app.mqtt.client import init_mqtt_client, get_mqtt_client
from app.mqtt.user_client import init_user_mqtt_manager, get_user_mqtt_manager
from app.websocket.manager import get_websocket_manager
from app.managers.db_acl_manager import init_acl_manager, get_acl_manager
from app.managers.db_ss_manager import init_ss_manager, get_ss_manager
from app.managers.db_auth_manager import init_auth_manager, get_auth_manager
from app.routes import websocket_router
from app.config import settings
from app.routes import acl_router, mqtt_router, ss_router, auth_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Test database connection
    if not await test_connection():
        logger.error("❌ Failed to connect to database")
        raise Exception("Database connection failed")

    # Initialize database
    try:
        await init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    # Get main event loop
    main_loop = asyncio.get_running_loop()

    # Initialize Auth Manager
    try:
        auth_mgr = init_auth_manager()
        logger.info("✅ Authentication manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Auth manager: {e}")

    # Initialize ACL Manager
    try:
        acl_mgr = await init_acl_manager()
        logger.info("✅ Database-backed ACL manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize ACL manager: {e}")

    # Initialize SS Manager
    try:
        ss_mgr = await init_ss_manager()
        logger.info("✅ Database-backed SS manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize SS manager: {e}")

    # Initialize MQTT clients
    ws_manager = get_websocket_manager()
    try:
        mqtt = init_mqtt_client(
            broker_host=settings.MQTT_BROKER_HOST,
            broker_port=settings.MQTT_BROKER_PORT,
            username=settings.MQTT_USERNAME,
            password=settings.MQTT_PASSWORD,
            qos=1,
            tls_enabled=settings.MQTT_TLS_ENABLED,
            ca_certs=settings.MQTT_CA_CERTS if settings.MQTT_CA_CERTS else None,
        )
        mqtt.set_websocket_manager(ws_manager)
        mqtt.connect()
        logger.info("✅ Shared MQTT client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MQTT client: {e}")

    # Initialize per-user MQTT manager
    try:
        user_mqtt_mgr = init_user_mqtt_manager(
            broker_host=settings.MQTT_BROKER_HOST,
            broker_port=settings.MQTT_BROKER_PORT,
            username=settings.MQTT_USERNAME,
            password=settings.MQTT_PASSWORD,
            qos=1,
            tls_enabled=settings.MQTT_TLS_ENABLED,
            ca_certs=settings.MQTT_CA_CERTS if settings.MQTT_CA_CERTS else None,
        )
        user_mqtt_mgr.set_main_loop(main_loop)
        logger.info("✅ Per-user MQTT manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize per-user MQTT manager: {e}")

    # Initialize EMQX Auth Manager
    try:
        logger.info("🔐 Initializing EMQX Auth Manager...")
        emqx_auth = init_emqx_auth_manager(
            api_url=settings.EMQX_API_URL,
            api_key=settings.EMQX_API_KEY,
            api_secret=settings.EMQX_API_SECRET,
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize EMQX Auth manager: {e}")

    # Verify EMQX connection
    if await emqx_auth.verify_connection():
        logger.info("✅ EMQX API connected successfully")
    else:
        logger.warning("⚠️  EMQX API connection failed - MQTT auth may not work")

    logger.info("🎉 Smart Factory Backend started successfully!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Smart Factory Backend...")

    mqtt = get_mqtt_client()
    if mqtt:
        mqtt.disconnect()
        logger.info("✅ MQTT client disconnected")

    user_mqtt_mgr = get_user_mqtt_manager()
    if user_mqtt_mgr:
        user_mqtt_mgr.disconnect_all()
        logger.info("✅ User MQTT clients disconnected")

    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Smart Factory API",
    description="Backend API with PostgreSQL, MQTT, WebSocket, ACL, and Sensor Security",
    version="3.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router)
app.include_router(mqtt_router.router)
app.include_router(websocket_router.router, prefix="/ws")
app.include_router(acl_router.router)
app.include_router(ss_router.router)


@app.get("/")
async def root():
    """Root endpoint with system status"""
    user_mqtt_mgr = get_user_mqtt_manager()
    acl_mgr = get_acl_manager()
    ss_mgr = get_ss_manager()
    mqtt = get_mqtt_client()
    emqx = get_emqx_auth_manager()

    return {
        "message": "Smart Factory API is running! 🏭",
        "status": "healthy",
        "version": "3.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "storage": "postgresql",
        "features": {
            "emqx_api": await emqx.verify_connection(),
            "mqtt_connected": mqtt is not None,
            "mqtt_qos": mqtt.qos if mqtt else None,
            "acl_enabled": acl_mgr is not None,
            "ss_enabled": ss_mgr is not None,
            "active_user_sessions": (
                user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0
            ),
            "database_storage": True,
            "websocket_support": True,
            "audit_logging": True,
        },
    }


@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check endpoint"""
    db_healthy = await test_connection()
    mqtt = get_mqtt_client()
    emqx_auth = get_emqx_auth_manager()
    user_mqtt_mgr = get_user_mqtt_manager()
    acl_mgr = get_acl_manager()
    ss_mgr = get_ss_manager()

    return {
        "status": "ok" if db_healthy else "error",
        "service": "Smart Factory Backend",
        "version": "3.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "mqtt": "connected" if mqtt else "disconnected",
            "emqx": (
                "connected" if await emqx_auth.verify_connection() else "disconnected"
            ),
            "acl": "enabled" if acl_mgr else "disabled",
            "ss": "enabled" if ss_mgr else "disabled",
            "user_sessions": (
                user_mqtt_mgr.get_connection_count() if user_mqtt_mgr else 0
            ),
        },
        "details": {
            "acl_info": await acl_mgr.get_acl_info(db) if acl_mgr else None,
            "ss_info": await ss_mgr.get_ss_info(db) if ss_mgr else None,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
