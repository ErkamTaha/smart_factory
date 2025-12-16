"""
Async Database-backed ACL Manager for Smart Factory
Supports async SQLAlchemy sessions and caching
"""

import logging
from typing import Dict, List, Optional
import fnmatch
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.acl_models import ACLUser, ACLRole, ACLConfig, ACLAuditLog
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class DatabaseACLManager:
    """Async Database-backed Access Control List Manager with caching"""

    def __init__(self):
        self.last_loaded: Optional[datetime] = None
        self._config_cache: Dict[str, str] = {}
        self._cache_timeout = timedelta(minutes=5)
        self._user_cache: Dict[str, Dict] = (
            {}
        )  # user_id -> {'roles': [...], 'permissions': [...], 'ts': datetime}

    # -------------------------------
    #   CONFIG LOADING
    # -------------------------------
    async def _load_config(self):
        """Load ACL configuration from database"""
        try:
            session = SessionLocal()
            async with session as db:
                result = await db.execute(select(ACLConfig))
                configs = result.scalars().all()
                self._config_cache = {c.key: c.value for c in configs}
                self.default_policy = self._config_cache.get("default_policy", "deny")
                self.last_loaded = datetime.now(timezone.utc)
                logger.info(f"ACL config loaded, default_policy={self.default_policy}")
        except Exception as e:
            logger.error(f"Error loading ACL config: {e}")
            self.default_policy = "deny"
            self._config_cache = {}

    async def reload(self, db: AsyncSession):
        """Reload ACL configuration"""
        await self._load_config(db)
        self._user_cache.clear()

    # -------------------------------
    #   TOPIC MATCHING
    # -------------------------------
    def _expand_topic_pattern(self, pattern: str, username: str) -> str:
        """Expand topic pattern with username variable"""
        return pattern.replace("${username}", username).replace("${user_id}", username)

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """Match MQTT topic against pattern with wildcards"""
        mqtt_pattern = pattern.replace("+", "*").replace("#", "**")
        if "**" in mqtt_pattern:
            pattern_parts = mqtt_pattern.split("/")
            topic_parts = topic.split("/")
            if pattern_parts[-1] == "**":
                return fnmatch.fnmatch(
                    "/".join(topic_parts[: len(pattern_parts) - 1]),
                    "/".join(pattern_parts[:-1]),
                )
        return fnmatch.fnmatch(topic, mqtt_pattern)

    # -------------------------------
    #   USER DATA (CACHED)
    # -------------------------------

    async def _get_user(self, username: str, db: AsyncSession) -> Optional[ACLUser]:
        """Get user from database with relationships"""
        result = await db.execute(
            select(ACLUser)
            .where(ACLUser.username == username, ACLUser.is_active == True)
            .options(selectinload(ACLUser.roles))
        )
        return result.scalars().first()

    async def get_user_roles(self, username: str, db: AsyncSession) -> List[str]:
        """Get roles with caching"""
        now = datetime.now(timezone.utc)
        cached = self._user_cache.get(username)
        if cached and now - cached["ts"] < self._cache_timeout and cached.get("roles"):
            return cached["roles"]

        try:
            user = await self._get_user(username, db)
            roles = [r.name for r in user.roles] if user else []
            if cached:
                cached["roles"] = roles
                cached["ts"] = now
            else:
                self._user_cache[username] = {
                    "roles": roles,
                    "permissions": [],
                    "ts": now,
                }
            return roles
        except Exception as e:
            logger.error(f"Error getting roles for {username}: {e}")
            return []

    async def get_user_permissions(self, username: str, db: AsyncSession) -> List[Dict]:
        """Get permissions with caching"""
        now = datetime.now(timezone.utc)
        cached = self._user_cache.get(username)
        if (
            cached
            and now - cached["ts"] < self._cache_timeout
            and cached.get("permissions")
        ):
            return cached["permissions"]

        try:
            user = await self._get_user(username, db)
            permissions = user.get_all_permissions() if user else []
            if cached:
                cached["permissions"] = permissions
                cached["ts"] = now
            else:
                self._user_cache[username] = {
                    "roles": [],
                    "permissions": permissions,
                    "ts": now,
                }
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for {username}: {e}")
            return []

    # -------------------------------
    #   PERMISSION CHECKING
    # -------------------------------
    async def check_permission(
        self, username: str, topic: str, action: str, db: AsyncSession
    ) -> bool:
        """Check if user has permission for topic/action"""
        try:
            user = await self._get_user(username, db)
            if not user:
                await self._log_permission_check(
                    username, topic, action, "denied", "user_not_found", db
                )
                return self.default_policy == "allow"

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            await db.flush()

            permissions = await self.get_user_permissions(username, db)
            for p in permissions:
                pattern = self._expand_topic_pattern(p.get("pattern", ""), username)
                allow = p.get("allow", [])
                deny = p.get("deny", [])
                if self._match_topic(topic, pattern):
                    if action in deny:
                        await self._log_permission_check(
                            username, topic, action, "denied", "explicit_deny", db
                        )
                        return False
                    if action in allow:
                        await self._log_permission_check(
                            username, topic, action, "allowed", "permission_match", db
                        )
                        return True

            await self._log_permission_check(
                username, topic, action, "denied", "no_match", db
            )
            return self.default_policy == "allow"

        except Exception as e:
            logger.error(f"Error checking permission for {username}: {e}")
            await self._log_permission_check(
                username, topic, action, "error", str(e), db
            )
            return False

    async def _log_permission_check(
        self,
        username: str,
        topic: str,
        action: str,
        result: str,
        reason: str,
        db: AsyncSession,
    ):
        """Log permission check to audit log"""
        try:
            entry = ACLAuditLog(
                username=username,
                action="permission_check",
                resource=f"{action}:{topic}",
                result=result,
                details={"reason": reason},
            )
            db.add(entry)
            await db.flush()
        except Exception as e:
            logger.error(f"Error logging permission check: {e}")

    async def can_subscribe(self, username: str, topic: str, db: AsyncSession) -> bool:
        """Check if user can subscribe to topic"""
        return await self.check_permission(username, topic, "subscribe", db)

    async def can_publish(self, username: str, topic: str, db: AsyncSession) -> bool:
        """Check if user can publish to topic"""
        return await self.check_permission(username, topic, "publish", db)

    # -------------------------------
    #   USER MANAGEMENT
    # -------------------------------
    async def add_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        roles: List[str],
        custom_permissions: Optional[List[Dict]],
        db: AsyncSession,
    ):
        """Add a new user"""
        try:
            result = await db.execute(
                select(ACLUser).where(ACLUser.username == username)
            )
            existing = result.scalars().first()
            if existing:
                raise ValueError(f"User {username} already exists")

            user = ACLUser(
                username=username,
                email=email,
                hashed_password=hashed_password,
                custom_permissions=custom_permissions or [],
                is_active=True,
            )
            db.add(user)
            await db.flush()

            for role_name in roles:
                result = await db.execute(
                    select(ACLRole).where(ACLRole.name == role_name)
                )
                role = result.scalars().first()
                if role:
                    user.roles.append(role)
                else:
                    logger.warning(f"Role {role_name} does not exist")

            await db.flush()
            return user
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            raise

    async def remove_user(self, username: str, db: AsyncSession):
        """Remove user (soft delete)"""
        try:
            result = await db.execute(
                select(ACLUser).where(ACLUser.username == username)
            )
            user = result.scalars().first()
            if user:
                user.is_active = False
                await db.flush()
                self._user_cache.pop(username, None)
            else:
                logger.warning(f"User {username} not found")
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            raise

    async def update_user_roles(
        self, username: str, roles: List[str], db: AsyncSession
    ):
        """Update user roles"""
        try:
            result = await db.execute(
                select(ACLUser)
                .where(ACLUser.username == username, ACLUser.is_active == True)
                .options(selectinload(ACLUser.roles))
            )
            user = result.scalars().first()
            if not user:
                raise ValueError(f"User {username} not found")

            user.roles.clear()
            for role_name in roles:
                result = await db.execute(
                    select(ACLRole).where(ACLRole.name == role_name)
                )
                role = result.scalars().first()
                if role:
                    user.roles.append(role)
                else:
                    logger.warning(f"Role {role_name} not found")

            await db.flush()

            # Update cache
            now = datetime.now(timezone.utc)
            cached = self._user_cache.get(username)
            if cached:
                cached["roles"] = [r.name for r in user.roles]
                cached["permissions"] = user.get_all_permissions()
                cached["ts"] = now
            else:
                self._user_cache[username] = {
                    "roles": [r.name for r in user.roles],
                    "permissions": user.get_all_permissions(),
                    "ts": now,
                }
        except Exception as e:
            logger.error(f"Error updating user roles: {e}")
            raise

    async def add_user_permission(
        self, username: str, permission: Dict, db: AsyncSession
    ):
        """Add custom permission to user"""
        try:
            result = await db.execute(
                select(ACLUser).where(
                    ACLUser.username == username, ACLUser.is_active == True
                )
            )
            user = result.scalars().first()
            if not user:
                raise ValueError(f"User {username} not found")

            if not user.custom_permissions:
                user.custom_permissions = []
            user.custom_permissions.append(permission)
            await db.flush()

            # Update cache
            now = datetime.now(timezone.utc)
            cached = self._user_cache.get(username)
            if cached:
                cached["roles"] = [r.name for r in user.roles]
                cached["permissions"] = user.get_all_permissions()
                cached["ts"] = now
            else:
                self._user_cache[username] = {
                    "roles": [r.name for r in user.roles],
                    "permissions": user.get_all_permissions(),
                    "ts": now,
                }
        except Exception as e:
            logger.error(f"Error adding user permission: {e}")
            raise

    # -------------------------------
    #   INFO ENDPOINTS
    # -------------------------------
    async def get_acl_info(self, db: AsyncSession) -> Dict:
        """Get ACL system info"""
        try:
            result = await db.execute(select(ACLUser).where(ACLUser.is_active == True))
            total_users = len(result.scalars().all())

            result = await db.execute(select(ACLRole))
            total_roles = len(result.scalars().all())

            return {
                "version": self._config_cache.get("version", "unknown"),
                "default_policy": getattr(self, "default_policy", "deny"),
                "total_users": total_users,
                "total_roles": total_roles,
                "last_loaded": (
                    self.last_loaded.isoformat() if self.last_loaded else None
                ),
                "storage": "database",
            }
        except Exception as e:
            logger.error(f"Error getting ACL info: {e}")
            return {}

    async def get_user_info(self, username: str, db: AsyncSession) -> Optional[Dict]:
        """Get user info"""
        try:
            user = await self._get_user(username, db)
            if not user:
                return None
            return {
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
                "permissions": user.get_all_permissions(),
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    async def get_all_users(self, db: AsyncSession) -> List[Dict]:
        """Get all users"""
        try:
            result = await db.execute(
                select(ACLUser).options(selectinload(ACLUser.roles))
            )
            users = result.scalars().all()

            user_list = []
            for user in users:
                user_list.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "roles": [r.name for r in user.roles],
                        "custom_permissions": user.custom_permissions or [],
                        "all_permissions": user.get_all_permissions(),
                        "is_active": user.is_active,
                        "created_at": (
                            user.created_at.isoformat() if user.created_at else None
                        ),
                        "updated_at": (
                            user.updated_at.isoformat() if user.updated_at else None
                        ),
                        "last_login": (
                            user.last_login.isoformat() if user.last_login else None
                        ),
                    }
                )

            return user_list
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_all_roles(self, db: AsyncSession) -> Dict[str, Dict]:
        """Get all roles"""
        try:
            result = await db.execute(select(ACLRole))
            roles = result.scalars().all()
            return {r.name: r.to_dict(include_relationships=False) for r in roles}
        except Exception as e:
            logger.error(f"Error getting all roles: {e}")
            return {}


# -------------------------------
#   GLOBAL INSTANCE
# -------------------------------
acl_manager: Optional[DatabaseACLManager] = None


def get_acl_manager() -> Optional[DatabaseACLManager]:
    """Get global ACL manager instance"""
    return acl_manager


async def init_acl_manager() -> DatabaseACLManager:
    """Initialize global database-backed ACL manager"""
    global acl_manager
    acl_manager = DatabaseACLManager()
    await acl_manager._load_config()
    logger.info("Async database-backed ACL manager initialized")
    return acl_manager
