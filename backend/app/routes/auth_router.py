# app/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.acl_models import ACLUser
from backend.app.schemas.auth_schemas import UserCreate, UserOut, Token, TokenData
from backend.app.security.auth_security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Helper to get DB session (asynccontextmanager style if you have it)
@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate):
    async with SessionLocal() as db:
        new_user = ACLUser(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            is_active=True,
        )
        db.add(new_user)
        try:
            await db.commit()
            await db.refresh(new_user)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail="User with that username or email already exists",
            )

        return new_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm expects fields: username and password (form-data)
    async with SessionLocal() as db:
        result = await db.execute(
            select(ACLUser).where(ACLUser.username == form_data.username)
        )
        user = result.scalars().first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        token = create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}


# Use as dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    username = payload["sub"]
    async with SessionLocal() as db:
        result = await db.execute(select(ACLUser).where(ACLUser.username == username))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


@router.get("/me", response_model=UserOut)
async def me(current_user: ACLUser = Depends(get_current_user)):
    return current_user
