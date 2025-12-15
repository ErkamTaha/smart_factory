# app/mqtt/emqx_auth.py
import httpx
import logging
from typing import Tuple, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class EMQXAuthManager:
    """Manage MQTT user credentials via EMQX HTTP API"""

    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        api_secret: str = None,
    ):
        self.api_url = (api_url or settings.EMQX_API_URL).rstrip("/")
        self.api_key = api_key or settings.EMQX_API_KEY
        self.api_secret = api_secret or settings.EMQX_API_SECRET

        # EMQX 5.x API endpoints
        self.auth_endpoint = f"{self.api_url}/api/v5/authentication/password_based:built_in_database/users"

        logger.info(f"EMQXAuthManager initialized with API URL: {self.api_url}")

    async def create_mqtt_user(
        self, mqtt_username: str, mqtt_password: str
    ) -> Tuple[bool, str]:
        """
        Create or update MQTT user in EMQX

        Returns: (success, message)
        """
        try:
            async with httpx.AsyncClient() as client:
                # Try to create user
                response = await client.post(
                    self.auth_endpoint,
                    json={
                        "user_id": mqtt_username,
                        "password": mqtt_password,
                        "is_superuser": False,  # Regular user, not admin
                    },
                    auth=(self.api_key, self.api_secret),
                    timeout=10.0,
                )

                if response.status_code == 201:
                    logger.info(f"✅ Created MQTT user: {mqtt_username}")
                    return True, "User created successfully"

                elif response.status_code == 409:
                    # User exists, update password instead
                    logger.info(f"🔄 MQTT user exists, updating: {mqtt_username}")
                    return await self.update_mqtt_user(mqtt_username, mqtt_password)

                else:
                    error_msg = f"Failed to create MQTT user: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return False, error_msg

        except httpx.ConnectError as e:
            error_msg = (
                f"Cannot connect to EMQX API at {self.api_url}. Is EMQX running?"
            )
            logger.error(f"{error_msg} - {str(e)}")
            return False, error_msg
        except httpx.TimeoutException as e:
            error_msg = f"EMQX API request timeout: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except httpx.RequestError as e:
            error_msg = f"EMQX API request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error creating MQTT user: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def update_mqtt_user(
        self, mqtt_username: str, mqtt_password: str
    ) -> Tuple[bool, str]:
        """Update existing MQTT user password"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.auth_endpoint}/{mqtt_username}",
                    json={"password": mqtt_password},
                    auth=(self.api_key, self.api_secret),
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info(f"✅ Updated MQTT user: {mqtt_username}")
                    return True, "User updated successfully"
                elif response.status_code == 204:
                    logger.info(f"✅ Updated MQTT user: {mqtt_username}")
                    return True, "User updated successfully"
                else:
                    error_msg = f"Failed to update MQTT user: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return False, error_msg

        except Exception as e:
            error_msg = f"Error updating MQTT user: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def delete_mqtt_user(self, mqtt_username: str) -> Tuple[bool, str]:
        """Delete MQTT user from EMQX"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.auth_endpoint}/{mqtt_username}",
                    auth=(self.api_key, self.api_secret),
                    timeout=10.0,
                )

                if response.status_code in (200, 204):
                    logger.info(f"🗑️  Deleted MQTT user: {mqtt_username}")
                    return True, "User deleted successfully"
                elif response.status_code == 404:
                    logger.warning(f"MQTT user not found: {mqtt_username}")
                    return True, "User not found (already deleted)"
                else:
                    error_msg = f"Failed to delete MQTT user: {response.status_code}"
                    logger.warning(error_msg)
                    return False, error_msg

        except Exception as e:
            error_msg = f"Error deleting MQTT user: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def list_mqtt_users(self) -> Tuple[bool, list]:
        """List all MQTT users"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.auth_endpoint,
                    auth=(self.api_key, self.api_secret),
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    users = data.get("data", [])
                    logger.info(f"Retrieved {len(users)} MQTT users")
                    return True, users
                else:
                    logger.error(f"Failed to list MQTT users: {response.status_code}")
                    return False, []

        except Exception as e:
            logger.error(f"Error listing MQTT users: {str(e)}")
            return False, []

    async def verify_connection(self) -> bool:
        """Verify EMQX API connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/api/v5/status",
                    auth=(self.api_key, self.api_secret),
                    timeout=5.0,
                )

                if response.status_code == 200:
                    logger.info("✅ EMQX API connection verified")
                    return True
                else:
                    logger.error(
                        f"❌ EMQX API connection failed: {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Cannot connect to EMQX API: {str(e)}")
            return False


# Global instance
_emqx_auth_manager: Optional[EMQXAuthManager] = None


def get_emqx_auth_manager() -> EMQXAuthManager:
    """Get global EMQX auth manager instance"""
    global _emqx_auth_manager
    if _emqx_auth_manager is None:
        _emqx_auth_manager = EMQXAuthManager()
    return _emqx_auth_manager


def init_emqx_auth_manager(
    api_url: str = None, api_key: str = None, api_secret: str = None
) -> EMQXAuthManager:
    """Initialize EMQX auth manager"""
    global _emqx_auth_manager
    _emqx_auth_manager = EMQXAuthManager(api_url, api_key, api_secret)
    return _emqx_auth_manager
