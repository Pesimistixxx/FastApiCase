from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none
from app.case.models import Case_model
from db.db_depends import get_db

adminRouter = APIRouter(prefix='/admin', tags=['admin'])
templates = Jinja2Templates(directory='templates')


@adminRouter.get('')
async def get_admin_panel(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: User_model | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    cases = await db.scalars(select(Case_model)
                             .options(joinedload(Case_model.author))
                             .order_by(Case_model.is_approved))
    return templates.TemplateResponse('admin.html', {'request': request,
                                                     'username': user.username,
                                                     'balance': user.balance,
                                                     'user': user,
                                                     'cases': cases.all()})
