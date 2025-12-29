"""
Async MQTT API router with database storage for sensor data, commands, and device management
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from fastapi.security import OAuth2PasswordBearer

from app.models.mqtt_models import (
    MQTTDevice,
    MQTTSensorReading,
    MQTTCommand,
    MQTTSession,
)
from app.schemas.mqtt_schemas import (
    SensorDataRequest,
    CommandRequest,
    CommandStatusUpdate,
    DeviceCreate,
    DeviceUpdate,
    SessionCreate,
    DeviceListResponse,
    DeviceWithStats,
    SensorReadingListResponse,
    SensorReadingResponse,
    CommandListResponse,
    CommandResponse,
    SessionListResponse,
    SessionResponse,
    MQTTStatsResponse,
    SuccessResponse,
)
from app.managers.db_mqtt_manager import (
    create_or_update_device,
    store_sensor_reading,
    store_command,
    update_command_status,
    create_mqtt_session,
    close_mqtt_session,
    get_device_by_id,
    get_all_devices,
    get_device_readings,
    get_recent_commands,
    get_device_commands,
    get_active_sessions,
)
from app.mqtt.client import get_mqtt_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mqtt", tags=["MQTT"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============= DEVICE ENDPOINTS =============


@router.get("/devices", response_model=DeviceListResponse)
async def get_devices(
    active_only: bool = Query(True, description="Only return active devices"),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all devices with statistics"""
    try:
        devices = await get_all_devices(db, active_only=active_only)
        device_list = []

        for device in devices:
            # Get latest reading
            latest_query = await db.execute(
                select(MQTTSensorReading)
                .where(MQTTSensorReading.device_id == device.id)
                .order_by(MQTTSensorReading.timestamp.desc())
                .limit(1)
            )
            latest = latest_query.scalars().first()

            # Get reading count
            count_query = await db.execute(
                select(func.count(MQTTSensorReading.id)).where(
                    MQTTSensorReading.device_id == device.id
                )
            )
            reading_count = count_query.scalar()

            # Get command count
            cmd_count_query = await db.execute(
                select(func.count(MQTTCommand.id)).where(
                    MQTTCommand.device_id == device.id
                )
            )
            command_count = cmd_count_query.scalar()

            device_dict = device.to_dict(include_relationships=False)
            device_dict["sensor_readings_count"] = reading_count or 0
            device_dict["commands_count"] = command_count or 0
            device_dict["latest_reading"] = (
                latest.timestamp.isoformat() if latest else None
            )

            device_list.append(DeviceWithStats(**device_dict))

        return DeviceListResponse(devices=device_list, count=len(device_list))

    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get devices: {str(e)}")


@router.get("/devices/{device_id}", response_model=DeviceWithStats)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific device by ID"""
    try:
        device = await get_device_by_id(db, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Get statistics
        reading_count = (
            await db.execute(
                select(func.count(MQTTSensorReading.id)).where(
                    MQTTSensorReading.device_id == device.id
                )
            )
        ).scalar()

        command_count = (
            await db.execute(
                select(func.count(MQTTCommand.id)).where(
                    MQTTCommand.device_id == device.id
                )
            )
        ).scalar()

        latest_query = await db.execute(
            select(MQTTSensorReading)
            .where(MQTTSensorReading.device_id == device.id)
            .order_by(MQTTSensorReading.timestamp.desc())
            .limit(1)
        )
        latest = latest_query.scalars().first()

        device_dict = device.to_dict(include_relationships=False)
        device_dict["sensor_readings_count"] = reading_count or 0
        device_dict["commands_count"] = command_count or 0
        device_dict["latest_reading"] = latest.timestamp.isoformat() if latest else None

        return DeviceWithStats(**device_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device: {str(e)}")


@router.post("/devices", response_model=SuccessResponse)
async def create_device(device: DeviceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new device"""
    try:
        # Check if device already exists
        existing = await get_device_by_id(db, device.device_id)
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Device {device.device_id} already exists"
            )

        device_data = device.model_dump()
        new_device = await create_or_update_device(db, device.device_id, device_data)
        await db.commit()

        return SuccessResponse(
            message="Device created successfully",
            data=new_device.to_dict(include_relationships=False),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating device: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create device: {str(e)}"
        )


