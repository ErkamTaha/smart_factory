"""
Database models for MQTT data (sensor readings, commands, device management)
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    Float,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, select
from app.database import Base
from datetime import datetime, timezone
from typing import List, Dict, Any


class MQTTDevice(Base):
    __tablename__ = "mqtt_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    device_name = Column(String(200))
    device_type = Column(String(50))  # "sensor", "actuator", "gateway", etc.
    location = Column(String(200))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON)  # Store additional device metadata

    # Relationships
    sensor_readings = relationship("MQTTSensorReading", back_populates="device")
    commands = relationship("MQTTCommand", back_populates="device")

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "location": self.location,
            "description": self.description,
            "is_active": self.is_active,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "meta_data": self.meta_data,
        }


class MQTTSensorReading(Base):
    __tablename__ = "mqtt_sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("mqtt_devices.id"), nullable=False, index=True
    )
    sensor_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    mqtt_topic = Column(String(200), nullable=False)
    qos = Column(Integer, default=1)
    retain = Column(Boolean, default=False)
    raw_data = Column(JSON)  # Store the complete raw MQTT payload
    user_id = Column(String(100), index=True)  # Who published this reading

    # Relationships
    device = relationship("MQTTDevice", back_populates="sensor_readings")

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_sensor_readings_device_time", "device_id", "timestamp"),
        Index("idx_sensor_readings_type_time", "sensor_type", "timestamp"),
        Index("idx_sensor_readings_user_time", "user_id", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device.device_id if self.device else None,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "mqtt_topic": self.mqtt_topic,
            "qos": self.qos,
            "retain": self.retain,
            "raw_data": self.raw_data,
            "user_id": self.user_id,
        }


class MQTTCommand(Base):
    __tablename__ = "mqtt_commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("mqtt_devices.id"), nullable=False, index=True
    )
    command = Column(String(100), nullable=False)
    parameters = Column(JSON)
    status = Column(
        String(20), default="sent", index=True
    )  # "sent", "acknowledged", "executed", "failed"
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    acknowledged_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    mqtt_topic = Column(String(200), nullable=False)
    qos = Column(Integer, default=1)
    retain = Column(Boolean, default=False)
    user_id = Column(String(100), nullable=False, index=True)  # Who sent the command
    response_data = Column(JSON)  # Store device response if any
    error_message = Column(Text)

    # Relationships
    device = relationship("MQTTDevice", back_populates="commands")

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device.device_id if self.device else None,
            "command": self.command,
            "parameters": self.parameters,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "mqtt_topic": self.mqtt_topic,
            "qos": self.qos,
            "retain": self.retain,
            "user_id": self.user_id,
            "response_data": self.response_data,
            "error_message": self.error_message,
        }


class MQTTSession(Base):
    __tablename__ = "mqtt_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    client_id = Column(String(200), nullable=False)
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    subscribed_topics = Column(JSON)  # Array of subscribed topics
    connection_metadata = Column(JSON)  # Additional connection info

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "connected_at": (
                self.connected_at.isoformat() if self.connected_at else None
            ),
            "disconnected_at": (
                self.disconnected_at.isoformat() if self.disconnected_at else None
            ),
            "is_active": self.is_active,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "subscribed_topics": self.subscribed_topics or [],
            "connection_metadata": self.connection_metadata,
        }


class MQTTTopicStats(Base):
    __tablename__ = "mqtt_topic_stats"

    id = Column(Integer, primary_key=True, index=True)
    topic_pattern = Column(String(200), nullable=False, index=True)
    date = Column(
        DateTime(timezone=True), nullable=False, index=True
    )  # Date for the stats
    message_count = Column(Integer, default=0)
    subscriber_count = Column(Integer, default=0)
    publisher_count = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    avg_qos = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint on topic and date
    __table_args__ = (
        Index("idx_topic_stats_topic_date", "topic_pattern", "date", unique=True),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "topic_pattern": self.topic_pattern,
            "date": self.date.isoformat() if self.date else None,
            "message_count": self.message_count,
            "subscriber_count": self.subscriber_count,
            "publisher_count": self.publisher_count,
            "total_bytes": self.total_bytes,
            "avg_qos": self.avg_qos,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Helper functions for MQTT operations
async def create_or_update_device(
    db, device_id: str, device_data: Dict[str, Any] = None
) -> MQTTDevice:
    """Create or update a device, return the device object"""
    results = await db.execute(
        select(MQTTDevice).where(MQTTDevice.device_id == device_id)
    )
    device = results.scalars.first()

    if not device:
        device = MQTTDevice(
            device_id=device_id,
            device_name=(
                device_data.get("name", device_id) if device_data else device_id
            ),
            device_type=(
                device_data.get("type", "unknown") if device_data else "unknown"
            ),
            is_active=True,
            last_seen=datetime.now(timezone.utc),
            meta_data=device_data,
        )
        db.add(device)
        await db.flush()  # Get the ID
    else:
        # Update last seen and metadata if provided
        device.last_seen = datetime.now(timezone.utc)
        if device_data:
            device.meta_data = device_data

    return device


async def store_sensor_reading(
    db,
    device_id: str,
    sensor_type: str,
    value: float,
    unit: str,
    topic: str,
    user_id: str = None,
    raw_data: Dict[str, Any] = None,
    qos: int = 1,
    retain: bool = False,
    timestamp: datetime = None,
) -> MQTTSensorReading:
    """Store a sensor reading in the database"""

    # Create or update device
    device = await create_or_update_device(db, device_id)

    # Create sensor reading
    reading = MQTTSensorReading(
        device_id=device.id,
        sensor_type=sensor_type,
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
    return reading


async def store_command(
    db,
    device_id: str,
    command: str,
    parameters: Dict[str, Any],
    topic: str,
    user_id: str,
    qos: int = 1,
    retain: bool = False,
) -> MQTTCommand:
    """Store a command in the database"""

    # Create or update device
    device = await create_or_update_device(db, device_id)

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
    return cmd
