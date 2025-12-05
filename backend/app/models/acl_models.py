"""
Database models for ACL (Access Control List) management
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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, select
from app.database import Base
from typing import List, Dict, Any


class ACLRole(Base):
    __tablename__ = "acl_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON)  # Store permissions as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("ACLUser", secondary="acl_user_roles", back_populates="roles")

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            result.update(
                {
                    "users_count": len(self.users) if self.users else 0,
                    "user_list": (
                        [user.username for user in self.users] if self.users else []
                    ),
                }
            )

        return result


class ACLUser(Base):
    __tablename__ = "acl_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=True)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    custom_permissions = Column(JSON)  # Store custom permissions as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    roles = relationship("ACLRole", secondary="acl_user_roles", back_populates="users")

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "custom_permissions": self.custom_permissions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

        if include_relationships:
            result.update(
                {
                    "roles": [role.name for role in self.roles] if self.roles else [],
                    "roles_details": (
                        [
                            role.to_dict(include_relationships=False)
                            for role in self.roles
                        ]
                        if self.roles
                        else []
                    ),
                }
            )

        return result

    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Get all permissions from roles and custom permissions"""
        permissions = []

        # Add role permissions
        for role in self.roles:
            if role.permissions:
                permissions.extend(role.permissions)

        # Add custom permissions
        if self.custom_permissions:
            permissions.extend(self.custom_permissions)

        return permissions


class ACLUserRole(Base):
    __tablename__ = "acl_user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("acl_users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("acl_roles.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String(100))  # Who assigned this role

    user = relationship("ACLUser")
    role = relationship("ACLRole")

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
        }

        if include_relationships:
            result.update(
                {
                    "username": self.user.username if self.user else None,
                    "role_name": self.role.name if self.role else None,
                }
            )

        return result


class ACLConfig(Base):
    __tablename__ = "acl_config"

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


class ACLAuditLog(Base):
    __tablename__ = "acl_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("acl_users.id"), nullable=False)
    action = Column(
        String(50), nullable=False
    )  # "login", "permission_check", "role_change", etc.
    resource = Column(String(200))  # Topic, role name, etc.
    result = Column(String(20))  # "allowed", "denied", "error"
    details = Column(JSON)  # Additional details
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("ACLUser")

    def to_dict(self, include_relationships=True):
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if include_relationships:
            result.update(
                {
                    "username": self.user.username if self.user else None,
                }
            )
        return result


# Helper functions for ACL operations
async def create_default_roles(db):
    """Create default ACL roles if they don't exist"""

    default_roles = [
        {
            "name": "admin",
            "description": "Full access to all topics",
            "permissions": [{"pattern": "#", "allow": ["subscribe", "publish"]}],
        },
        {
            "name": "operator",
            "description": "Can read all sensors, write to commands",
            "permissions": [
                {"pattern": "sf/sensors/#", "allow": ["subscribe"]},
                {"pattern": "sf/commands/#", "allow": ["publish"]},
            ],
        },
        {
            "name": "viewer",
            "description": "Read-only access to sensors",
            "permissions": [{"pattern": "sf/sensors/#", "allow": ["subscribe"]}],
        },
        {
            "name": "device_owner",
            "description": "Full access to own devices only",
            "permissions": [
                {
                    "pattern": "sf/sensors/${user_id}/#",
                    "allow": ["subscribe", "publish"],
                },
                {
                    "pattern": "sf/commands/${user_id}/#",
                    "allow": ["subscribe", "publish"],
                },
            ],
        },
    ]

    for role_data in default_roles:
        result = await db.execute(
            select(ACLRole).where(ACLRole.name == role_data["name"])
        )
        existing = result.scalars().first()
        if not existing:
            role = ACLRole(**role_data)
            db.add(role)

    await db.commit()


async def create_default_acl_users(db):
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
        user = ACLUser(user_id=user_data["user_id"], is_active=True)
        db.add(user)
        await db.flush()  # Get generated ID

        # Assign roles
        for role_name in user_data["roles"]:
            result = await db.execute(select(ACLRole).where(ACLRole.name == role_name))
            role = result.scalars().first()
            if role:
                user.roles.append(role)

    # Custom permissions — Bob
    result = await db.execute(select(ACLUser).where(ACLUser.user_id == "bob"))
    bob = result.scalars().first()
    if bob and not bob.custom_permissions:
        bob.custom_permissions = [
            {"pattern": "sf/sensors/room1/#", "allow": ["subscribe", "publish"]}
        ]

    # Custom permissions — Eve
    result = await db.execute(select(ACLUser).where(ACLUser.user_id == "eve"))
    eve = result.scalars().first()
    if eve and not eve.custom_permissions:
        eve.custom_permissions = [
            {"pattern": "sf/sensors/special/#", "allow": ["subscribe", "publish"]}
        ]

    await db.commit()


async def create_default_acl_config(db):
    """Create default ACL configuration"""
    default_configs = [
        {
            "key": "default_policy",
            "value": "deny",
            "description": "Default policy when no explicit permission is found",
        },
        {"key": "version", "value": "1.0", "description": "ACL configuration version"},
        {
            "key": "session_timeout",
            "value": "3600",
            "description": "Session timeout in seconds",
        },
        {
            "key": "max_failed_attempts",
            "value": "5",
            "description": "Maximum failed authentication attempts",
        },
    ]

    for config_data in default_configs:
        result = await db.execute(
            select(ACLConfig).where(ACLConfig.key == config_data["key"])
        )
        existing = result.scalars().first()

        if not existing:
            db.add(ACLConfig(**config_data))

    await db.commit()
