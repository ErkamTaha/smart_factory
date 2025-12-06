"""
Database manager for authentication operations
"""

import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.acl_models import ACLUser, ACLRole

logger = logging.getLogger(__name__)


class DatabaseAuthManager:
    """Database manager for authentication operations"""

    async def get_user_by_username(
        self, username: str, db: AsyncSession
    ) -> Optional[ACLUser]:
        """Get user by username"""
        try:
            result = await db.execute(
                select(ACLUser)
                .where(ACLUser.username == username)
                .options(selectinload(ACLUser.roles))
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    async def get_user_by_email(
        self, email: str, db: AsyncSession
    ) -> Optional[ACLUser]:
        """Get user by email"""
        try:
            result = await db.execute(
                select(ACLUser)
                .where(ACLUser.email == email)
                .options(selectinload(ACLUser.roles))
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        is_active: bool = True,
        is_superuser: bool = False,
        db: AsyncSession = None,
    ) -> ACLUser:
        """Create a new user"""
        try:
            # Check if username already exists
            existing_user = await self.get_user_by_username(username, db)
            if existing_user:
                raise ValueError(f"User with username '{username}' already exists")

            # Check if email already exists
            if email:
                existing_email = await self.get_user_by_email(email, db)
                if existing_email:
                    raise ValueError(f"User with email '{email}' already exists")

            # Create new user
            new_user = ACLUser(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=is_active,
                is_superuser=is_superuser,
            )
            db.add(new_user)
            await db.flush()

            # Refresh to get the user with relationships
            await db.refresh(new_user, ["roles"])

            logger.info(f"User {username} created successfully")
            return new_user

        except ValueError:
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error creating user {username}: {e}")
            raise ValueError("User with that username or email already exists") from e
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            raise

    async def assign_default_role(
        self, user: ACLUser, role_name: str, db: AsyncSession
    ):
        """Assign a default role to user"""
        try:
            result = await db.execute(select(ACLRole).where(ACLRole.name == role_name))
            role = result.scalars().first()

            if role:
                user.roles.append(role)
                await db.flush()
                logger.info(f"Assigned role {role_name} to user {user.username}")
            else:
                logger.warning(f"Role {role_name} not found")

        except Exception as e:
            logger.error(
                f"Error assigning role {role_name} to user {user.username}: {e}"
            )
            raise

    async def update_user_last_login(self, username: str, db: AsyncSession):
        """Update user's last login timestamp"""
        try:
            from datetime import datetime, timezone

            result = await db.execute(
                select(ACLUser).where(ACLUser.username == username)
            )
            user = result.scalars().first()

            if user:
                user.last_login = datetime.now(timezone.utc)
                await db.flush()
                logger.debug(f"Updated last login for user {username}")
            else:
                logger.warning(f"User {username} not found for last login update")

        except Exception as e:
            logger.error(f"Error updating last login for {username}: {e}")
            raise

    async def verify_user_credentials(
        self, username: str, password: str, verify_password_func, db: AsyncSession
    ) -> Optional[ACLUser]:
        """Verify user credentials and return user if valid"""
        try:
            user = await self.get_user_by_username(username, db)

            if not user:
                logger.warning(f"Login attempt for non-existent user: {username}")
                return None

            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {username}")
                return None

            if not verify_password_func(password, user.hashed_password):
                logger.warning(f"Invalid password for user: {username}")
                return None

            logger.info(f"Successful login for user: {username}")
            return user

        except Exception as e:
            logger.error(f"Error verifying credentials for {username}: {e}")
            return None

    async def get_user_with_permissions(
        self, username: str, db: AsyncSession
    ) -> Optional[dict]:
        """Get user with full permissions information"""
        try:
            user = await self.get_user_by_username(username, db)

            if not user:
                return None

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "roles": [role.name for role in user.roles] if user.roles else [],
                "permissions": user.get_all_permissions(),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }

        except Exception as e:
            logger.error(f"Error getting user with permissions for {username}: {e}")
            return None


# Global auth manager instance
auth_manager: Optional[DatabaseAuthManager] = None


def get_auth_manager() -> Optional[DatabaseAuthManager]:
    """Get global auth manager instance"""
    return auth_manager


def init_auth_manager() -> DatabaseAuthManager:
    """Initialize global database-backed auth manager"""
    global auth_manager
    auth_manager = DatabaseAuthManager()
    logger.info("Database-backed auth manager initialized")
    return auth_manager
