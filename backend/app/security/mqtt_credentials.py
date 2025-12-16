# app/security/mqtt_credentials.py
import secrets
import logging
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.routes.acl_router import get_user
from app.security.auth_security import hash_password, verify_password
from app.mqtt.emqx_auth import get_emqx_auth_manager

logger = logging.getLogger(__name__)


class MQTTCredentialManager:
    """Manages persistent MQTT credentials for users"""

    @staticmethod
    def generate_mqtt_password() -> str:
        """Generate a secure random password for MQTT"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def get_or_create_mqtt_credentials(
        user_id: str, db: AsyncSession, force_regenerate: bool = False
    ) -> Tuple[str, str]:
        """
        Get existing MQTT credentials or create new ones.

        Args:
            user_id: The user's ID/username
            db: Database session
            force_regenerate: If True, generate new password even if one exists

        Returns:
            (mqtt_username, mqtt_password) tuple
        """
        user = await get_user(user_id, db)

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Check if user already has MQTT credentials and we're not forcing regeneration
        if user.mqtt_username and user.mqtt_password and not force_regenerate:
            # User has existing credentials
            logger.info(f"Using existing MQTT credentials for user {user_id}")
            return user.mqtt_username, user.mqtt_password

        else:
            # Create new credentials
            logger.info(f"Creating new MQTT credentials for user {user_id}")

            mqtt_password = MQTTCredentialManager.generate_mqtt_password()

            mqtt_username = f"mqtt_{user_id}"

            # Store in database
            user.mqtt_username = mqtt_username
            user.mqtt_password = mqtt_password
            user.mqtt_created_at = datetime.now(timezone.utc)
            user.mqtt_updated_at = datetime.now(timezone.utc)
            await db.commit()

            # Register with EMQX broker
            emqx_auth = get_emqx_auth_manager()
            if emqx_auth:
                success, message = await emqx_auth.create_mqtt_user(
                    mqtt_username, mqtt_password
                )
                if not success:
                    logger.error(f"Failed to create MQTT user in EMQX: {message}")
                    # Don't fail - MQTT connection will fail later with better error
            else:
                logger.warning("EMQX Auth Manager not available")

            logger.info(f"Created MQTT credentials for user {mqtt_username}")
            return mqtt_username, mqtt_password

    @staticmethod
    async def delete_mqtt_credentials(user_id: str, db: AsyncSession) -> bool:
        """
        Delete MQTT credentials for a user

        Args:
            user_id: The user's ID/username
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        user = await get_user(user_id, db)

        if not user or not user.mqtt_username:
            logger.warning(f"No MQTT credentials found for user {user_id}")
            return False

        mqtt_username = user.mqtt_username

        # Delete from EMQX
        emqx_auth = get_emqx_auth_manager()
        if emqx_auth:
            success, message = await emqx_auth.delete_mqtt_user(mqtt_username)
            if not success:
                logger.error(f"Failed to delete MQTT user from EMQX: {message}")

        # Clear from database
        user.mqtt_username = None
        user.mqtt_password = None
        user.mqtt_created_at = None
        user.mqtt_updated_at = None
        await db.commit()

        logger.info(f"Deleted MQTT credentials for user {user_id}")
        return True

    @staticmethod
    async def rotate_mqtt_password(user_id: str, db: AsyncSession) -> Tuple[str, str]:
        """
        Force rotation of MQTT password for security purposes.
        Useful for password reset or security breach response.

        Returns:
            (mqtt_username, new_mqtt_password) tuple
        """
        logger.info(f"Rotating MQTT password for user {user_id}")
        return await MQTTCredentialManager.get_or_create_mqtt_credentials(
            user_id, db, force_regenerate=True
        )
