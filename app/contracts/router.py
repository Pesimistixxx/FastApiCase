import random
from typing import Annotated
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from app.contracts.schemas import ContractRequest
from app.models_associations import User_Skin_model
from app.auth.security import get_current_user_or_none
from app.skin.models import Skin_model
from db.db_depends import get_db

contractRouter = APIRouter(prefix='/contract', tags=['skins', 'contracts'])
templates = Jinja2Templates(directory='templates')


@contractRouter.get('/')
async def get_contract(request: Request,
                       db: Annotated[AsyncSession, Depends(get_db)],
                       user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/user/login')

    user_skins = await db.scalars(select(User_Skin_model).where(
        User_Skin_model.user_id == user.id,
        User_Skin_model.is_active,
    ).options(selectinload(User_Skin_model.skin))
     .order_by(desc('id')))

    return templates.TemplateResponse('contracts.html', {'request': request,
                                                         'user': user,
                                                         'balance': user.balance,
                                                         'username': user.username,
                                                         'user_skins': user_skins.all(),
                                                         'is_admin': user.is_admin})


@contractRouter.post('/')
async def post_contract(db: Annotated[AsyncSession, Depends(get_db)],
                        skins: ContractRequest,
                        user: User_model | None = Depends(get_current_user_or_none),
                        ):
    if not user:
        return RedirectResponse('/user/login')

    total_price = 0
    user_skins = await db.scalars(select(User_Skin_model).where(
        User_Skin_model.user_id == user.id,
        User_Skin_model.id.in_(skins.skins),
        User_Skin_model.is_active
    ).options(selectinload(User_Skin_model.skin)))

    user.contracts_cnt += 1
    user.activity_points += 30

    for skin in user_skins.all():
        skin.is_active = False
        total_price += skin.skin.price
    drop_price = random.randint(int(total_price * 0.6), int(total_price * 1.5))

    dropped_skin = await db.scalar(select(Skin_model).where(
        Skin_model.price < drop_price,
        Skin_model.is_active
    ).order_by(desc(Skin_model.price))
     .limit(1))

    if dropped_skin.price > total_price:
        user.successful_contracts_cnt += 1
        user.activity_points += 15

    result = await db.execute(insert(User_Skin_model).values(
        user_id=user.id,
        skin_id=dropped_skin.id
    ).returning(User_Skin_model.id))
    user_skin_id = result.scalar_one()

    await db.commit()

    dropped_skin_obj = await db.scalar(select(User_Skin_model)
                                       .where(User_Skin_model.id == user_skin_id)
                                       .options(selectinload(User_Skin_model.skin)))
    return {
        'status': status.HTTP_200_OK,
        'dropped_skin': user_skin_id,
        'dropped_skin_image': dropped_skin_obj.skin.image if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_name': dropped_skin_obj.skin.name if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_price': dropped_skin_obj.skin.price if dropped_skin_obj and dropped_skin_obj.skin else None
    }
