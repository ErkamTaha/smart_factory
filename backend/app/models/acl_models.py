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
from sqlalchemy.sql import func
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ACLUser(Base):
    __tablename__ = "acl_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, index=True, nullable=False)
    custom_permissions = Column(JSON)  # Store custom permissions as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    roles = relationship("ACLRole", secondary="acl_user_roles", back_populates="users")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "roles": [role.name for role in self.roles],
            "custom_permissions": self.custom_permissions or [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

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


class ACLConfig(Base):
    __tablename__ = "acl_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    @classmethod
    def get_config_dict(cls, db):
        """Get all configuration as a dictionary"""
        configs = db.query(cls).all()
        return {config.key: config.value for config in configs}


class ACLAuditLog(Base):
    __tablename__ = "acl_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(
        String(50), nullable=False
    )  # "login", "permission_check", "role_change", etc.
    resource = Column(String(200))  # Topic, role name, etc.
    result = Column(String(20))  # "allowed", "denied", "error"
    details = Column(JSON)  # Additional details
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self):
        return {
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


# Helper functions for ACL operations
async def create_default_roles(db):
    """Create default ACL roles if they don't exist"""
    from sqlalchemy import select

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
