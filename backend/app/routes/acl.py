from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.security.acl_manager import get_acl_manager
from app.mqtt.user_client_manager import get_user_mqtt_manager

router = APIRouter(prefix="/api/acl", tags=["ACL Management"])


# Request models
class PermissionCheck(BaseModel):
    user_id: str
    topic: str
    action: str  # "subscribe" or "publish"


class UserCreate(BaseModel):
    user_id: str
    roles: List[str]
    custom_permissions: Optional[List[Dict[str, Any]]] = None


class UserUpdate(BaseModel):
    roles: Optional[List[str]] = None
    custom_permissions: Optional[List[Dict[str, Any]]] = None


class Permission(BaseModel):
    pattern: str
    allow: List[str]
    deny: Optional[List[str]] = None


# ACL Information Endpoints
@router.get("/info")
async def get_acl_info():
    """Get ACL configuration information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    return acl.get_acl_info()


@router.get("/users")
async def get_all_users():
    """Get list of all users in ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    users_list = []
    for user_id in acl.users.keys():
        user_info = acl.get_user_info(user_id)
        if user_info:
            users_list.append(user_info)

    return {"users": users_list, "count": len(users_list)}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get specific user's ACL information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    user_info = acl.get_user_info(user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found in ACL")

    return user_info


@router.get("/roles")
async def get_all_roles():
    """Get list of all available roles"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    return {"roles": acl.roles, "count": len(acl.roles)}


# Permission Check Endpoint
@router.post("/check")
async def check_permission(check: PermissionCheck):
    """Check if user has permission for action on topic"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    has_permission = acl.check_permission(check.user_id, check.topic, check.action)

    return {
        "user_id": check.user_id,
        "topic": check.topic,
        "action": check.action,
        "allowed": has_permission,
    }


# User Management Endpoints
@router.post("/users")
async def create_user(user: UserCreate):
    """Add a new user to ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    # Check if user already exists
    if user.user_id in acl.users:
        raise HTTPException(
            status_code=400, detail=f"User {user.user_id} already exists"
        )

    # Validate roles
    for role in user.roles:
        if role not in acl.roles:
            raise HTTPException(status_code=400, detail=f"Role {role} does not exist")

    acl.add_user(user.user_id, user.roles, user.custom_permissions)

    return {
        "message": f"User {user.user_id} created successfully",
        "user": acl.get_user_info(user.user_id),
    }


@router.put("/users/{user_id}")
async def update_user(user_id: str, update: UserUpdate):
    """Update user's roles or permissions"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    if user_id not in acl.users:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Update roles if provided
    if update.roles is not None:
        # Validate roles
        for role in update.roles:
            if role not in acl.roles:
                raise HTTPException(
                    status_code=400, detail=f"Role {role} does not exist"
                )
        acl.update_user_roles(user_id, update.roles)

    # Update custom permissions if provided
    if update.custom_permissions is not None:
        acl.users[user_id]["custom_permissions"] = update.custom_permissions
        acl._save_acl()

    # If user is currently connected, notify them about permission changes
    mqtt_manager = get_user_mqtt_manager()
    if mqtt_manager:
        user_client = mqtt_manager.get_user_client(user_id)
        if user_client:
            # Check current subscriptions against new permissions
            for topic in user_client.subscribed_topics[:]:
                if not acl.can_subscribe(user_id, topic):
                    # Permission revoked, force unsubscribe
                    user_client.unsubscribe(topic)
                    user_client._send_to_user(
                        {
                            "type": "permission_revoked",
                            "topic": topic,
                            "action": "subscribe",
                            "message": "Your subscription was removed due to permission change",
                        }
                    )

    return {
        "message": f"User {user_id} updated successfully",
        "user": acl.get_user_info(user_id),
    }


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Remove user from ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    if user_id not in acl.users:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # If user is connected, disconnect them
    mqtt_manager = get_user_mqtt_manager()
    if mqtt_manager:
        mqtt_manager.remove_user_client(user_id)

    acl.remove_user(user_id)

    return {"message": f"User {user_id} removed successfully"}


@router.post("/users/{user_id}/permissions")
async def add_user_permission(user_id: str, permission: Permission):
    """Add custom permission to user"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    if user_id not in acl.users:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    acl.add_user_permission(user_id, permission.model_dump())

    return {
        "message": f"Permission added to user {user_id}",
        "user": acl.get_user_info(user_id),
    }


# ACL Reload Endpoint
@router.post("/reload")
async def reload_acl():
    """Manually trigger ACL configuration reload"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    acl.reload()

    # Check all connected users and enforce new permissions
    mqtt_manager = get_user_mqtt_manager()
    if mqtt_manager:
        for user_id, user_client in mqtt_manager.user_clients.items():
            # Check subscriptions against new ACL
            for topic in user_client.subscribed_topics[:]:
                if not acl.can_subscribe(user_id, topic):
                    # Permission revoked, force unsubscribe
                    user_client.unsubscribe(topic)
                    user_client._send_to_user(
                        {
                            "type": "permission_revoked",
                            "topic": topic,
                            "action": "subscribe",
                            "message": "Your subscription was removed due to ACL reload",
                        }
                    )

    return {
        "message": "ACL configuration reloaded successfully",
        "info": acl.get_acl_info(),
    }


# Active Sessions Endpoint
@router.get("/sessions")
async def get_active_sessions():
    """Get active user sessions with their current permissions"""
    acl = get_acl_manager()
    mqtt_manager = get_user_mqtt_manager()

    if not mqtt_manager:
        return {"sessions": [], "count": 0}

    sessions = []
    for user_id, client in mqtt_manager.user_clients.items():
        session_info = {
            "user_id": user_id,
            "is_connected": client.is_connected,
            "subscribed_topics": client.subscribed_topics,
            "roles": [],
            "permissions_count": 0,
        }

        if acl:
            session_info["roles"] = acl.get_user_roles(user_id)
            session_info["permissions_count"] = len(acl.get_user_permissions(user_id))

        sessions.append(session_info)

    return {"sessions": sessions, "count": len(sessions)}
