import datetime
from typing import Annotated

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException, status

from db.db_depends import get_db
from app.auth.models import SessionModel, UserModel


async def verify_session(session_id: str,
                         db: AsyncSession):
    session = await db.scalar(select(SessionModel).where(
        SessionModel.session_token == session_id
    ))

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='You are not authorized'
        )
    if session.expires <= datetime.datetime.now():
        await db.execute(delete(SessionModel).where(
            SessionModel.id == session.id
        ))
        await db.commit()
        return None

    user_id = session.user_id
    user = await db.scalar(select(UserModel).where(
        UserModel.id == user_id,
        UserModel.is_active
    ))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    return user


async def get_user(request: Request,
                   db: Annotated[AsyncSession, Depends(get_db)]):
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    user = await verify_session(session_id, db)

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid session')

    return user


async def get_current_user_or_none(request: Request,
                                   db: Annotated[AsyncSession, Depends(get_db)]):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None

    try:
        return await verify_session(session_id, db)
    except HTTPException:
        return None
