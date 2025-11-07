from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.mqtt.client import get_mqtt_client

router = APIRouter(prefix="/api/iot", tags=["IoT"])

# In-memory storage for demo (replace with database later)
sensor_data_store: Dict[str, list] = {}


class SensorData(BaseModel):
    device_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: Optional[str] = None


class CommandPayload(BaseModel):
    device_id: str
    command: str
    parameters: Optional[Dict[str, Any]] = None


@router.get("/devices")
async def get_devices():
    """Get list of all devices that have sent data"""
    devices = list(
        set(
            [
                reading["device_id"]
                for readings in sensor_data_store.values()
                for reading in readings
            ]
        )
    )
    return {"devices": devices, "count": len(devices)}


@router.get("/data/{device_id}")
async def get_device_data(device_id: str, limit: int = 10):
    """Get sensor data for a specific device"""
    device_data = []
    for sensor_readings in sensor_data_store.values():
        device_data.extend(
            [
                reading
                for reading in sensor_readings
                if reading["device_id"] == device_id
            ]
        )

    # Sort by timestamp and limit
    device_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {
        "device_id": device_id,
        "data": device_data[:limit],
        "count": len(device_data),
    }


@router.post("/data")
async def publish_sensor_data(data: SensorData):
    """Publish sensor data via MQTT"""
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    # Add timestamp if not provided
    if not data.timestamp:
        data.timestamp = datetime.utcnow().isoformat()

    # Store locally
    sensor_key = f"{data.device_id}_{data.sensor_type}"
    if sensor_key not in sensor_data_store:
        sensor_data_store[sensor_key] = []

    sensor_data_store[sensor_key].append(data.dict())

    # Publish to MQTT
    topic = f"sf/sensors/{data.device_id}/{data.sensor_type}"
    mqtt.publish(topic, data.dict())

    return {
        "message": "Data published successfully",
        "topic": topic,
        "data": data.dict(),
    }


@router.post("/command")
async def send_command(command: CommandPayload):
    """Send command to device via MQTT"""
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    topic = f"sf/commands/{command.device_id}"
    payload = {
        "command": command.command,
        "parameters": command.parameters or {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    mqtt.publish(topic, payload)

    return {"message": "Command sent successfully", "topic": topic, "payload": payload}


@router.get("/latest")
async def get_latest_data(limit: int = 20):
    """Get latest sensor readings from all devices"""
    all_data = []
    for readings in sensor_data_store.values():
        all_data.extend(readings)

    # Sort by timestamp
    all_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {"data": all_data[:limit], "total": len(all_data)}


# Callback function for MQTT messages
def handle_sensor_message(topic: str, data: dict):
    """Handle incoming sensor data from MQTT"""
    print(f"Received sensor data: {topic} -> {data}")

    # Parse topic to extract device_id and sensor_type
    parts = topic.split("/")
    if len(parts) >= 4:
        device_id = parts[-2]
        sensor_type = parts[-1]

        # Store the data
        sensor_key = f"{device_id}_{sensor_type}"
        if sensor_key not in sensor_data_store:
            sensor_data_store[sensor_key] = []

        if isinstance(data, dict):
            data["device_id"] = device_id
            data["sensor_type"] = sensor_type
            if "timestamp" not in data:
                data["timestamp"] = datetime.utcnow().isoformat()
            sensor_data_store[sensor_key].append(data)
