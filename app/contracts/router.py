import random
from typing import Annotated
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.achievement.models import AchievementModel
from app.auth.models import UserModel
from app.contracts.schemas import ContractRequest
from app.models_associations import UserSkinModel, UserAchievementModel
from app.auth.security import get_current_user_or_none
from app.notification.models import NotificationModel
from app.skin.models import SkinModel
from app.utils.db_queries import get_user_new_notifications, get_user_notifications, get_unread_messages
from db.db_depends import get_db

contractRouter = APIRouter(prefix='/contract', tags=['skins', 'contracts'])
templates = Jinja2Templates(directory='templates')


async def check_contract_achievements(
        db: AsyncSession,
        user: UserModel,
):
    achievements_map = {
        10: ('ВКонтракте', 'Поздравляем, вы получили достижение ВКонтракте'),
        100: ('Художник', 'Поздравляем, вы получили достижение Художник'),
        1000: ('Контрактный душ', 'Поздравляем, вы получили достижение Контрактный душ'),
        10000: ('Бизнесмен', 'Поздравляем, вы получили достижение Бизнесмен'),
    }

    for threshold, (name, message) in achievements_map.items():
        if user.contracts_cnt < threshold <= user.contracts_cnt + 1:
            achievement = await db.scalar(
                select(AchievementModel).where(AchievementModel.name == name)
            )
            if not achievement:
                continue

            exists_query = select(UserAchievementModel).where(
                UserAchievementModel.achievement_id == achievement.id,
                UserAchievementModel.user_id == user.id
            )
            user_achievement = await db.scalar(exists_query)

            if not user_achievement:
                await db.execute(
                    insert(NotificationModel).values(
                        notification_receiver_id=user.id,
                        type='achievement',
                        text=message
                    )
                )

                user.achievements_cnt += 1
                await db.execute(
                    insert(UserAchievementModel).values(
                        user_id=user.id,
                        achievement_id=achievement.id
                    )
                )


@contractRouter.get('/')
async def get_contract(request: Request,
                       db: Annotated[AsyncSession, Depends(get_db)],
                       user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/user/login')

    user_skins = await db.scalars(select(UserSkinModel).where(
        UserSkinModel.user_id == user.id,
        UserSkinModel.is_active,
    ).options(selectinload(UserSkinModel.skin))
     .order_by(desc('id')))

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('contract.html',
                                      {'request': request,
                                       'user': user,
                                       'user_skins': user_skins.all(),
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@contractRouter.post('/')
async def post_contract(db: Annotated[AsyncSession, Depends(get_db)],
                        skins: ContractRequest,
                        user: UserModel | None = Depends(get_current_user_or_none),
                        ):
    if not user:
        return RedirectResponse('/user/login')

    total_price = 0
    user_skins = await db.scalars(select(UserSkinModel).where(
        UserSkinModel.user_id == user.id,
        UserSkinModel.id.in_(skins.skins),
        UserSkinModel.is_active
    ).options(selectinload(UserSkinModel.skin)))

    await check_contract_achievements(db=db, user=user)
    user.contracts_cnt += 1
    user.activity_points += 30

    for skin in user_skins.all():
        skin.is_active = False
        total_price += skin.skin.price
    drop_price = random.randint(int(total_price * 0.6), int(total_price * 1.5))

    dropped_skin = await db.scalar(select(SkinModel).where(
        SkinModel.price < drop_price,
        SkinModel.is_active
    ).order_by(desc(SkinModel.price))
     .limit(1))

    if dropped_skin.price > total_price:
        user.successful_contracts_cnt += 1
        user.activity_points += 15

    result = await db.execute(insert(UserSkinModel).values(
        user_id=user.id,
        skin_id=dropped_skin.id
    ).returning(UserSkinModel.id))
    user_skin_id = result.scalar_one()

    await db.commit()

    dropped_skin_obj = await db.scalar(select(UserSkinModel)
                                       .where(UserSkinModel.id == user_skin_id)
                                       .options(selectinload(UserSkinModel.skin)))
    return {
        'status': status.HTTP_200_OK,
        'dropped_skin': user_skin_id,
        'dropped_skin_image': dropped_skin_obj.skin.image if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_name': dropped_skin_obj.skin.name if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_price': dropped_skin_obj.skin.price if dropped_skin_obj and dropped_skin_obj.skin else None
    }
