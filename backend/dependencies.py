"""
Shared dependencies for Servex Holdings backend.
Contains dependency functions used across multiple routes.
"""
from fastapi import HTTPException, Request, Depends
from datetime import datetime, timezone

from database import db


async def get_current_user(request: Request) -> dict:
    """
    Get current user from session token (cookie or header).
    
    Args:
        request: FastAPI Request object
    
    Returns:
        User document dict
    
    Raises:
        HTTPException: 401 if not authenticated or session invalid/expired
    """
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Find user
    user_doc = await db.users.find_one(
        {"id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user_doc


async def get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    """
    Extract tenant_id from current user.
    
    Args:
        user: Current user dict from get_current_user dependency
    
    Returns:
        Tenant ID string
    
    Raises:
        HTTPException: 403 if user not associated with a tenant
    """
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User not associated with a tenant")
    return tenant_id
