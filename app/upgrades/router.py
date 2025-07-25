from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from sqlalchemy import select, desc, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.responses import RedirectResponse
import random

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none
from app.models_associations import User_Skin_model
from app.skin.models import Skin_model
from db.db_depends import get_db

upgradeRouter = APIRouter(prefix='/upgrade', tags=['skin', 'upgrade'])
templates = Jinja2Templates(directory='templates')


@upgradeRouter.get('/')
async def get_upgrade(db: Annotated[AsyncSession, Depends(get_db)],
                      request: Request,
                      user: User_model | None = Depends(get_current_user_or_none
                                                        )):
    if not user:
        return RedirectResponse('/user/login')

    skins = await db.scalars(select(Skin_model).where(
        Skin_model.is_active,
        Skin_model.price != 0
    ).order_by('price'))

    user_skins = await db.scalars(
        select(User_Skin_model)
        .where(
            User_Skin_model.user_id == user.id,
            User_Skin_model.is_active
        )
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc(User_Skin_model.id))
    )

    skins_all = skins.all()
    user_skins_all = user_skins.all()

    return templates.TemplateResponse('upgrade.html', {'request': request,
                                                       'all_skins': skins_all,
                                                       'user_skins': user_skins_all,
                                                       'user': user,
                                                       'balance': user.balance,
                                                       'username': user.username,
                                                       'is_admin': user.is_admin})


@upgradeRouter.post('/')
async def post_upgrade(db: Annotated[AsyncSession, Depends(get_db)],
                       user: User_model | None = Depends(get_current_user_or_none),
                       chance: float = Form(...),
                       user_skin_id: int = Form(...),
                       market_skin_id: int = Form(...)
                       ):
    chance = chance * 100
    randint = random.randint(0, 10000)

    user_skin = await db.scalar((select(User_Skin_model).where(
        User_Skin_model.id == user_skin_id,
        User_Skin_model.user_id == user.id,
        User_Skin_model.is_active
    )))

    if not user_skin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Skin not found'
        )

    user_skin.is_active = False
    user.upgrades_cnt += 1
    user.activity_points += 15

    if randint < chance:
        result = await db.execute(insert(User_Skin_model).values(
            user_id=user.id,
            skin_id=market_skin_id
        ).returning(User_Skin_model.id))
        user_skin_id = result.scalar_one()
        user.successful_upgrades_cnt += 1
        user.activity_points += (100 - chance // 100) // 2

        await db.commit()
        return {'is_success': True,
                'randint': randint / 100,
                'skin_id': user_skin_id}

    await db.commit()
    return {'is_success': False,
            'randint': randint / 100}