@router.patch("/devices/{device_id}", response_model=SuccessResponse)
async def update_device(
    device_id: str, update: DeviceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update device information"""
    try:
        device = await get_device_by_id(db, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        update_data = update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(device, key, value)

        await db.commit()
        await db.refresh(device)

        return SuccessResponse(
            message="Device updated successfully",
            data=device.to_dict(include_relationships=False),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating device: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update device: {str(e)}"
        )


# ============= SENSOR READING ENDPOINTS =============


@router.get("/readings", response_model=SensorReadingListResponse)
async def get_latest_readings(
    limit: int = Query(20, ge=1, le=1000, description="Number of readings to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get latest sensor readings across all devices"""
    try:
        result = await db.execute(
            select(MQTTSensorReading)
            .order_by(MQTTSensorReading.timestamp.desc())
            .limit(limit)
        )
        readings = result.scalars().all()

        return SensorReadingListResponse(
            readings=[
                SensorReadingResponse(**r.to_dict(include_relationships=True))
                for r in readings
            ],
            count=len(readings),
        )

    except Exception as e:
        logger.error(f"Error getting latest readings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get latest readings: {str(e)}"
        )


@router.get("/devices/{device_id}/readings", response_model=SensorReadingListResponse)
async def get_device_sensor_readings(
    device_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of readings to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get sensor readings for a specific device"""
    try:
        readings = await get_device_readings(db, device_id, limit=limit)

        return SensorReadingListResponse(
            readings=[
                SensorReadingResponse(**r.to_dict(include_relationships=True))
                for r in readings
            ],
            count=len(readings),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device readings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get device readings: {str(e)}"
        )


@router.post("/readings", response_model=SuccessResponse)
async def publish_sensor_reading(
    data: SensorDataRequest, db: AsyncSession = Depends(get_db)
):
    """Publish a sensor reading (stores in DB and publishes to MQTT)"""
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        timestamp = (
            datetime.fromisoformat(data.timestamp.replace("Z", "+00:00"))
            if data.timestamp
            else datetime.now(timezone.utc)
        )

        # Store in database
        reading = await store_sensor_reading(
            db=db,
            device_id=data.device_id,
            sensor_id=data.sensor_id,
            sensor_type_id=data.sensor_type_id,
            value=data.value,
            unit=data.unit,
            topic=f"sf/sensors/{data.device_id}",
            user_id=data.user_id,
            raw_data=data.model_dump(),
            qos=data.qos,
            retain=data.retain,
            timestamp=timestamp,
        )
        await db.commit()

        # Publish to MQTT
        mqtt_payload = {
            "device_id": data.device_id,
            "sensor_id": data.sensor_id,
            "sensor_type_id": data.sensor_type_id,
            "value": data.value,
            "unit": data.unit,
            "timestamp": timestamp.isoformat(),
        }
        mqtt.publish(
            f"sf/sensors/{data.device_id}",
            mqtt_payload,
            qos=data.qos,
            retain=data.retain,
        )

        return SuccessResponse(
            message="Sensor reading published and stored successfully",
            data=reading.to_dict(include_relationships=True),
        )

    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error publishing sensor reading: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to publish sensor reading: {str(e)}"
        )


# ============= COMMAND ENDPOINTS =============


@router.get("/commands", response_model=CommandListResponse)
async def get_commands(
    limit: int = Query(50, ge=1, le=500, description="Number of commands to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent commands across all devices"""
    try:
        commands = await get_recent_commands(db, limit=limit)

        return CommandListResponse(
            commands=[
                CommandResponse(**c.to_dict(include_relationships=True))
                for c in commands
            ],
            count=len(commands),
        )

    except Exception as e:
        logger.error(f"Error getting commands: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get commands: {str(e)}")


@router.get("/devices/{device_id}/commands", response_model=CommandListResponse)
async def get_device_command_history(
    device_id: str,
    limit: int = Query(50, ge=1, le=500, description="Number of commands to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get command history for a specific device"""
    try:
        commands = await get_device_commands(db, device_id, limit=limit)

        return CommandListResponse(
            commands=[
                CommandResponse(**c.to_dict(include_relationships=True))
                for c in commands
            ],
            count=len(commands),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device commands: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get device commands: {str(e)}"
        )


@router.post("/commands", response_model=SuccessResponse)
async def send_device_command(
    command: CommandRequest, db: AsyncSession = Depends(get_db)
):
    """Send a command to a device (stores in DB and publishes to MQTT)"""
    mqtt = get_mqtt_client()
    if mqtt is None:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        topic = f"sf/commands/{command.device_id}"

        # Store command in database
        cmd = await store_command(
            db=db,
            device_id=command.device_id,
            command=command.command,
            parameters=command.parameters or {},
            topic=topic,
            user_id=command.user_id,
            qos=command.qos,
            retain=command.retain,
        )
        await db.commit()

        # Publish to MQTT
        mqtt_payload = {
            "command": command.command,
            "parameters": command.parameters or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mqtt.publish(topic, mqtt_payload, qos=command.qos, retain=command.retain)

        return SuccessResponse(
            message="Command sent and stored successfully",
            data=cmd.to_dict(include_relationships=True),
        )

    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error sending command: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.patch("/commands/{command_id}", response_model=SuccessResponse)
async def update_command(
    command_id: int, update: CommandStatusUpdate, db: AsyncSession = Depends(get_db)
):
    """Update command status"""
    try:
        cmd = await update_command_status(
            db=db,
            command_id=command_id,
            status=update.status,
            response_data=update.response_data,
            error_message=update.error_message,
        )
        await db.commit()

        return SuccessResponse(
            message="Command status updated successfully",
            data=cmd.to_dict(include_relationships=True),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating command: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update command: {str(e)}"
        )


# ============= SESSION ENDPOINTS =============


@router.get("/sessions", response_model=SessionListResponse)
async def get_mqtt_sessions(
    active_only: bool = Query(True, description="Only return active sessions"),
    db: AsyncSession = Depends(get_db),
):
    """Get MQTT sessions"""
    try:
        if active_only:
            sessions = await get_active_sessions(db)
        else:
            result = await db.execute(select(MQTTSession))
            sessions = result.scalars().all()

        return SessionListResponse(
            sessions=[
                SessionResponse(**s.to_dict(include_relationships=True))
                for s in sessions
            ],
            count=len(sessions),
        )

    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@router.post("/sessions", response_model=SuccessResponse)
async def create_session(session: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new MQTT session"""
    try:
        new_session = await create_mqtt_session(
            db=db,
            user_id=session.user_id,
            client_id=session.client_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            subscribed_topics=session.subscribed_topics,
            connection_metadata=session.connection_metadata,
        )
        await db.commit()

        return SuccessResponse(
            message="Session created successfully",
            data=new_session.to_dict(include_relationships=True),
        )

    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def close_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Close an MQTT session"""
    try:
        session = await close_mqtt_session(db, session_id=session_id)
        await db.commit()

        return SuccessResponse(
            message="Session closed successfully",
            data=session.to_dict(include_relationships=True),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error closing session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to close session: {str(e)}"
        )


# ============= STATISTICS ENDPOINTS =============


@router.get("/stats", response_model=MQTTStatsResponse)
async def get_mqtt_statistics(db: AsyncSession = Depends(get_db)):
    """Get MQTT system statistics"""
    try:
        # Device counts
        total_devices = (
            await db.execute(select(func.count()).select_from(MQTTDevice))
        ).scalar()

        active_devices = (
            await db.execute(select(func.count()).where(MQTTDevice.is_active == True))
        ).scalar()

        # Reading counts
        total_readings = (
            await db.execute(select(func.count()).select_from(MQTTSensorReading))
        ).scalar()

        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        readings_24h = (
            await db.execute(
                select(func.count()).where(MQTTSensorReading.timestamp >= since_24h)
            )
        ).scalar()

        # Command counts
        total_commands = (
            await db.execute(select(func.count()).select_from(MQTTCommand))
        ).scalar()

        commands_24h = (
            await db.execute(
                select(func.count()).where(MQTTCommand.sent_at >= since_24h)
            )
        ).scalar()

        # Active sessions
        active_sessions = (
            await db.execute(select(func.count()).where(MQTTSession.is_active == True))
        ).scalar()

        # Most active devices
        result = await db.execute(
            select(
                MQTTDevice.device_id,
                MQTTDevice.device_name,
                func.count(MQTTSensorReading.id).label("reading_count"),
            )
            .join(MQTTSensorReading)
            .group_by(MQTTDevice.device_id, MQTTDevice.device_name)
            .order_by(func.count(MQTTSensorReading.id).desc())
            .limit(5)
        )

        most_active = [
            {"device_id": d, "device_name": n, "readings": c}
            for d, n, c in result.all()
        ]

        return MQTTStatsResponse(
            total_devices=total_devices or 0,
            active_devices=active_devices or 0,
            total_readings=total_readings or 0,
            total_commands=total_commands or 0,
            readings_24h=readings_24h or 0,
            commands_24h=commands_24h or 0,
            active_sessions=active_sessions or 0,
            most_active_devices=most_active,
        )

    except Exception as e:
        logger.error(f"Error getting MQTT statistics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get MQTT statistics: {str(e)}"
        )


# ============= CREDENTIALS ENDPOINT =============


@router.get("/credentials")
async def get_mqtt_credentials(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Get MQTT credentials for the current authenticated user"""

    from app.routes.auth_router import get_current_user
    from app.security.mqtt_credentials import MQTTCredentialManager
    from app.config import settings

    # Get current user
    current_user = await get_current_user(token, db)
    try:
        mqtt_username, mqtt_password = (
            await MQTTCredentialManager.get_or_create_mqtt_credentials(
                current_user.username, db
            )
        )
        return {
            "mqtt_username": mqtt_username,
            "mqtt_password": mqtt_password,
            "mqtt_broker_host": settings.MQTT_BROKER_HOST,
            "mqtt_broker_port": settings.MQTT_BROKER_PORT,
            "mqtt_tls_enabled": settings.MQTT_TLS_ENABLED,
            "mqtt_ws_port": 8083,  # WebSocket port if needed
        }

    except ValueError as e:
        logger.error(f"Error getting MQTT credentials: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting MQTT credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get MQTT credentials: {str(e)}"
        )
