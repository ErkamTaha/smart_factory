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
from sqlalchemy.sql import func, select
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

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            result.update(
                {
                    "sensors_count": len(self.sensors) if self.sensors else 0,
                }
            )

        return result


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

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "sensor_id": self.sensor_id,
            "pattern": self.pattern,
            "sensor_type_id": self.sensor_type_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            selected_limit = self.get_selected_limit()
            result.update(
                {
                    "sensor_type": (
                        self.sensor_type_obj.name if self.sensor_type_obj else None
                    ),
                    "limits": (
                        [
                            limit.to_dict(include_relationships=False)
                            for limit in self.limits
                        ]
                        if self.limits
                        else []
                    ),
                    "selected_limit": (
                        selected_limit.to_dict(include_relationships=False)
                        if selected_limit
                        else None
                    ),
                    "unresolved_alerts_count": len(self.get_unresolved_alerts()),
                }
            )

        return result

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

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "name": self.name,
            "upper_limit": self.upper_limit,
            "lower_limit": self.lower_limit,
            "unit": self.unit,
            "is_selected": self.is_selected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            result.update(
                {
                    "sensor_id": self.sensor.sensor_id if self.sensor else None,
                    "sensor_pattern": self.sensor.pattern if self.sensor else None,
                }
            )

        return result


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

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "sensor_id": self.sensor_id,
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

        if include_relationships:
            result.update(
                {
                    "sensor_identifier": self.sensor.sensor_id if self.sensor else None,
                    "sensor_pattern": self.sensor.pattern if self.sensor else None,
                    "sensor_type": (
                        self.sensor.sensor_type_obj.name
                        if self.sensor and self.sensor.sensor_type_obj
                        else None
                    ),
                }
            )

        return result


class SSConfig(Base):
    __tablename__ = "ss_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }

    @classmethod
    def get_config_dict(cls, db):
        """Get all configuration as a dictionary"""
        configs = db.query(cls).all()
        return {config.key: config.value for config in configs}


# Helper functions for SS operations
async def create_default_sensor_types(db):
    """Create default sensor types if they don't exist"""

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
    """Create default sensors for each sensor type if they don't exist"""

    # Get all sensor types
    result = await db.execute(select(SSSensorType))
    sensor_types = {st.name: st for st in result.scalars()}

    if not sensor_types:
        return  # No sensor types exist yet

    default_sensors = [
        {
            "sensor_id": "temp_sensor_floor_a1",
            "pattern": "sf/sensors/temp_sensor_floor_a1/temperature",
            "sensor_type_name": "temperature",
            "limits": [
                {
                    "name": "normal_operation",
                    "upper_limit": 30.0,
                    "lower_limit": 18.0,
                    "unit": "C",
                    "is_selected": True,
                },
                {
                    "name": "strict_control",
                    "upper_limit": 25.0,
                    "lower_limit": 20.0,
                    "unit": "C",
                    "is_selected": False,
                },
            ],
        },
        {
            "sensor_id": "humidity_sensor_floor_a1",
            "pattern": "sf/sensors/humidity_sensor_floor_a1/humidity",
            "sensor_type_name": "humidity",
            "limits": [
                {
                    "name": "normal_operation",
                    "upper_limit": 70.0,
                    "lower_limit": 30.0,
                    "unit": "%",
                    "is_selected": True,
                },
                {
                    "name": "optimal_range",
                    "upper_limit": 60.0,
                    "lower_limit": 40.0,
                    "unit": "%",
                    "is_selected": False,
                },
            ],
        },
        {
            "sensor_id": "pressure_sensor_line_b",
            "pattern": "sf/sensors/pressure_sensor_line_b/pressure",
            "sensor_type_name": "pressure",
            "limits": [
                {
                    "name": "safe_operation",
                    "upper_limit": 90.0,
                    "lower_limit": 20.0,
                    "unit": "psi",
                    "is_selected": True,
                },
                {
                    "name": "optimal_performance",
                    "upper_limit": 80.0,
                    "lower_limit": 40.0,
                    "unit": "psi",
                    "is_selected": False,
                },
            ],
        },
        {
            "sensor_id": "motion_sensor_entrance_1",
            "pattern": "sf/sensors/motion_sensor_entrance_1/motion",
            "sensor_type_name": "motion",
            "limits": [
                {
                    "name": "activity_threshold",
                    "upper_limit": 100.0,  # Max detections per minute
                    "lower_limit": 0.0,
                    "unit": "count",
                    "is_selected": True,
                },
                {
                    "name": "high_traffic",
                    "upper_limit": 50.0,
                    "lower_limit": 0.0,
                    "unit": "count",
                    "is_selected": False,
                },
            ],
        },
    ]

    for sensor_data in default_sensors:
        # Check if sensor already exists
        result = await db.execute(
            select(SSSensor).where(SSSensor.sensor_id == sensor_data["sensor_id"])
        )
        existing = result.scalars().first()

        if not existing:
            sensor_type_name = sensor_data["sensor_type_name"]
            sensor_type = sensor_types.get(sensor_type_name)

            if not sensor_type:
                continue  # Skip if sensor type doesn't exist

            # Create sensor
            sensor = SSSensor(
                sensor_id=sensor_data["sensor_id"],
                pattern=sensor_data["pattern"],
                sensor_type_id=sensor_type.id,
                is_active=True,
            )
            db.add(sensor)
            await db.flush()  # Get the sensor ID

            # Create limits for this sensor
            for limit_data in sensor_data["limits"]:
                limit = SSSensorLimit(
                    sensor_id=sensor.id,
                    name=limit_data["name"],
                    upper_limit=limit_data["upper_limit"],
                    lower_limit=limit_data["lower_limit"],
                    unit=limit_data["unit"],
                    is_selected=limit_data["is_selected"],
                )
                db.add(limit)

    await db.commit()


async def create_default_ss_config(db):
    """Create default SS (Sensor Security) configuration"""
    default_configs = [
        {
            "key": "alert_retention_days",
            "value": "30",
            "description": "Number of days to retain resolved alerts",
        },
        {
            "key": "auto_resolve_alerts",
            "value": "false",
            "description": "Automatically resolve alerts when sensor values return to normal",
        },
        {
            "key": "enable_notifications",
            "value": "true",
            "description": "Enable WebSocket notifications for sensor alerts",
        },
        {
            "key": "alert_cooldown_seconds",
            "value": "60",
            "description": "Minimum time between consecutive alerts for the same sensor",
        },
        {
            "key": "version",
            "value": "1.0",
            "description": "SS configuration version",
        },
    ]

    for config_data in default_configs:
        result = await db.execute(
            select(SSConfig).where(SSConfig.key == config_data["key"])
        )
        existing = result.scalars().first()

        if not existing:
            db.add(SSConfig(**config_data))

    await db.commit()
