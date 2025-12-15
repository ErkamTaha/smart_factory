"""
Database-backed Sensor Security (SS) Manager for Smart Factory
All methods now accept db session as parameter for proper lifecycle management
"""

import traceback
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ss_models import (
    SSSensor,
    SSSensorType,
    SSSensorLimit,
    SSAlert,
    SSConfig,
)

from app.database import get_db

logger = logging.getLogger(__name__)


class DatabaseSSManager:
    """Async Database-backed Sensor Security Manager with caching"""

    def __init__(self):
        self.last_loaded: Optional[datetime] = None
        self._config_cache: Dict[str, str] = {}
        self._cache_timeout = timedelta(minutes=5)
        # Sensor cache: sensor_id -> {'info': Dict, 'limits': Dict, 'ts': datetime}
        self._sensor_cache: Dict[str, Dict] = {}
        # Type cache: type_name -> Dict
        self._type_cache: Dict[str, Dict] = {}
        self._type_cache_ts: Optional[datetime] = None

    async def _load_config(self, db: AsyncSession):
        """Load SS configuration from database"""
        try:
            logger.info("Loading SS configuration from database")

            # Load configuration
            result = await db.execute(select(SSConfig))
            configs = result.scalars().all()
            self._config_cache = {config.key: config.value for config in configs}

            self.last_loaded = datetime.now(timezone.utc)

            # Count sensors and types for logging
            sensor_count_result = await db.execute(
                select(SSSensor).where(SSSensor.is_active == True)
            )
            sensor_count = len(sensor_count_result.scalars().all())

            type_count_result = await db.execute(select(SSSensorType))
            type_count = len(type_count_result.scalars().all())

            logger.info(
                f"SS loaded from database: {sensor_count} sensors, {type_count} types"
            )

        except Exception as e:
            logger.error(f"Error loading SS from database: {e}")
            self._config_cache = {}

    async def reload(self, db: AsyncSession):
        """Reload SS configuration from database"""
        await self._load_config(db)
        self._sensor_cache.clear()
        self._type_cache.clear()

    async def _get_sensor(self, sensor_id: str, db: AsyncSession) -> Optional[SSSensor]:
        """Fetch sensor from DB with relationships"""
        result = await db.execute(
            select(SSSensor)
            .where(and_(SSSensor.sensor_id == sensor_id, SSSensor.is_active == True))
            .options(selectinload(SSSensor.sensor_type_obj))
        )
        return result.scalars().first()

    async def get_sensor_type(self, sensor_id: str, db: AsyncSession) -> Optional[str]:
        """Get sensor type with caching"""
        now = datetime.now(timezone.utc)
        cached = self._sensor_cache.get(sensor_id)
        if cached and now - cached["ts"] < self._cache_timeout and cached.get("type"):
            return cached["type"]

        try:
            sensor = await self._get_sensor(sensor_id, db)
            sensor_type = (
                sensor.sensor_type_obj.name
                if sensor and sensor.sensor_type_obj
                else None
            )

            if cached:
                cached["type"] = sensor_type
                cached["ts"] = now
            else:
                self._sensor_cache[sensor_id] = {"type": sensor_type, "ts": now}

            return sensor_type
        except Exception as e:
            logger.error(f"Error getting sensor type for {sensor_id}: {e}")
            return None

    async def get_sensor_activeness(
        self, sensor_id: str, db: AsyncSession
    ) -> Optional[bool]:
        """Get sensor activeness status with caching"""
        now = datetime.now(timezone.utc)
        cached = self._sensor_cache.get(sensor_id)
        if (
            cached
            and now - cached["ts"] < self._cache_timeout
            and "is_active" in cached
        ):
            return cached["is_active"]

        try:
            result = await db.execute(
                select(SSSensor).where(SSSensor.sensor_id == sensor_id)
            )
            sensor = result.scalars().first()
            is_active = sensor.is_active if sensor else None

            if cached:
                cached["is_active"] = is_active
                cached["ts"] = now
            else:
                self._sensor_cache[sensor_id] = {"is_active": is_active, "ts": now}

            return is_active
        except Exception as e:
            logger.error(f"Error getting sensor activeness for {sensor_id}: {e}")
            return None

    async def get_all_sensor_limits(
        self, sensor_id: str, db: AsyncSession
    ) -> Optional[Dict]:
        """Get all limit configurations for a sensor with caching"""
        now = datetime.now(timezone.utc)
        cached = self._sensor_cache.get(sensor_id)
        if (
            cached
            and now - cached["ts"] < self._cache_timeout
            and cached.get("all_limits")
        ):
            return cached["all_limits"]

        try:
            sensor = await self._get_sensor(sensor_id, db)
            limits = None

            if sensor:
                limits = {}
                result = await db.execute(
                    select(SSSensorLimit).where(SSSensorLimit.sensor_id == sensor.id)
                )
                sensor_limits = result.scalars().all()

                for limit in sensor_limits:
                    limits[limit.name] = {
                        "selected": limit.is_selected,
                        "upper": limit.upper_limit,
                        "lower": limit.lower_limit,
                        "unit": limit.unit,
                    }

            if cached:
                cached["all_limits"] = limits
                cached["ts"] = now
            else:
                self._sensor_cache[sensor_id] = {"all_limits": limits, "ts": now}

            return limits
        except Exception as e:
            logger.error(f"Error getting sensor limits for {sensor_id}: {e}")
            return None

    async def get_sensor_limit_config(
        self, sensor_id: str, db: AsyncSession
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """Get the selected limit configuration for a sensor with caching"""
        now = datetime.now(timezone.utc)
        cached = self._sensor_cache.get(sensor_id)
        if (
            cached
            and now - cached["ts"] < self._cache_timeout
            and cached.get("selected_limit_name") is not None
        ):
            return cached["selected_limit_name"], cached.get("selected_limit_config")

        try:
            sensor = await self._get_sensor(sensor_id, db)
            limit_name, limit_config = None, None

            if sensor:
                result = await db.execute(
                    select(SSSensorLimit).where(
                        and_(
                            SSSensorLimit.sensor_id == sensor.id,
                            SSSensorLimit.is_selected == True,
                        )
                    )
                )
                selected_limit = result.scalars().first()

                if selected_limit:
                    limit_name = selected_limit.name
                    limit_config = {
                        "upper": selected_limit.upper_limit,
                        "lower": selected_limit.lower_limit,
                        "unit": selected_limit.unit,
                        "selected": selected_limit.is_selected,
                    }

            if cached:
                cached["selected_limit_name"] = limit_name
                cached["selected_limit_config"] = limit_config
                cached["ts"] = now
            else:
                self._sensor_cache[sensor_id] = {
                    "selected_limit_name": limit_name,
                    "selected_limit_config": limit_config,
                    "ts": now,
                }

            return limit_name, limit_config
        except Exception as e:
            logger.error(f"Error getting sensor limit config for {sensor_id}: {e}")
            return None, None

    async def check_limit_for_alert(
        self, sensor_id: str, value: float, unit: str, db: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """Check if a sensor value violates limits and should trigger an alert"""
        try:
            # Get selected limit configuration from cache
            limit_name, limit_config = await self.get_sensor_limit_config(sensor_id, db)

            if not limit_config:
                logger.warning(f"Sensor {sensor_id} not found or no limit config in SS")
                return False, None

            # Check if alerts are enabled
            alerts_enabled = (
                self._config_cache.get("enable_alerts", "true").lower() == "true"
            )
            if not alerts_enabled:
                return False, None

            # Check if unit matches
            if unit != limit_config["unit"]:
                logger.warning(
                    f"Sensor limit unit for {sensor_id} does not match the unit in {limit_name} config in SS"
                )
                return False, None

            # Check value against limits
            alert_triggered = False
            alert_type = None

            if value > limit_config["upper"]:
                alert_triggered = True
                alert_type = "upper"
                logger.warning(
                    f"Alert: Sensor value is greater than the upper limit for {sensor_id}"
                )
            elif value < limit_config["lower"]:
                alert_triggered = True
                alert_type = "lower"
                logger.warning(
                    f"Alert: Sensor value is lower than the lower limit for {sensor_id}"
                )

            if alert_triggered:
                # Get sensor for alert creation
                sensor = await self._get_sensor(sensor_id, db)
                if sensor:
                    # Create alert record
                    limit_value = (
                        limit_config["upper"]
                        if alert_type == "upper"
                        else limit_config["lower"]
                    )

                    alert = SSAlert(
                        sensor_id=sensor.id,
                        alert_type=alert_type,
                        triggered_value=value,
                        limit_value=limit_value,
                        unit=unit,
                        message=(
                            f"Sensor {sensor_id} exceeded {alert_type} limit: {value}{unit} > {limit_value}{unit}"
                            if alert_type == "upper"
                            else f"Sensor {sensor_id} below {alert_type} limit: {value}{unit} < {limit_value}{unit}"
                        ),
                        is_resolved=False,
                        mqtt_topic=sensor.pattern,
                        raw_data={
                            "sensor_id": sensor_id,
                            "value": value,
                            "unit": unit,
                        },
                    )

                    db.add(alert)
                    await db.flush()

                    logger.warning(f"Alert triggered: {alert.message}")

            return alert_triggered, alert_type

        except Exception as e:
            logger.error(f"Error checking limits for {sensor_id}: {e}")
            return False, None

    async def add_sensor(
        self,
        sensor_id: str,
        pattern: str,
        sensor_type: str,
        active: bool,
        limits: List[Dict],
        db: AsyncSession,
    ):
        """Add a new sensor to SS"""
        try:
            # Check if sensor already exists
            result = await db.execute(
                select(SSSensor).where(SSSensor.sensor_id == sensor_id)
            )
            existing = result.scalars().first()
            if existing:
                raise ValueError(f"Sensor {sensor_id} already exists")

            # Get sensor type
            result = await db.execute(
                select(SSSensorType).where(SSSensorType.name == sensor_type)
            )
            sensor_type_obj = result.scalars().first()
            if not sensor_type_obj:
                raise ValueError(f"Sensor type {sensor_type} not found")

            # Create sensor
            sensor = SSSensor(
                sensor_id=sensor_id,
                pattern=pattern,
                sensor_type_id=sensor_type_obj.id,
                is_active=active,
            )
            db.add(sensor)
            await db.flush()

            # Add limits
            for limit_data in limits:
                limit_dict = (
                    limit_data.dict() if hasattr(limit_data, "dict") else limit_data
                )

                limit = SSSensorLimit(
                    sensor_id=sensor.id,
                    name=limit_dict.get("name", "default"),
                    upper_limit=float(limit_dict["upper_limit"]),
                    lower_limit=float(limit_dict["lower_limit"]),
                    unit=limit_dict["unit"],
                    is_selected=bool(limit_dict.get("is_selected", False)),
                )
                db.add(limit)

            await db.flush()

            # Clear cache for this sensor
            self._sensor_cache.pop(sensor_id, None)

            logger.info(f"Added sensor {sensor_id} with pattern: {pattern}")

        except Exception as e:
            logger.error(f"Error adding sensor {sensor_id}: {e}")
            raise

    async def remove_sensor(self, sensor_id: str, db: AsyncSession):
        """Remove sensor from SS (soft delete)"""
        try:
            result = await db.execute(
                select(SSSensor).where(SSSensor.sensor_id == sensor_id)
            )
            sensor = result.scalars().first()
            if sensor:
                sensor.is_active = False
                await db.flush()

                # Clear cache for this sensor
                self._sensor_cache.pop(sensor_id, None)

                logger.info(f"Deactivated sensor {sensor_id}")
            else:
                logger.warning(f"Sensor {sensor_id} not found")
        except Exception as e:
            logger.error(f"Error removing sensor {sensor_id}: {e}")
            raise

    async def update_sensor(
        self,
        sensor_id: str,
        pattern: Optional[str],
        sensor_type: Optional[str],
        active: Optional[bool],
        limits: Optional[List[Dict]],
        db: AsyncSession,
    ):
        """Update sensor configuration"""
        try:
            # Fetch sensor
            result = await db.execute(
                select(SSSensor).where(SSSensor.sensor_id == sensor_id)
            )
            sensor = result.scalars().first()
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")

            # Update basic fields
            if pattern is not None:
                sensor.pattern = pattern

            if active is not None:
                sensor.is_active = active

            if sensor_type is not None:
                result = await db.execute(
                    select(SSSensorType).where(SSSensorType.name == sensor_type)
                )
                st = result.scalars().first()
                if st:
                    sensor.sensor_type_id = st.id

            # Update limits
            if limits is not None:
                # Remove existing limits
                result = await db.execute(
                    select(SSSensorLimit).where(SSSensorLimit.sensor_id == sensor.id)
                )
                existing_limits = result.scalars().all()

                for l in existing_limits:
                    await db.delete(l)

                # Insert new limits
                for limit_data in limits:
                    limit_dict = (
                        limit_data.dict() if hasattr(limit_data, "dict") else limit_data
                    )

                    new_limit = SSSensorLimit(
                        sensor_id=sensor.id,
                        name=limit_dict.get("name", "default"),
                        upper_limit=float(limit_dict["upper_limit"]),
                        lower_limit=float(limit_dict["lower_limit"]),
                        unit=limit_dict["unit"],
                        is_selected=bool(limit_dict.get("is_selected", False)),
                    )

                    db.add(new_limit)

            await db.flush()

            # Clear cache
            self._sensor_cache.pop(sensor_id, None)

            logger.info(f"Updated sensor {sensor_id}")

        except Exception as e:
            logger.error(f"Error updating sensor {sensor_id}: {e}")
            raise

    async def get_ss_info(self) -> Dict:
        """Get SS configuration info"""
        try:
            async with get_db as db:
                # Count sensors
                result = await db.execute(
                    select(SSSensor).where(SSSensor.is_active == True)
                )
                total_sensors = len(result.scalars().all())

                # Count types
                result = await db.execute(select(SSSensorType))
                total_types = len(result.scalars().all())

                # Count active alerts
                result = await db.execute(
                    select(SSAlert).where(SSAlert.is_resolved == False)
                )
                active_alerts = len(result.scalars().all())

                return {
                    "version": self._config_cache.get("version", "unknown"),
                    "total_sensors": total_sensors,
                    "total_types": total_types,
                    "active_alerts": active_alerts,
                    "last_loaded": (
                        self.last_loaded.isoformat() if self.last_loaded else None
                    ),
                    "storage": "database",
                    "alerts_enabled": self._config_cache.get("enable_alerts", "true"),
                }
        except Exception as e:
            logger.error(f"Error getting SS info: {e}")
            return {
                "version": "unknown",
                "total_sensors": 0,
                "total_types": 0,
                "active_alerts": 0,
                "last_loaded": (
                    self.last_loaded.isoformat() if self.last_loaded else None
                ),
                "storage": "database",
                "error": str(e),
            }

    async def get_sensor_info(self, sensor_id: str, db: AsyncSession) -> Optional[Dict]:
        """Get sensor's SS information"""
        try:
            sensor = await self._get_sensor(sensor_id, db)
            if not sensor:
                return None

            # Get limits
            result = await db.execute(
                select(SSSensorLimit).where(SSSensorLimit.sensor_id == sensor.id)
            )
            limits = result.scalars().all()

            selected_limit = next(
                (limit for limit in limits if limit.is_selected), None
            )

            return {
                "sensor_id": sensor_id,
                "pattern": sensor.pattern,
                "sensor_type": (
                    sensor.sensor_type_obj.name if sensor.sensor_type_obj else "unknown"
                ),
                "active": sensor.is_active,
                "limit_name": selected_limit.name if selected_limit else None,
                "limit_config": (
                    selected_limit.to_dict(include_relationships=False)
                    if selected_limit
                    else None
                ),
                "all_limits": [
                    limit.to_dict(include_relationships=False) for limit in limits
                ],
            }
        except Exception as e:
            logger.error(f"Error getting sensor info for {sensor_id}: {e}")
            return None

    async def get_all_sensors(
        self, check_activeness: bool, db: AsyncSession
    ) -> List[Dict]:
        """Get all sensors"""
        try:
            query = select(SSSensor)
            if check_activeness:
                query = query.where(SSSensor.is_active == True)
            query = query.options(
                selectinload(SSSensor.sensor_type_obj),
                selectinload(SSSensor.limits),
                selectinload(SSSensor.alerts),
            )
            result = await db.execute(query)
            sensors = result.scalars().all()

            sensor_list = []
            for sensor in sensors:
                limits = sensor.limits if hasattr(sensor, "limits") else []
                alerts = sensor.alerts if hasattr(sensor, "alerts") else []
                selected_limit = next((l for l in limits if l.is_selected), None)

                sensor_dict = {
                    "id": sensor.id,
                    "sensor_id": sensor.sensor_id,
                    "pattern": sensor.pattern,
                    "sensor_type": (
                        sensor.sensor_type_obj.name
                        if sensor.sensor_type_obj
                        else "unknown"
                    ),
                    "is_active": sensor.is_active,
                    "limits": [
                        limit.to_dict(include_relationships=False) for limit in limits
                    ],
                    "selected_limit": (
                        selected_limit.to_dict(include_relationships=False)
                        if selected_limit
                        else None
                    ),
                    "alerts": [
                        alert.to_dict(include_relationships=False) for alert in alerts
                    ],
                    "created_at": (
                        sensor.created_at.isoformat() if sensor.created_at else None
                    ),
                    "updated_at": (
                        sensor.updated_at.isoformat() if sensor.updated_at else None
                    ),
                }
                sensor_list.append(sensor_dict)

            return sensor_list
        except Exception as e:
            logger.error(f"Error getting all sensors:\n{traceback.format_exc()}")
            return []

    async def get_all_sensor_types(self, db: AsyncSession) -> Dict[str, Dict]:
        """Get all sensor types with caching"""
        now = datetime.now(timezone.utc)
        if (
            self._type_cache
            and self._type_cache_ts
            and now - self._type_cache_ts < self._cache_timeout
        ):
            return self._type_cache

        try:
            result = await db.execute(select(SSSensorType))
            types = result.scalars().all()
            self._type_cache = {
                type_obj.name: type_obj.to_dict(include_relationships=False)
                for type_obj in types
            }
            self._type_cache_ts = now
            return self._type_cache
        except Exception as e:
            logger.error(f"Error getting all sensor types: {e}")
            return {}

    async def get_alerts(
        self, limit: int, include_resolved: bool, db: AsyncSession
    ) -> List[Dict]:
        """Get alerts"""
        try:
            query = (
                select(SSAlert)
                .options(selectinload(SSAlert.sensor))
                .order_by(SSAlert.triggered_at.desc())
            )
            if limit != 0:
                query = query.limit(limit)
            if not include_resolved:
                query = query.where(SSAlert.is_resolved == False)
            result = await db.execute(query)
            alerts = result.scalars().all()

            return [alert.to_dict(include_relationships=True) for alert in alerts]
        except Exception as e:
            logging.error(f"Error in get_alerts:\n{traceback.format_exc()}")
            return []

    async def resolve_alert(self, alert_id: int, db: AsyncSession):
        """Mark an alert as resolved"""
        try:
            result = await db.execute(select(SSAlert).where(SSAlert.id == alert_id))
            alert = result.scalars().first()
            if alert:
                if not alert.is_resolved:
                    alert.is_resolved = True
                    alert.resolved_at = datetime.now(timezone.utc)
                    await db.flush()
                    logger.info(f"Resolved alert {alert_id}")
                else:
                    logger.warning(f"Alert {alert_id} is already resolved")
            else:
                logger.warning(f"Alert {alert_id} not found")
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            raise

    async def revert_alert(self, alert_id: int, db: AsyncSession):
        """Revert an alert resolve"""
        try:
            result = await db.execute(select(SSAlert).where(SSAlert.id == alert_id))
            alert = result.scalars().first()
            if alert:
                if alert.is_resolved:
                    alert.is_resolved = False
                    alert.resolved_at = None
                    await db.flush()
                    logger.info(f"Reverted alert {alert_id}")
                else:
                    logger.warning(f"Alert {alert_id} is already unresolved")
            else:
                logger.warning(f"Alert {alert_id} not found")
        except Exception as e:
            logger.error(f"Error reverting alert {alert_id}: {e}")
            raise


# Global SS manager instance
ss_manager: Optional[DatabaseSSManager] = None


def get_ss_manager() -> Optional[DatabaseSSManager]:
    """Get global SS manager instance"""
    return ss_manager


async def init_ss_manager(db: AsyncSession) -> DatabaseSSManager:
    """Initialize global database-backed SS manager"""
    global ss_manager
    ss_manager = DatabaseSSManager()
    await ss_manager._load_config(db)
    logger.info("Async database-backed SS manager initialized")
    return ss_manager
