from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...core.dependencies import get_current_user, get_admin_user
from ...database.session import get_async_session
from ...models.user import User
from ...schemas.session import SessionCreate, SessionRead, SessionListResponse
from ...services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/start", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_in: SessionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    return await session_service.start_session(db, current_user.id, session_in)

@router.get("", response_model=SessionListResponse)
async def get_sessions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_superuser:
        sessions = await session_service.get_all_sessions(db, skip=skip, limit=limit)
    else:
        sessions = await session_service.get_user_sessions(db, current_user.id, skip=skip, limit=limit)
    return {"items": sessions, "total": len(sessions)}

@router.get("/active", response_model=SessionRead)
async def get_active_session(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    session = await session_service.get_active_session(db, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session found")
    return session

@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    session = await session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")
    return session

@router.post("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    return await session_service.end_session(db, session_id, current_user.id, is_admin=current_user.is_superuser)
