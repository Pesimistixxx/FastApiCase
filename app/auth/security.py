import datetime
from typing import Annotated

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException, status

from db.db_depends import get_db
from app.auth.models import Session_model, User_model


async def verify_session(session_id: str,
                         db: AsyncSession):
    session = await db.scalar(select(Session_model).where(
        Session_model.session_token == session_id
    ))

    if session.expires <= datetime.datetime.now():
        await db.execute(delete(Session_model).where(
            Session_model.id==session.id
        ))
        await db.commit()
        return None

    user_id = session.user_id
    user = await db.scalar(select(User_model).where(
        User_model.id == user_id,
        User_model.is_active == True
    ))

    return user.username


async def get_user(request: Request,
                   db: Annotated[AsyncSession, Depends(get_db)]):
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    user = await verify_session(session_id, db)

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid session')

    return user
