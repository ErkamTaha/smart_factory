"""
Async IoT service with database storage for sensor data
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from app.models.mqtt_models import (
    MQTTDevice,
    MQTTSensorReading,
    MQTTCommand,
    store_sensor_reading,
    store_command,
    create_or_update_device,
)

from app.mqtt.client import get_mqtt_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/iot", tags=["IoT"])


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# GET DEVICES
# ---------------------------------------------------------


@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db)):
    """Get list of all devices that have sent data"""
    try:
        result = await db.execute(
            select(MQTTDevice).where(MQTTDevice.is_active == True)
        )
        devices = result.scalars().all()

        device_list = []

        for device in devices:
            # Latest reading
            latest_query = await db.execute(
                select(MQTTSensorReading)
                .where(MQTTSensorReading.device_id == device.id)
                .order_by(MQTTSensorReading.timestamp.desc())
                .limit(1)
            )
            latest = latest_query.scalars().first()

            # Sensor count
            count_query = await db.execute(
                select(func.count(MQTTSensorReading.id)).where(
                    MQTTSensorReading.device_id == device.id
                )
            )
            sensor_count = count_query.scalar()

            d = device.to_dict()
            d["latest_reading"] = latest.timestamp.isoformat() if latest else None
            d["sensor_count"] = sensor_count

            device_list.append(d)

        return {"devices": device_list, "count": len(device_list)}

    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to get devices")


# ---------------------------------------------------------
# GET DATA FOR A DEVICE
# ---------------------------------------------------------


@router.get("/data/{device_id}")
async def get_device_data(
    device_id: str, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    try:
        device_query = await db.execute(
            select(MQTTDevice).where(MQTTDevice.device_id == device_id)
        )
        device = device_query.scalars().first()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        readings_query = await db.execute(
            select(MQTTSensorReading)
            .where(MQTTSensorReading.device_id == device.id)
            .order_by(MQTTSensorReading.timestamp.desc())
            .limit(limit)
        )

        readings = readings_query.scalars().all()

        return {
            "device_id": device_id,
            "data": [r.to_dict() for r in readings],
            "count": len(readings),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device data")


# ---------------------------------------------------------
# PUBLISH SENSOR DATA
# ---------------------------------------------------------


@router.post("/data")
async def publish_sensor_data(data: SensorData, db: AsyncSession = Depends(get_db)):
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        timestamp = (
            datetime.fromisoformat(data.timestamp.replace("Z", "+00:00"))
            if data.timestamp
            else datetime.now(timezone.utc)
        )

        data_dict = {
            "device_id": data.device_id,
            "sensor_type": data.sensor_type,
            "value": data.value,
            "unit": data.unit,
            "timestamp": timestamp.isoformat(),
        }

        # Store in DB
        reading = await store_sensor_reading(
            db=db,
            device_id=data.device_id,
            sensor_type=data.sensor_type,
            value=data.value,
            unit=data.unit,
            topic=f"sf/sensors/{data.device_id}/{data.sensor_type}",
            user_id="api_user",
            raw_data=data_dict,
            timestamp=timestamp,
        )
        await db.commit()

        # Publish to MQTT
        mqtt.publish(f"sf/sensors/{data.device_id}/{data.sensor_type}", data_dict)

        return {
            "message": "Data published and stored successfully",
            "data": data_dict,
            "reading_id": reading.id,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error publishing sensor data: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish sensor data")


# ---------------------------------------------------------
# SEND COMMAND
# ---------------------------------------------------------


@router.post("/command")
async def send_command(command: CommandPayload, db: AsyncSession = Depends(get_db)):
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        topic = f"sf/commands/{command.device_id}"
        payload = {
            "command": command.command,
            "parameters": command.parameters or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        cmd = await store_command(
            db=db,
            device_id=command.device_id,
            command=command.command,
            parameters=command.parameters or {},
            topic=topic,
            user_id="api_user",
        )
        await db.commit()

        mqtt.publish(topic, payload)

        return {
            "message": "Command sent and stored successfully",
            "topic": topic,
            "payload": payload,
            "command_id": cmd.id,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error sending command: {e}")
        raise HTTPException(status_code=500, detail="Failed to send command")


# ---------------------------------------------------------
# LATEST READINGS
# ---------------------------------------------------------


@router.get("/latest")
async def get_latest_data(limit: int = 20, db: AsyncSession = Depends(get_db)):
    try:
        q = await db.execute(
            select(MQTTSensorReading)
            .order_by(MQTTSensorReading.timestamp.desc())
            .limit(limit)
        )
        readings = q.scalars().all()

        return {"data": [r.to_dict() for r in readings], "total": len(readings)}

    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get latest data")


# ---------------------------------------------------------
# SENSOR TYPE DATA
# ---------------------------------------------------------


@router.get("/sensors/{sensor_type}")
async def get_sensor_type_data(
    sensor_type: str, hours: int = 24, db: AsyncSession = Depends(get_db)
):
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        q = await db.execute(
            select(MQTTSensorReading)
            .where(
                MQTTSensorReading.sensor_type == sensor_type,
                MQTTSensorReading.timestamp >= since,
            )
            .order_by(MQTTSensorReading.timestamp.desc())
        )

        readings = q.scalars().all()

        return {
            "sensor_type": sensor_type,
            "hours": hours,
            "data": [r.to_dict() for r in readings],
            "count": len(readings),
        }

    except Exception as e:
        logger.error(f"Error getting sensor type data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sensor type data")


# ---------------------------------------------------------
# RECENT COMMANDS
# ---------------------------------------------------------


@router.get("/commands")
async def get_recent_commands(limit: int = 50, db: AsyncSession = Depends(get_db)):
    try:
        q = await db.execute(
            select(MQTTCommand).order_by(MQTTCommand.sent_at.desc()).limit(limit)
        )

        cmds = q.scalars().all()

        return {"commands": [c.to_dict() for c in cmds], "count": len(cmds)}

    except Exception as e:
        logger.error(f"Error getting commands: {e}")
        raise HTTPException(status_code=500, detail="Failed to get commands")


# ---------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------


@router.get("/stats")
async def get_iot_stats(db: AsyncSession = Depends(get_db)):
    try:
        # Counts
        device_count = (
            await db.execute(
                select(func.count()).select_from(
                    select(MQTTDevice).where(MQTTDevice.is_active == True).subquery()
                )
            )
        ).scalar()

        reading_count = (
            await db.execute(select(func.count()).select_from(MQTTSensorReading))
        ).scalar()

        command_count = (
            await db.execute(select(func.count()).select_from(MQTTCommand))
        ).scalar()

        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

        recent_readings = (
            await db.execute(
                select(func.count()).where(MQTTSensorReading.timestamp >= since_24h)
            )
        ).scalar()

        # Most active devices
        q = await db.execute(
            select(
                MQTTDevice.device_id,
                func.count(MQTTSensorReading.id).label("reading_count"),
            )
            .join(MQTTSensorReading)
            .group_by(MQTTDevice.device_id)
            .order_by(func.count(MQTTSensorReading.id).desc())
            .limit(5)
        )

        most_active = [{"device_id": d, "readings": c} for d, c in q.all()]

        return {
            "total_devices": device_count,
            "total_readings": reading_count,
            "total_commands": command_count,
            "readings_24h": recent_readings,
            "most_active_devices": most_active,
        }

    except Exception as e:
        logger.error(f"Error getting IoT stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get IoT statistics")


# ---------------------------------------------------------
# ASYNC MQTT CALLBACK HANDLER
# ---------------------------------------------------------


async def handle_sensor_message(topic: str, data: dict, user_id: str = None):
    """Handle incoming sensor data from MQTT and store in database (async safe)"""
    logger.info(f"Received sensor data: {topic} -> {data}")

    try:
        parts = topic.split("/")
        if len(parts) >= 3:
            # For topics like "sf/sensors/test_device_001" or "sf/sensors/test_device_001/temperature"
            # The sensor ID should be the 3rd part (index 2)
            if len(parts) >= 3 and parts[0] == "sf" and parts[1] == "sensors":
                device_id = parts[2]  # Extract device ID from sf/sensors/DEVICE_ID/...
                sensor_type = parts[3]
            else:
                device_id = parts[-1]  # Fallback to last part
                sensor_type = ""

        async with get_db() as db:

            if isinstance(data, dict) and "value" in data and "unit" in data:

                timestamp = (
                    datetime.fromisoformat(data.get("timestamp"))
                    if data.get("timestamp")
                    else datetime.now(timezone.utc)
                )

                await store_sensor_reading(
                    db=db,
                    device_id=device_id,
                    sensor_type=sensor_type,
                    value=float(data["value"]),
                    unit=data["unit"],
                    topic=topic,
                    user_id=user_id or "mqtt_client",
                    raw_data=data,
                    timestamp=timestamp,
                )

                await db.commit()

                logger.info(f"Stored sensor reading: {device_id}/{sensor_type}")

            else:
                logger.warning(f"Incomplete MQTT payload: {data}")

    except Exception as e:
        logger.error(f"Error handling sensor MQTT message: {e}")
