from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class PermissionCheck(BaseModel):
    username: str
    topic: str
    action: str  # "subscribe" or "publish"


class UserCreate(BaseModel):
    username: str
    roles: List[str]
    custom_permissions: Optional[List[Dict[str, Any]]] = None


class UserUpdate(BaseModel):
    roles: Optional[List[str]] = None
    custom_permissions: Optional[List[Dict[str, Any]]] = None


class Permission(BaseModel):
    pattern: str
    allow: List[str]
    deny: Optional[List[str]] = None
