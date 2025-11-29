"""
Database initialization with default data (Async Version)
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl_models import create_default_roles, ACLUser, ACLRole, ACLConfig
from app.models.ss_models import (
    create_default_sensor_types,
    create_default_sensors,
    SSConfig
)
from app.models.mqtt_models import create_or_update_device

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
#   MAIN ENTRY POINT
# ---------------------------------------------------------
async def create_default_data(db: AsyncSession):
    """Create default data for a fresh database (async)"""
    logger.info("Creating default data...")

    try:
        # ACL defaults
        await create_default_roles(db)
        await create_default_acl_users(db)
        await create_default_acl_config(db)

        # SS defaults
        await create_default_sensor_types(db)
        await create_default_sensors(db)
        await create_default_ss_config(db)

        logger.info("Default data created successfully!")

    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        await db.rollback()
        raise


# ---------------------------------------------------------
#   DEFAULT ACL USERS
# ---------------------------------------------------------
async def create_default_acl_users(db: AsyncSession):
    """Create default ACL users"""
    default_users = [
        {"user_id": "alice", "roles": ["admin"]},
        {"user_id": "bob", "roles": ["operator"]},
        {"user_id": "charlie", "roles": ["viewer", "operator"]},
        {"user_id": "dave", "roles": ["device_owner"]},
        {"user_id": "eve", "roles": ["device_owner"]},
        {"user_id": "erkam", "roles": ["admin"]},
    ]

    for user_data in default_users:
        # Check if user exists
        result = await db.execute(
            select(ACLUser).where(ACLUser.user_id == user_data["user_id"])
        )
        existing = result.scalars().first()
        if existing:
            continue

        # Create user
        user = ACLUser(
            user_id=user_data["user_id"],
            is_active=True
        )
        db.add(user)
        await db.flush()  # Get generated ID

        # Assign roles
        for role_name in user_data["roles"]:
            result = await db.execute(
                select(ACLRole).where(ACLRole.name == role_name)
            )
            role = result.scalars().first()
            if role:
                user.roles.append(role)

    # Custom permissions — Bob
    result = await db.execute(select(ACLUser).where(ACLUser.user_id == "bob"))
    bob = result.scalars().first()
    if bob and not bob.custom_permissions:
        bob.custom_permissions = [
            {
                "pattern": "sf/sensors/room1/#",
                "allow": ["subscribe", "publish"]
            }
        ]

    # Custom permissions — Eve
    result = await db.execute(select(ACLUser).where(ACLUser.user_id == "eve"))
    eve = result.scalars().first()
    if eve and not eve.custom_permissions:
        eve.custom_permissions = [
            {
                "pattern": "sf/sensors/special/#",
                "allow": ["subscribe", "publish"]
            }
        ]

    await db.commit()


# ---------------------------------------------------------
#   DEFAULT ACL CONFIG
# ---------------------------------------------------------
async def create_default_acl_config(db: AsyncSession):
    """Create default ACL configuration"""
    default_configs = [
        {"key": "default_policy", "value": "deny",
         "description": "Default policy when no explicit permission is found"},
        {"key": "version", "value": "1.0",
         "description": "ACL configuration version"},
        {"key": "session_timeout", "value": "3600",
         "description": "Session timeout in seconds"},
        {"key": "max_failed_attempts", "value": "5",
         "description": "Maximum failed authentication attempts"},
    ]

    for config_data in default_configs:
        result = await db.execute(
            select(ACLConfig).where(ACLConfig.key == config_data["key"])
        )
        existing = result.scalars().first()

        if not existing:
            db.add(ACLConfig(**config_data))

    await db.commit()


# ---------------------------------------------------------
#   DEFAULT SS CONFIG
# ---------------------------------------------------------
async def create_default_ss_config(db: AsyncSession):
    """Create default SS configuration"""
    default_configs = [
        {"key": "version", "value": "1.0", "description": "SS configuration version"},
        {"key": "alert_cooldown", "value": "300", "description": "Alert cooldown seconds"},
        {"key": "enable_alerts", "value": "true", "description": "Enable alerts"},
        {"key": "alert_channels", "value": "websocket,email",
         "description": "Comma-separated alert channels"},
    ]

    for config_data in default_configs:
        result = await db.execute(
            select(SSConfig).where(SSConfig.key == config_data["key"])
        )
        existing = result.scalars().first()

        if not existing:
            db.add(SSConfig(**config_data))

    await db.commit()
