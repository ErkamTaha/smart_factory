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
from app.database import SessionLocal
from contextlib import asynccontextmanager
from app.models.acl_models import ACLUser, ACLRole, ACLConfig, ACLAuditLog

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

    @staticmethod
    @asynccontextmanager
    async def _get_db():
        async with SessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    # -------------------------------
    #   CONFIG LOADING
    # -------------------------------
    async def _load_config(self):
        """Load ACL configuration from database"""
        try:
            async with self._get_db() as db:
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

    async def reload(self):
        """Reload ACL configuration"""
        await self._load_config()
        self._user_cache.clear()

    # -------------------------------
    #   TOPIC MATCHING
    # -------------------------------
    def _expand_topic_pattern(self, pattern: str, user_id: str) -> str:
        return pattern.replace("${user_id}", user_id)

    def _match_topic(self, topic: str, pattern: str) -> bool:
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

    async def _get_user(self, user_id: str) -> Optional[ACLUser]:
        async with self._get_db() as db:
            result = await db.execute(
                select(ACLUser)
                .where(ACLUser.user_id == user_id, ACLUser.is_active == True)
                .options(selectinload(ACLUser.roles))  # if you have this relationship
            )
            return result.scalars().first()

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get roles with caching"""
        now = datetime.now(timezone.utc)
        cached = self._user_cache.get(user_id)
        if cached and now - cached["ts"] < self._cache_timeout and cached.get("roles"):
            return cached["roles"]

        try:
            user = await self._get_user(user_id)
            roles = [r.name for r in user.roles] if user else []
            if cached:
                cached["roles"] = roles
                cached["ts"] = now
            else:
                self._user_cache[user_id] = {
                    "roles": roles,
                    "permissions": [],
                    "ts": now,
                }
            return roles
        except Exception as e:
            logger.error(f"Error getting roles for {user_id}: {e}")
            return []

    async def get_user_permissions(self, user_id: str) -> List[Dict]:
        """Get permissions with caching"""
        now = datetime.now(timezone.utc)
        cached = self._user_cache.get(user_id)
        if (
            cached
            and now - cached["ts"] < self._cache_timeout
            and cached.get("permissions")
        ):
            return cached["permissions"]

        try:
            user = await self._get_user(user_id)
            permissions = user.get_all_permissions() if user else []
            if cached:
                cached["permissions"] = permissions
                cached["ts"] = now
            else:
                self._user_cache[user_id] = {
                    "roles": [],
                    "permissions": permissions,
                    "ts": now,
                }
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for {user_id}: {e}")
            return []

    # -------------------------------
    #   PERMISSION CHECKING
    # -------------------------------
    async def check_permission(self, user_id: str, topic: str, action: str) -> bool:
        try:
            user = await self._get_user(user_id)
            if not user:
                await self._log_permission_check(
                    user_id, topic, action, "denied", "user_not_found"
                )
                return self.default_policy == "allow"

            user.last_login = datetime.now(timezone.utc)
            async with self._get_db() as db:
                await db.commit()

            permissions = await self.get_user_permissions(user_id)
            for p in permissions:
                pattern = self._expand_topic_pattern(p.get("pattern", ""), user_id)
                allow = p.get("allow", [])
                deny = p.get("deny", [])
                if self._match_topic(topic, pattern):
                    if action in deny:
                        await self._log_permission_check(
                            user_id, topic, action, "denied", "explicit_deny"
                        )
                        return False
                    if action in allow:
                        await self._log_permission_check(
                            user_id, topic, action, "allowed", "permission_match"
                        )
                        return True

            await self._log_permission_check(
                user_id, topic, action, "denied", "no_match"
            )
            return self.default_policy == "allow"

        except Exception as e:
            logger.error(f"Error checking permission for {user_id}: {e}")
            await self._log_permission_check(user_id, topic, action, "error", str(e))
            return False

    async def _log_permission_check(
        self, user_id: str, topic: str, action: str, result: str, reason: str
    ):
        try:
            async with self._get_db() as db:
                entry = ACLAuditLog(
                    user_id=user_id,
                    action="permission_check",
                    resource=f"{action}:{topic}",
                    result=result,
                    details={"reason": reason},
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.error(f"Error logging permission check: {e}")

    async def can_subscribe(self, user_id: str, topic: str) -> bool:
        return await self.check_permission(user_id, topic, "subscribe")

    async def can_publish(self, user_id: str, topic: str) -> bool:
        return await self.check_permission(user_id, topic, "publish")

    # -------------------------------
    #   USER MANAGEMENT
    # -------------------------------
    async def add_user(
        self,
        user_id: str,
        roles: List[str],
        custom_permissions: Optional[List[Dict]] = None,
    ):
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).where(ACLUser.user_id == user_id)
                )
                existing = result.scalars().first()
                if existing:
                    raise ValueError(f"User {user_id} already exists")

                user = ACLUser(
                    user_id=user_id,
                    custom_permissions=custom_permissions or [],
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                for rn in roles:
                    result = await db.execute(select(ACLRole).where(ACLRole.name == rn))
                    role = result.scalars().first()
                    if role:
                        user.roles.append(role)
                    else:
                        logger.warning(f"Role {rn} does not exist")
                await db.commit()
        except Exception as e:
            logger.error(f"Error adding user: {e}")

    async def remove_user(self, user_id: str):
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).where(ACLUser.user_id == user_id)
                )
                user = result.scalars().first()
                if user:
                    user.is_active = False
                    await db.commit()
                    self._user_cache.pop(user_id, None)
                else:
                    logger.warning(f"User {user_id} not found")
        except Exception as e:
            logger.error(f"Error removing user: {e}")

    async def update_user_roles(self, user_id: str, roles: List[str]):
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).where(
                        ACLUser.user_id == user_id, ACLUser.is_active == True
                    )
                )
                user = result.scalars().first()
                if not user:
                    raise ValueError(f"User {user_id} not found")

                user.roles.clear()
                for rn in roles:
                    result = await db.execute(select(ACLRole).where(ACLRole.name == rn))
                    role = result.scalars().first()
                    if role:
                        user.roles.append(role)
                    else:
                        logger.warning(f"Role {rn} not found")
                await db.commit()

                # Update cache
                now = datetime.now(timezone.utc)
                cached = self._user_cache.get(user_id)
                if cached:
                    cached["roles"] = user.roles
                    cached["permissions"] = user.permissions
                    cached["ts"] = now
                else:
                    self._user_cache[user_id] = {
                        "roles": user.roles,
                        "permissions": user.permissions,
                        "ts": now,
                    }
        except Exception as e:
            logger.error(f"Error updating user roles: {e}")

    async def add_user_permission(self, user_id: str, permission: Dict):
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).where(
                        ACLUser.user_id == user_id, ACLUser.is_active == True
                    )
                )
                user = result.scalars().first()
                if not user:
                    raise ValueError(f"User {user_id} not found")
                if not user.custom_permissions:
                    user.custom_permissions = []
                user.custom_permissions.append(permission)
                await db.commit()

                # Update cache
                now = datetime.now(timezone.utc)
                cached = self._user_cache.get(user_id)
                if cached:
                    cached["roles"] = user.roles
                    cached["permissions"] = user.permissions
                    cached["ts"] = now
                else:
                    self._user_cache[user_id] = {
                        "roles": user.roles,
                        "permissions": user.permissions,
                        "ts": now,
                    }
        except Exception as e:
            logger.error(f"Error adding user permission: {e}")

    # -------------------------------
    #   INFO ENDPOINTS
    # -------------------------------
    async def get_acl_info(self) -> Dict:
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).where(ACLUser.is_active == True)
                )
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

    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        try:
            user = await self._get_user(user_id)
            if not user:
                return None
            return {
                "user_id": user.user_id,
                "roles": [r.name for r in user.roles],
                "permissions": await self.get_user_permissions(user_id),
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")

    async def get_all_users(self) -> List[Dict]:
        try:
            async with self._get_db() as db:
                result = await db.execute(
                    select(ACLUser).options(selectinload(ACLUser.roles))
                )
                users = result.scalars().all()

                user_list = []
                for user in users:
                    user_list.append(
                        {
                            "id": user.id,
                            "user_id": user.user_id,
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

    async def get_all_roles(self) -> Dict[str, Dict]:
        try:
            async with self._get_db() as db:
                result = await db.execute(select(ACLRole))
                roles = result.scalars().all()
                return {r.name: r.to_dict() for r in roles}
        except Exception as e:
            logger.error(f"Error getting all roles: {e}")


# -------------------------------
#   GLOBAL INSTANCE
# -------------------------------
acl_manager: Optional[DatabaseACLManager] = None


def get_acl_manager() -> Optional[DatabaseACLManager]:
    return acl_manager


async def init_acl_manager() -> DatabaseACLManager:
    global acl_manager
    acl_manager = DatabaseACLManager()
    await acl_manager._load_config()
    logger.info("Async database-backed ACL manager initialized")
    return acl_manager
