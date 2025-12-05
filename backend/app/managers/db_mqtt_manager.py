"""
Database manager for MQTT operations
Helper functions for MQTT device, sensor reading, command, and session management
"""

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from app.models.mqtt_models import (
    MQTTDevice,
    MQTTSensorReading,
    MQTTCommand,
    MQTTSession,
    MQTTTopicStats,
)
from app.models.ss_models import SSSensor, SSSensorType
from app.models.acl_models import ACLUser


async def create_or_update_device(
    db: AsyncSession, device_id: str, device_data: Dict[str, Any] = None
) -> MQTTDevice:
    """Create or update a device, return the device object"""
    results = await db.execute(
        select(MQTTDevice).where(MQTTDevice.device_id == device_id)
    )
    device = results.scalars().first()

    if not device:
        device = MQTTDevice(
            device_id=device_id,
            device_name=(
                device_data.get("name", device_id) if device_data else device_id
            ),
            device_type=(
                device_data.get("type", "unknown") if device_data else "unknown"
            ),
            location=device_data.get("location") if device_data else None,
            description=device_data.get("description") if device_data else None,
            is_active=True,
            last_seen=datetime.now(timezone.utc),
            meta_data=device_data,
        )
        db.add(device)
        await db.flush()
    else:
        device.last_seen = datetime.now(timezone.utc)
        if device_data:
            if "name" in device_data:
                device.device_name = device_data["name"]
            if "type" in device_data:
                device.device_type = device_data["type"]
            if "location" in device_data:
                device.location = device_data["location"]
            if "description" in device_data:
                device.description = device_data["description"]
            device.meta_data = device_data

    return device


