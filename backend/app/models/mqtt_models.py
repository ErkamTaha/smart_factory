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
from .ss_models import SSSensor, SSSensorType
from .acl_models import ACLUser


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

    def to_dict(self, include_relationships=True):
        result = {
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

        if include_relationships:
            result.update(
                {
                    "sensor_readings_count": (
                        len(self.sensor_readings) if self.sensor_readings else 0
                    ),
                    "commands_count": len(self.commands) if self.commands else 0,
                }
            )

        return result


class MQTTSensorReading(Base):
    __tablename__ = "mqtt_sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("mqtt_devices.id"), nullable=False, index=True
    )
    sensor_id = Column(Integer, ForeignKey("ss_sensors.id"), nullable=False, index=True)
    sensor_type = Column(
        Integer, ForeignKey("ss_sensor_types.id"), nullable=False, index=True
    )
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    mqtt_topic = Column(String(200), nullable=False)
    qos = Column(Integer, default=1)
    retain = Column(Boolean, default=False)
    raw_data = Column(JSON)  # Store the complete raw MQTT payload
    user_id = Column(
        Integer, ForeignKey("acl_users.id"), nullable=False, index=True
    )  # Who published this reading

    # Relationships
    device = relationship("MQTTDevice", back_populates="sensor_readings")
    sensor = relationship("SSSensor")
    sensor_type_obj = relationship("SSSensorType")
    user = relationship("ACLUser")

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_sensor_readings_device_time", "device_id", "timestamp"),
        Index("idx_sensor_readings_type_time", "sensor_type", "timestamp"),
        Index("idx_sensor_readings_user_time", "user_id", "timestamp"),
    )

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "device_id": self.device_id,
            "sensor_id": self.sensor_id,
            "sensor_type_id": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "mqtt_topic": self.mqtt_topic,
            "qos": self.qos,
            "retain": self.retain,
            "raw_data": self.raw_data,
            "user_id": self.user_id,
        }

        if include_relationships:
            result.update(
                {
                    "device_name": self.device.device_name if self.device else None,
                    "device_identifier": self.device.device_id if self.device else None,
                    "sensor_identifier": self.sensor.sensor_id if self.sensor else None,
                    "sensor_pattern": self.sensor.pattern if self.sensor else None,
                    "sensor_type_name": (
                        self.sensor_type_obj.name if self.sensor_type_obj else None
                    ),
                    "username": self.user.username if self.user else None,
                }
            )

        return result


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
    user_id = Column(
        Integer, ForeignKey("acl_users.id"), nullable=False, index=True
    )  # Who sent the command
    response_data = Column(JSON)  # Store device response if any
    error_message = Column(Text)

    # Relationships
    device = relationship("MQTTDevice", back_populates="commands")
    user = relationship("ACLUser")

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "device_id": self.device_id,
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

        if include_relationships:
            result.update(
                {
                    "device_name": self.device.device_name if self.device else None,
                    "device_identifier": self.device.device_id if self.device else None,
                    "username": self.user.username if self.user else None,
                }
            )

        return result


class MQTTSession(Base):
    __tablename__ = "mqtt_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("acl_users.id"), nullable=False, index=True)
    client_id = Column(String(200), nullable=False)
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    subscribed_topics = Column(JSON)  # Array of subscribed topics
    connection_metadata = Column(JSON)  # Additional connection info

    user = relationship("ACLUser")

    def to_dict(self, include_relationships=True):
        result = {
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

        if include_relationships:
            result.update(
                {
                    "username": self.user.username if self.user else None,
                    "user_email": self.user.email if self.user else None,
                }
            )

        return result


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


# In mqtt_models.py


async def create_default_mqtt_devices(db):
    """Create default MQTT devices for each sensor type if they don't exist"""
    from sqlalchemy import select

    default_devices = [
        {
            "device_id": "temp_sensor_floor_a1",
            "device_name": "Temperature Sensor - Floor A1",
            "device_type": "sensor",
            "location": "Factory Floor - Section A1",
            "description": "Ambient temperature monitoring for production area A1",
            "is_active": True,
            "meta_data": {
                "manufacturer": "Sensirion AG",
                "model": "SHT85",
                "firmware_version": "2.1.0",
                "installation_date": "2024-01-15",
                "calibration_date": "2024-01-10",
            },
        },
        {
            "device_id": "humidity_sensor_floor_a1",
            "device_name": "Humidity Sensor - Floor A1",
            "device_type": "sensor",
            "location": "Factory Floor - Section A1",
            "description": "Relative humidity monitoring for production area A1",
            "is_active": True,
            "meta_data": {
                "manufacturer": "Sensirion AG",
                "model": "SHT85",
                "firmware_version": "2.1.0",
                "installation_date": "2024-01-15",
                "calibration_date": "2024-01-10",
            },
        },
        {
            "device_id": "pressure_sensor_line_b",
            "device_name": "Pressure Sensor - Production Line B",
            "device_type": "sensor",
            "location": "Factory Floor - Production Line B",
            "description": "Hydraulic pressure monitoring for production line B",
            "is_active": True,
            "meta_data": {
                "manufacturer": "Honeywell",
                "model": "PX3AN0BS100PSAAX",
                "firmware_version": "1.5.2",
                "installation_date": "2024-02-01",
                "pressure_range": "0-100 PSI",
            },
        },
        {
            "device_id": "motion_sensor_entrance_1",
            "device_name": "Motion Sensor - Main Entrance",
            "device_type": "sensor",
            "location": "Factory Floor - Main Entrance",
            "description": "Personnel and equipment movement detection at main entrance",
            "is_active": True,
            "meta_data": {
                "manufacturer": "Bosch Security",
                "model": "ISC-BPR2-W12",
                "firmware_version": "3.0.1",
                "installation_date": "2024-01-20",
                "detection_range": "12 meters",
            },
        },
        {
            "device_id": "gateway_main_floor",
            "device_name": "Main Floor Gateway",
            "device_type": "gateway",
            "location": "Factory Floor - Control Room",
            "description": "Primary MQTT gateway for factory floor sensor network",
            "is_active": True,
            "meta_data": {
                "manufacturer": "Industrial IoT Solutions",
                "model": "IGW-1000",
                "firmware_version": "2.5.0",
                "max_connections": 250,
                "supported_protocols": ["MQTT", "CoAP", "HTTP"],
            },
        },
    ]

    for device_data in default_devices:
        result = await db.execute(
            select(MQTTDevice).where(MQTTDevice.device_id == device_data["device_id"])
        )
        existing = result.scalars().first()
        if not existing:
            device = MQTTDevice(**device_data)
            db.add(device)

    await db.commit()
