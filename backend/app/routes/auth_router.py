"""
Authentication API routes with database integration
"""

import logging
import traceback
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.database import get_db
from app.models.acl_models import ACLUser
from app.managers.db_auth_manager import get_auth_manager
from app.schemas.auth_schemas import UserCreate, UserOut, Token
from app.security.auth_security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    auth = get_auth_manager()
    if not auth:
        raise HTTPException(
            status_code=503, detail="Authentication manager not available"
        )

    try:
        # Hash the password
        hashed_password = hash_password(user_in.password)

        # Create user via manager
        new_user = await auth.create_user(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
            db=db,
        )

        # Assign default role if specified
        if hasattr(user_in, "default_role") and user_in.default_role:
            await auth.assign_default_role(new_user, user_in.default_role, db)
        else:
            # Assign 'viewer' role by default
            await auth.assign_default_role(new_user, "viewer", db)

        # Commit the transaction
        await db.commit()

        # Refresh to get latest state
        await db.refresh(new_user)

        logger.info(f"User {user_in.username} registered successfully")

        return new_user

    except ValueError as e:
        await db.rollback()
        logger.warning(f"Registration validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in register:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Failed to register user. Please try again."
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with username and password to get access token"""
    auth = get_auth_manager()
    if not auth:
        raise HTTPException(
            status_code=503, detail="Authentication manager not available"
        )

    try:
        # Verify credentials via manager
        user = await auth.verify_user_credentials(
            username=form_data.username,
            password=form_data.password,
            verify_password_func=verify_password,
            db=db,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login timestamp
        await auth.update_user_last_login(user.username, db)

        # Commit the last login update
        await db.commit()

        # Create access token
        token = create_access_token({"sub": user.username})

        logger.info(f"User {user.username} logged in successfully")

        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in login:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    current_user: ACLUser = Depends(lambda: get_current_user),
):
    """Get current authenticated user information"""
    return current_user


@router.get("/me/permissions")
async def get_current_user_permissions(
    current_user: ACLUser = Depends(lambda: get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's permissions"""
    auth = get_auth_manager()
    if not auth:
        raise HTTPException(
            status_code=503, detail="Authentication manager not available"
        )

    try:
        user_info = await auth.get_user_with_permissions(current_user.username, db)

        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in get_current_user_permissions:\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve user permissions"
        )


# Dependency to get current authenticated user
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> ACLUser:
    """
    Dependency to get current authenticated user from token
    Use this as a dependency in protected routes
    """
    auth = get_auth_manager()
    if not auth:
        raise HTTPException(
            status_code=503,
            detail="Authentication manager not available",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode and verify token
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = payload["sub"]

        # Get user from database
        user = await auth.get_user_by_username(username, db)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dependency to get current active superuser
async def get_current_superuser(
    current_user: ACLUser = Depends(get_current_user),
) -> ACLUser:
    """
    Dependency to ensure current user is a superuser
    Use this for admin-only routes
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges. Superuser access required.",
        )
    return current_user


# Optional: Token refresh endpoint
@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: ACLUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token for authenticated user"""
    auth = get_auth_manager()
    if not auth:
        raise HTTPException(
            status_code=503, detail="Authentication manager not available"
        )

    try:
        # Update last login
        await auth.update_user_last_login(current_user.username, db)
        await db.commit()

        # Create new token
        token = create_access_token({"sub": current_user.username})

        logger.info(f"Token refreshed for user {current_user.username}")

        return {"access_token": token, "token_type": "bearer"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error in refresh_token:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")
