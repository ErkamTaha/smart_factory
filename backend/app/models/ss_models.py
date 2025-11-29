"""
Database models for SS (Sensor Security) management
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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple


class SSSensorType(Base):
    __tablename__ = "ss_sensor_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text)
    properties = Column(JSON)  # Store type properties as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sensors = relationship("SSSensor", back_populates="sensor_type_obj")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SSSensor(Base):
    __tablename__ = "ss_sensors"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(100), unique=True, index=True, nullable=False)
    pattern = Column(String(200), nullable=False)  # MQTT topic pattern
    sensor_type_id = Column(Integer, ForeignKey("ss_sensor_types.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sensor_type_obj = relationship("SSSensorType", back_populates="sensors")
    limits = relationship("SSSensorLimit", back_populates="sensor")
    alerts = relationship("SSAlert", back_populates="sensor")

    def to_dict(self):
        selected_limit = next(
            (limit for limit in self.limits if limit.is_selected), None
        )
        return {
            "id": self.id,
            "sensor_id": self.sensor_id,
            "pattern": self.pattern,
            "sensor_type": self.sensor_type_obj.name if self.sensor_type_obj else None,
            "is_active": self.is_active,
            "limits": [limit.to_dict() for limit in self.limits],
            "selected_limit": selected_limit.to_dict() if selected_limit else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_selected_limit(self) -> Optional["SSSensorLimit"]:
        """Get the currently selected limit configuration"""
        return next((limit for limit in self.limits if limit.is_selected), None)

    def check_value_against_limits(
        self, value: float, unit: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if a value exceeds the sensor's limits"""
        selected_limit = self.get_selected_limit()

        if not selected_limit:
            return False, None

        if selected_limit.unit != unit:
            return False, None

        if value > selected_limit.upper_limit:
            return True, "upper"
        elif value < selected_limit.lower_limit:
            return True, "lower"

        return False, None

    def get_unresolved_alerts(self):
        """Get all unresolved alerts for this sensor"""
        return [alert for alert in self.alerts if not alert.is_resolved]

    def get_recent_alerts(self, days: int = 7):
        """Get alerts from the last N days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [alert for alert in self.alerts if alert.triggered_at >= cutoff]


class SSSensorLimit(Base):
    __tablename__ = "ss_sensor_limits"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("ss_sensors.id"), nullable=False)
    name = Column(String(50), nullable=False)  # "default", "secondary", etc.
    upper_limit = Column(Float, nullable=False)
    lower_limit = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sensor = relationship("SSSensor", back_populates="limits")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "upper_limit": self.upper_limit,
            "lower_limit": self.lower_limit,
            "unit": self.unit,
            "is_selected": self.is_selected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SSAlert(Base):
    __tablename__ = "ss_alerts"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("ss_sensors.id"), nullable=False)
    alert_type = Column(String(20), nullable=False)  # "upper", "lower"
    triggered_value = Column(Float, nullable=False)
    limit_value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    message = Column(Text)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True))
    triggered_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    mqtt_topic = Column(String(200))  # The MQTT topic that triggered the alert
    raw_data = Column(JSON)  # Store the raw sensor data that triggered the alert

    # Relationships
    sensor = relationship("SSSensor", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "sensor_id": self.sensor.sensor_id if self.sensor else None,
            "alert_type": self.alert_type,
            "triggered_value": self.triggered_value,
            "limit_value": self.limit_value,
            "unit": self.unit,
            "message": self.message,
            "is_resolved": self.is_resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "triggered_at": (
                self.triggered_at.isoformat() if self.triggered_at else None
            ),
            "mqtt_topic": self.mqtt_topic,
            "raw_data": self.raw_data,
        }


class SSConfig(Base):
    __tablename__ = "ss_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    @classmethod
    def get_config_dict(cls, db):
        """Get all configuration as a dictionary"""
        configs = db.query(cls).all()
        return {config.key: config.value for config in configs}


# Helper functions for SS operations
async def create_default_sensor_types(db):
    """Create default sensor types if they don't exist"""
    from sqlalchemy import select

    default_types = [
        {
            "name": "temperature",
            "description": "Temperature sensors",
            "properties": {"common_units": ["C", "F", "K"]},
        },
        {
            "name": "humidity",
            "description": "Humidity sensors",
            "properties": {"common_units": ["%"]},
        },
        {
            "name": "pressure",
            "description": "Pressure sensors",
            "properties": {"common_units": ["Pa", "bar", "psi"]},
        },
        {
            "name": "motion",
            "description": "Motion detection sensors",
            "properties": {"common_units": ["bool", "count"]},
        },
    ]

    for type_data in default_types:
        result = await db.execute(
            select(SSSensorType).where(SSSensorType.name == type_data["name"])
        )
        existing = result.scalars().first()
        if not existing:
            sensor_type = SSSensorType(**type_data)
            db.add(sensor_type)

    await db.commit()


async def create_default_sensors(db):
    """Create default sensors from existing config if they don't exist"""
    from sqlalchemy import select

    # Get temperature sensor type
    result = await db.execute(
        select(SSSensorType).where(SSSensorType.name == "temperature")
    )
    temp_type = result.scalars().first()
    if not temp_type:
        return

    # Create test sensor if it doesn't exist
    result = await db.execute(
        select(SSSensor).where(SSSensor.sensor_id == "test_device_001")
    )
    existing = result.scalars().first()
    if not existing:
        sensor = SSSensor(
            sensor_id="test_device_001",
            pattern="sf/sensors/test_device_001",
            sensor_type_id=temp_type.id,
            is_active=True,
        )
        db.add(sensor)
        await db.flush()  # Get the ID

        # Create default limits
        default_limit = SSSensorLimit(
            sensor_id=sensor.id,
            name="default",
            upper_limit=30.0,
            lower_limit=20.0,
            unit="C",
            is_selected=True,
        )

        secondary_limit = SSSensorLimit(
            sensor_id=sensor.id,
            name="secondary",
            upper_limit=35.0,
            lower_limit=25.0,
            unit="C",
            is_selected=False,
        )

        db.add(default_limit)
        db.add(secondary_limit)

    await db.commit()
