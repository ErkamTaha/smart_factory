"""
Database initialization with default data (Async Version)
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl_models import (
    create_default_roles,
    create_default_acl_users,
    create_default_acl_config,
)
from app.models.ss_models import (
    create_default_sensor_types,
    create_default_sensors,
    create_default_ss_config,
)
from app.models.mqtt_models import create_default_mqtt_devices

logger = logging.getLogger(__name__)


async def create_default_data(db: AsyncSession):
    """Create default data for a fresh database (async)"""
    logger.info("Creating default data...")

    try:
        # MQTT defaults
        await create_default_mqtt_devices(db)

        # ACL defaults
        await create_default_roles(db)
        await create_default_acl_users(db)
        await create_default_acl_config(db)

        # SS defaults
        await create_default_sensor_types(db)
        await create_default_sensors(db)
        await create_default_ss_config(db)
        await db.commit()

        logger.info("Default data created successfully!")

    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        await db.rollback()
        raise
