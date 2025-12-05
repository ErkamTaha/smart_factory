"""
ACL (Access Control List) API routes with database integration
"""

import logging, traceback
from fastapi import APIRouter, HTTPException, Query
from app.managers.db_acl_manager import get_acl_manager
from backend.app.mqtt.user_client import get_user_mqtt_manager
from app.schemas.acl_schemas import PermissionCheck, Permission, UserCreate, UserUpdate

router = APIRouter(prefix="/api/acl", tags=["ACL Management"])


# ACL Information Endpoints
@router.get("/info")
async def get_acl_info():
    """Get ACL configuration information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        return await acl.get_acl_info()
    except Exception as e:
        logging.error(f"Error in get_acl_info:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users():
    """Get list of all users in ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")
    try:
        users_list = await acl.get_all_users()

        return users_list
    except Exception as e:
        logging.error(f"Error in get_all_users:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user(username: str):
    """Get specific user's ACL information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")
    try:
        user_info = await acl.get_user_info(username)
        if not user_info:
            raise HTTPException(
                status_code=404, detail=f"User {username} not found in ACL"
            )

        return user_info
    except Exception as e:
        logging.error(f"Error in get_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_all_roles():
    """Get list of all available roles"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")
    try:
        roles = await acl.get_all_roles()
        return roles
    except Exception as e:
        logging.error(f"Error in get_all_roles:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Permission Check Endpoint
@router.post("/check")
async def check_permission(check: PermissionCheck):
    """Check if user has permission for action on topic"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")
    try:

        has_permission = await acl.check_permission(
            check.username, check.topic, check.action
        )

        return {
            "username": check.username,
            "topic": check.topic,
            "action": check.action,
            "allowed": has_permission,
        }
    except Exception as e:
        logging.error(f"Error in check_permission:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# User Management Endpoints
@router.post("/users")
async def create_user(user: UserCreate):
    """Add a new user to ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        await acl.add_user(user.username, user.roles, user.custom_permissions)

        return {
            "message": f"User {user.username} created successfully",
            "user": await acl.get_user_info(user.username),
        }
    except Exception as e:
        logging.error(f"Error in create_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{username}")
async def update_user(username: str, update: UserUpdate):
    """Update user's roles or permissions"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        # Update roles if provided
        if update.roles is not None:
            await acl.update_user_roles(username, update.roles)

        # Update custom permissions if provided
        if update.custom_permissions is not None:
            # Note: This would need to be implemented in the database manager
            # For now, we'll add each permission individually
            for permission in update.custom_permissions:
                await acl.add_user_permission(username, permission)

        # If user is currently connected, notify them about permission changes
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            user_client = mqtt_manager.get_user_client(username)
            if user_client:
                # Check current subscriptions against new permissions
                for topic in user_client.subscribed_topics[:]:
                    if not await acl.can_subscribe(username, topic):
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
            "message": f"User {username} updated successfully",
            "user": await acl.get_user_info(username),
        }
    except Exception as e:
        logging.error(f"Error in update_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(username: str):
    """Remove user from ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        # If user is connected, disconnect them
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            mqtt_manager.remove_user_client(username)

        await acl.remove_user(username)

        return {"message": f"User {username} removed successfully"}
    except Exception as e:
        logging.error(f"Error in delete_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{username}/permissions")
async def add_user_permission(username: str, permission: Permission):
    """Add custom permission to user"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        await acl.add_user_permission(username, permission.dict())

        return {
            "message": f"Permission added to user {username}",
            "user": acl.get_user_info(username),
        }
    except Exception as e:
        logging.error(f"Error in add_user_permission:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ACL Reload Endpoint
@router.post("/reload")
async def reload_acl():
    """Manually trigger ACL configuration reload"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        await acl.reload()

        # Check all connected users and enforce new permissions
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            for user_id, user_client in mqtt_manager.user_clients.items():
                # Check subscriptions against new ACL
                for topic in user_client.subscribed_topics[:]:
                    if not await acl.can_subscribe(user_id, topic):
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
            "info": await acl.get_acl_info(),
        }
    except Exception as e:
        logging.error(f"Error in reload_acl:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Active Sessions Endpoint
@router.get("/sessions")
async def get_active_sessions():
    """Get active user sessions with their current permissions"""
    acl = get_acl_manager()
    mqtt_manager = get_user_mqtt_manager()

    try:

        if not mqtt_manager:
            return {"sessions": [], "count": 0}

        sessions = []
        for username, client in mqtt_manager.user_clients.items():
            session_info = {
                "username": username,
                "is_connected": client.is_connected,
                "subscribed_topics": client.subscribed_topics,
                "roles": [],
                "permissions_count": 0,
            }

            if acl:
                session_info["roles"] = await acl.get_user_roles(username)
                session_info["permissions_count"] = len(
                    await acl.get_user_permissions(username)
                )

            sessions.append(session_info)

        return sessions
    except Exception as e:
        logging.error(f"Error in sessions:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
