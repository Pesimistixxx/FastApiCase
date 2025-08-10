import random
from typing import Annotated
from sqlalchemy import select, desc, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse

from app.auth.models import UserModel
from app.auth.security import get_current_user_or_none
from app.models_associations import UserSkinModel
from app.skin.models import SkinModel
from app.utils.db_queries import get_user_notifications, get_user_new_notifications, get_unread_messages
from db.db_depends import get_db

upgradeRouter = APIRouter(prefix='/upgrade', tags=['skin', 'upgrade'])
templates = Jinja2Templates(directory='templates')


@upgradeRouter.get('/')
async def get_upgrade(db: Annotated[AsyncSession, Depends(get_db)],
                      request: Request,
                      user: UserModel | None = Depends(get_current_user_or_none
                                                       )):
    if not user:
        return RedirectResponse('/user/login')

    skins = await db.scalars(select(SkinModel).where(
        SkinModel.is_active,
        SkinModel.price != 0
    ).order_by('price'))

    user_skins = await db.scalars(
        select(UserSkinModel)
        .where(
            UserSkinModel.user_id == user.id,
            UserSkinModel.is_active
        )
        .options(selectinload(UserSkinModel.skin))
        .order_by(desc(UserSkinModel.id))
    )

    skins_all = skins.all()
    user_skins_all = user_skins.all()

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('upgrade.html', {'request': request,
                                                       'all_skins': skins_all,
                                                       'user_skins': user_skins_all,
                                                       'user': user,
                                                       'notifications_cnt': len(new_notifications.all()),
                                                       'new_messages_cnt': len(new_messages.all()),
                                                       'notifications': notifications.all(),
                                                       })


@upgradeRouter.post('/')
async def post_upgrade(db: Annotated[AsyncSession, Depends(get_db)],
                       user: UserModel | None = Depends(get_current_user_or_none),
                       chance: float = Form(...),
                       user_skin_id: int = Form(...),
                       market_skin_id: int = Form(...)
                       ):
    chance = chance * 100
    randint = random.randint(0, 10000)

    user_skin = await db.scalar((select(UserSkinModel).where(
        UserSkinModel.id == user_skin_id,
        UserSkinModel.user_id == user.id,
        UserSkinModel.is_active
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
        result = await db.execute(insert(UserSkinModel).values(
            user_id=user.id,
            skin_id=market_skin_id
        ).returning(UserSkinModel.id))
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