async def store_sensor_reading(
    db: AsyncSession,
    device_id: str,
    sensor_id: int,
    sensor_type_id: int,
    value: float,
    unit: str,
    topic: str,
    user_id: int,
    raw_data: Dict[str, Any] = None,
    qos: int = 1,
    retain: bool = False,
    timestamp: datetime = None,
) -> MQTTSensorReading:
    """Store a sensor reading in the database"""

    # Create or update device
    device = await create_or_update_device(db, device_id)

    # Verify sensor exists
    sensor_result = await db.execute(select(SSSensor).where(SSSensor.id == sensor_id))
    sensor = sensor_result.scalars().first()
    if not sensor:
        raise ValueError(f"Sensor with id {sensor_id} not found")

    # Verify sensor type exists
    sensor_type_result = await db.execute(
        select(SSSensorType).where(SSSensorType.id == sensor_type_id)
    )
    sensor_type = sensor_type_result.scalars().first()
    if not sensor_type:
        raise ValueError(f"Sensor type with id {sensor_type_id} not found")

    # Verify user exists
    user_result = await db.execute(select(ACLUser).where(ACLUser.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    # Create sensor reading
    reading = MQTTSensorReading(
        device_id=device.id,
        sensor_id=sensor_id,
        sensor_type=sensor_type_id,
        value=value,
        unit=unit,
        timestamp=timestamp or datetime.now(timezone.utc),
        mqtt_topic=topic,
        qos=qos,
        retain=retain,
        raw_data=raw_data,
        user_id=user_id,
    )

    db.add(reading)
    await db.flush()

    # Optionally eager load relationships for immediate use
    await db.refresh(reading, ["device", "sensor", "sensor_type_obj", "user"])

    return reading


async def store_command(
    db: AsyncSession,
    device_id: str,
    command: str,
    parameters: Dict[str, Any],
    topic: str,
    user_id: int,
    qos: int = 1,
    retain: bool = False,
) -> MQTTCommand:
    """Store a command in the database"""

    # Create or update device
    device = await create_or_update_device(db, device_id)

    # Verify user exists
    user_result = await db.execute(select(ACLUser).where(ACLUser.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    # Create command
    cmd = MQTTCommand(
        device_id=device.id,
        command=command,
        parameters=parameters,
        mqtt_topic=topic,
        qos=qos,
        retain=retain,
        user_id=user_id,
        status="sent",
    )

    db.add(cmd)
    await db.flush()

    # Optionally eager load relationships for immediate use
    await db.refresh(cmd, ["device", "user"])

    return cmd


async def update_command_status(
    db: AsyncSession,
    command_id: int,
    status: str,
    response_data: Dict[str, Any] = None,
    error_message: str = None,
) -> MQTTCommand:
    """Update the status of a command"""
    result = await db.execute(select(MQTTCommand).where(MQTTCommand.id == command_id))
    cmd = result.scalars().first()

    if not cmd:
        raise ValueError(f"Command with id {command_id} not found")

    cmd.status = status

    if status == "acknowledged":
        cmd.acknowledged_at = datetime.now(timezone.utc)
    elif status == "executed":
        cmd.executed_at = datetime.now(timezone.utc)

    if response_data:
        cmd.response_data = response_data

    if error_message:
        cmd.error_message = error_message
        cmd.status = "failed"

    await db.flush()
    return cmd


async def create_mqtt_session(
    db: AsyncSession,
    user_id: int,
    client_id: str,
    ip_address: str = None,
    user_agent: str = None,
    subscribed_topics: List[str] = None,
    connection_metadata: Dict[str, Any] = None,
) -> MQTTSession:
    """Create a new MQTT session"""

    # Verify user exists
    user_result = await db.execute(select(ACLUser).where(ACLUser.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    session = MQTTSession(
        user_id=user_id,
        client_id=client_id,
        is_active=True,
        ip_address=ip_address,
        user_agent=user_agent,
        subscribed_topics=subscribed_topics or [],
        connection_metadata=connection_metadata,
    )

    db.add(session)

    # Update user's last login
    user.last_login = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(session, ["user"])
    return session


async def close_mqtt_session(
    db: AsyncSession,
    session_id: int = None,
    client_id: str = None,
) -> MQTTSession:
    """Close an MQTT session by ID or client_id"""

    if session_id:
        result = await db.execute(
            select(MQTTSession).where(MQTTSession.id == session_id)
        )
    elif client_id:
        result = await db.execute(
            select(MQTTSession).where(
                MQTTSession.client_id == client_id, MQTTSession.is_active == True
            )
        )
    else:
        raise ValueError("Either session_id or client_id must be provided")

    session = result.scalars().first()

    if not session:
        raise ValueError("Session not found")

    session.is_active = False
    session.disconnected_at = datetime.now(timezone.utc)

    await db.flush()
    return session


async def update_session_activity(
    db: AsyncSession,
    session_id: int,
    subscribed_topics: List[str] = None,
) -> MQTTSession:
    """Update session last activity and optionally subscribed topics"""

    result = await db.execute(select(MQTTSession).where(MQTTSession.id == session_id))
    session = result.scalars().first()

    if not session:
        raise ValueError(f"Session with id {session_id} not found")

    session.last_activity = datetime.now(timezone.utc)

    if subscribed_topics is not None:
        session.subscribed_topics = subscribed_topics

    await db.flush()
    return session


async def update_topic_stats(
    db: AsyncSession,
    topic_pattern: str,
    date: datetime,
    message_count: int = 0,
    subscriber_count: int = 0,
    publisher_count: int = 0,
    total_bytes: int = 0,
    avg_qos: float = 0.0,
) -> MQTTTopicStats:
    """Create or update topic statistics for a given date"""

    # Try to find existing stats for this topic and date
    result = await db.execute(
        select(MQTTTopicStats).where(
            MQTTTopicStats.topic_pattern == topic_pattern,
            MQTTTopicStats.date == date.date(),
        )
    )
    stats = result.scalars().first()

    if not stats:
        stats = MQTTTopicStats(
            topic_pattern=topic_pattern,
            date=date.date(),
            message_count=message_count,
            subscriber_count=subscriber_count,
            publisher_count=publisher_count,
            total_bytes=total_bytes,
            avg_qos=avg_qos,
        )
        db.add(stats)
    else:
        # Update existing stats
        stats.message_count += message_count
        stats.subscriber_count = max(stats.subscriber_count, subscriber_count)
        stats.publisher_count = max(stats.publisher_count, publisher_count)
        stats.total_bytes += total_bytes
        # Recalculate average QoS
        if message_count > 0:
            total_messages = stats.message_count
            stats.avg_qos = (
                (stats.avg_qos * (total_messages - message_count))
                + (avg_qos * message_count)
            ) / total_messages

    await db.flush()
    return stats


async def get_device_by_id(db: AsyncSession, device_id: str) -> Optional[MQTTDevice]:
    """Get a device by its device_id"""
    result = await db.execute(
        select(MQTTDevice).where(MQTTDevice.device_id == device_id)
    )
    return result.scalars().first()


async def get_device_by_id_with_stats(
    db: AsyncSession, device_id: str
) -> Optional[Dict[str, Any]]:
    """Get a device by its device_id with statistics"""
    device = await get_device_by_id(db, device_id)

    if not device:
        return None

    device_dict = device.to_dict(include_relationships=False)

    # Get reading count
    reading_count = (
        await db.execute(
            select(func.count(MQTTSensorReading.id)).where(
                MQTTSensorReading.device_id == device.id
            )
        )
    ).scalar()

    # Get command count
    command_count = (
        await db.execute(
            select(func.count(MQTTCommand.id)).where(MQTTCommand.device_id == device.id)
        )
    ).scalar()

    # Get latest reading
    latest_query = await db.execute(
        select(MQTTSensorReading)
        .where(MQTTSensorReading.device_id == device.id)
        .order_by(MQTTSensorReading.timestamp.desc())
        .limit(1)
    )
    latest = latest_query.scalars().first()

    device_dict["sensor_readings_count"] = reading_count or 0
    device_dict["commands_count"] = command_count or 0
    device_dict["latest_reading"] = latest.timestamp.isoformat() if latest else None

    return device_dict


async def get_all_devices(
    db: AsyncSession, active_only: bool = False, include_stats: bool = False
) -> List[Dict[str, Any]]:
    """Get all devices, optionally filtered by active status and with statistics"""
    query = select(MQTTDevice)

    if active_only:
        query = query.where(MQTTDevice.is_active == True)

    query = query.order_by(MQTTDevice.device_name)
    result = await db.execute(query)
    devices = result.scalars().all()

    if not include_stats:
        return devices

    # Include statistics for each device
    devices_with_stats = []
    for device in devices:
        device_dict = device.to_dict(include_relationships=False)

        # Get latest reading
        latest_query = await db.execute(
            select(MQTTSensorReading)
            .where(MQTTSensorReading.device_id == device.id)
            .order_by(MQTTSensorReading.timestamp.desc())
            .limit(1)
        )
        latest = latest_query.scalars().first()

        # Get reading count
        reading_count = (
            await db.execute(
                select(func.count(MQTTSensorReading.id)).where(
                    MQTTSensorReading.device_id == device.id
                )
            )
        ).scalar()

        # Get command count
        command_count = (
            await db.execute(
                select(func.count(MQTTCommand.id)).where(
                    MQTTCommand.device_id == device.id
                )
            )
        ).scalar()

        device_dict["sensor_readings_count"] = reading_count or 0
        device_dict["commands_count"] = command_count or 0
        device_dict["latest_reading"] = latest.timestamp.isoformat() if latest else None

        devices_with_stats.append(device_dict)

    return devices_with_stats


async def get_device_readings(
    db: AsyncSession,
    device_id: str,
    limit: int = 100,
    include_relationships: bool = True,
) -> List[MQTTSensorReading]:
    """Get sensor readings for a specific device"""
    device = await get_device_by_id(db, device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")

    query = select(MQTTSensorReading).where(MQTTSensorReading.device_id == device.id)

    if include_relationships:
        query = query.options(
            selectinload(MQTTSensorReading.device),
            selectinload(MQTTSensorReading.sensor),
            selectinload(MQTTSensorReading.sensor_type_obj),
            selectinload(MQTTSensorReading.user),
        )

    query = query.order_by(MQTTSensorReading.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_recent_commands(
    db: AsyncSession, limit: int = 50, include_relationships: bool = True
) -> List[MQTTCommand]:
    """Get recent commands"""
    query = select(MQTTCommand)

    if include_relationships:
        query = query.options(
            selectinload(MQTTCommand.device),
            selectinload(MQTTCommand.user),
        )

    query = query.order_by(MQTTCommand.sent_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_device_commands(
    db: AsyncSession,
    device_id: str,
    limit: int = 50,
    include_relationships: bool = True,
) -> List[MQTTCommand]:
    """Get commands for a specific device"""
    device = await get_device_by_id(db, device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")

    query = select(MQTTCommand).where(MQTTCommand.device_id == device.id)

    if include_relationships:
        query = query.options(
            selectinload(MQTTCommand.device),
            selectinload(MQTTCommand.user),
        )

    query = query.order_by(MQTTCommand.sent_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_active_sessions(
    db: AsyncSession, include_relationships: bool = True
) -> List[MQTTSession]:
    """Get all active MQTT sessions"""
    query = select(MQTTSession).where(MQTTSession.is_active == True)

    if include_relationships:
        query = query.options(selectinload(MQTTSession.user))

    query = query.order_by(MQTTSession.connected_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_user_sessions(
    db: AsyncSession, user_id: int, active_only: bool = False
) -> List[MQTTSession]:
    """Get sessions for a specific user"""
    query = select(MQTTSession).where(MQTTSession.user_id == user_id)

    if active_only:
        query = query.where(MQTTSession.is_active == True)

    query = query.order_by(MQTTSession.connected_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_mqtt_statistics(db: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive MQTT system statistics"""

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
        await db.execute(select(func.count()).where(MQTTCommand.sent_at >= since_24h))
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
        {"device_id": d, "device_name": n, "readings": c} for d, n, c in result.all()
    ]

    return {
        "total_devices": total_devices or 0,
        "active_devices": active_devices or 0,
        "total_readings": total_readings or 0,
        "total_commands": total_commands or 0,
        "readings_24h": readings_24h or 0,
        "commands_24h": commands_24h or 0,
        "active_sessions": active_sessions or 0,
        "most_active_devices": most_active,
    }
