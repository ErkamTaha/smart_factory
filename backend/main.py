from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.config import settings
from app.mqtt.client import init_mqtt_client, get_mqtt_client
from app.routes import iot

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
    
    # Initialize MQTT client
    try:
        mqtt = init_mqtt_client(
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password
        )
        mqtt.connect()
        
        # Subscribe to sensor topics
        mqtt.subscribe(f"{settings.mqtt_topic_prefix}/sensors/#", 
                      iot.handle_sensor_message)
        
        logger.info("MQTT client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {e}")
        logger.warning("Application will run without MQTT functionality")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    mqtt = get_mqtt_client()
    if mqtt is not None:
        mqtt.disconnect()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Smart Factory API",
    description="Backend API for Smart Factory application with MQTT support",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Ionic app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(iot.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Smart Factory API is running",
        "status": "healthy",
        "mqtt_connected": get_mqtt_client() is not None
    }

@app.get("/api/health")
async def health_check():
    mqtt = get_mqtt_client()
    return {
        "status": "ok",
        "service": "Smart Factory Backend",
        "mqtt_status": "connected" if mqtt is not None else "disconnected"
    }

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )