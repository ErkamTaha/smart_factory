"""
ACL (Access Control List) API routes with database integration
"""

import logging
import traceback
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.managers.db_acl_manager import get_acl_manager
from app.mqtt.user_client import get_user_mqtt_manager
from app.schemas.acl_schemas import PermissionCheck, Permission, UserCreate, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/acl", tags=["ACL Management"])


# ACL Information Endpoints
@router.get("/info")
async def get_acl_info(db: AsyncSession = Depends(get_db)):
    """Get ACL configuration information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        info = await acl.get_acl_info(db)
        return info
    except Exception as e:
        logger.error(f"Error in get_acl_info:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_db)):
    """Get list of all users in ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        users_list = await acl.get_all_users(db)
        return users_list
    except Exception as e:
        logger.error(f"Error in get_all_users:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{username}")
async def get_user(username: str, db: AsyncSession = Depends(get_db)):
    """Get specific user's ACL information"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        user_info = await acl.get_user_info(username, db)
        if not user_info:
            raise HTTPException(
                status_code=404, detail=f"User {username} not found in ACL"
            )
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_all_roles(db: AsyncSession = Depends(get_db)):
    """Get list of all available roles"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        roles = await acl.get_all_roles(db)
        return roles
    except Exception as e:
        logger.error(f"Error in get_all_roles:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Permission Check Endpoint
@router.post("/check")
async def check_permission(check: PermissionCheck, db: AsyncSession = Depends(get_db)):
    """Check if user has permission for action on topic"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        has_permission = await acl.check_permission(
            check.username, check.topic, check.action, db
        )

        # Commit the permission check log
        await db.commit()

        return {
            "username": check.username,
            "topic": check.topic,
            "action": check.action,
            "allowed": has_permission,
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in check_permission:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# User Management Endpoints
@router.post("/users")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Add a new user to ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        new_user = await acl.add_user(
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            roles=user.roles,
            custom_permissions=user.custom_permissions,
            db=db,
        )

        # Commit the new user
        await db.commit()

        # Refresh to get the latest state with relationships
        await db.refresh(new_user)

        return {
            "message": f"User {user.username} created successfully",
            "user": await acl.get_user_info(user.username, db),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in create_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{username}")
async def update_user(
    username: str, update: UserUpdate, db: AsyncSession = Depends(get_db)
):
    """Update user's roles or permissions"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        # Update roles if provided
        if update.roles is not None:
            await acl.update_user_roles(username, update.roles, db)

        # Add custom permissions if provided
        if update.custom_permissions is not None:
            for permission in update.custom_permissions:
                await acl.add_user_permission(username, permission, db)

        # Commit all changes
        await db.commit()

        # If user is currently connected, notify them about permission changes
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            user_client = mqtt_manager.get_user_client(username)
            if user_client:
                # Check current subscriptions against new permissions
                for topic in user_client.subscribed_topics[:]:
                    if not await acl.can_subscribe(username, topic, db):
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

                # Commit the permission check logs
                await db.commit()

        return {
            "message": f"User {username} updated successfully",
            "user": await acl.get_user_info(username, db),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in update_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(username: str, db: AsyncSession = Depends(get_db)):
    """Remove user from ACL"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        # If user is connected, disconnect them
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            mqtt_manager.remove_user_client(username)

        await acl.remove_user(username, db)

        # Commit the deletion
        await db.commit()

        return {"message": f"User {username} removed successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in delete_user:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{username}/permissions")
async def add_user_permission(
    username: str, permission: Permission, db: AsyncSession = Depends(get_db)
):
    """Add custom permission to user"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        await acl.add_user_permission(username, permission.dict(), db)

        # Commit the permission addition
        await db.commit()

        return {
            "message": f"Permission added to user {username}",
            "user": await acl.get_user_info(username, db),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in add_user_permission:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ACL Reload Endpoint
@router.post("/reload")
async def reload_acl(db: AsyncSession = Depends(get_db)):
    """Manually trigger ACL configuration reload"""
    acl = get_acl_manager()
    if not acl:
        raise HTTPException(status_code=503, detail="ACL manager not available")

    try:
        await acl.reload(db)

        # Check all connected users and enforce new permissions
        mqtt_manager = get_user_mqtt_manager()
        if mqtt_manager:
            for username, user_client in mqtt_manager.user_clients.items():
                # Check subscriptions against new ACL
                for topic in user_client.subscribed_topics[:]:
                    if not await acl.can_subscribe(username, topic, db):
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

        # Commit any permission check logs
        await db.commit()

        return {
            "message": "ACL configuration reloaded successfully",
            "info": await acl.get_acl_info(db),
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in reload_acl:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
