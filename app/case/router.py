import asyncio
from typing import Annotated
from sqlalchemy import select, insert, desc, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, Path, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.battles.lobby_manager import manager
from app.auth.models import UserModel
from app.auth.security import get_user, get_current_user_or_none
from app.battles.models import BattleModel
from app.models_associations import CaseSkinModel, UserSkinModel, UserBattleModel
from app.notification.models import NotificationModel
from app.utils.db_queries import get_user_notifications, get_unread_messages, get_user_new_notifications
from app.case.models import CaseModel
from app.skin.models import SkinModel
from app.case.schemas import CaseCreate, CaseOpen, CaseCalculateProbability
from app.case.probability import get_item_by_probability, calculate_probabilities
from db.db_depends import get_db

caseRouter = APIRouter(prefix='/case', tags=['case'])
templates = Jinja2Templates(directory='templates')


@caseRouter.get('/list')
async def get_case_list(db: Annotated[AsyncSession, Depends(get_db)]):
    cases = await db.scalars(select(CaseModel).where(
        CaseModel.is_active
    ))
    return cases.all()


@caseRouter.get('/create')
async def get_case_create(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/user/login')

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('case_create.html',
                                      {'request': request,
                                       'notifications': notifications.all(),
                                       'user': user,
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@caseRouter.post('/calculate_probability')
async def post_calculate_probability(db: Annotated[AsyncSession, Depends(get_db)],
                                     case_inp: CaseCalculateProbability):
    result = await db.scalars(select(SkinModel).where(
        SkinModel.id.in_(case_inp.skins)
    ))
    skins = result.all()

    probabilities = calculate_probabilities(skins,
                                            case_inp.sigma,
                                            case_inp.math_exception)
    skin_probabilities = {}
    for i, skin in enumerate(skins):
        skin_probabilities[skin.name] = probabilities[i]
    return {'status': status.HTTP_200_OK,
            'probabilities': skin_probabilities}


@caseRouter.post('/calculate_price')
async def post_calculate_case_price(db: Annotated[AsyncSession, Depends(get_db)],
                                    case_inp: CaseCalculateProbability):
    result = await db.scalars(select(SkinModel).where(
        SkinModel.id.in_(case_inp.skins)
    ))
    skins = result.all()

    probabilities = calculate_probabilities(skins,
                                            case_inp.sigma,
                                            case_inp.math_exception)

    mo = sum(skin.price * probability for skin, probability in zip(skins, probabilities))

    return {'status': status.HTTP_200_OK,
            'case_price': f'{mo:.0f}'
            }


@caseRouter.post('/create_case')
async def post_create_case(db: Annotated[AsyncSession, Depends(get_db)],
                           case_inp: CaseCreate,
                           user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/user/login')
    try:
        new_case = CaseModel(name=case_inp.name,
                             price=case_inp.price,
                             math_exception=case_inp.math_exception,
                             sigma=case_inp.sigma,
                             author_id=user.id)

        db.add(new_case)
        await db.flush()

    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Название кейса уже занято') from exc

    for skin_id in case_inp.skins:
        await db.execute(insert(CaseSkinModel).values(
            case_id=new_case.id,
            skin_id=skin_id
        ))

    user.activity_points += 100
    await db.commit()

    return {'status': status.HTTP_201_CREATED,
            'detail': 'created'}


@caseRouter.get('/{name}/edit')
async def get_edit_case(db: Annotated[AsyncSession, Depends(get_db)],
                        request: Request,
                        user: UserModel | None = Depends(get_current_user_or_none),
                        name: str = Path(),
                        ):
    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.name == name,
                                  CaseModel.is_active)
                           .options(selectinload(CaseModel.skins)))

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Case not found')

    if not user or not (user.is_admin or user.id == case.author_id):
        return RedirectResponse('/')

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('case_create.html',
                                      {'request': request,
                                       'username': user.username,
                                       'balance': user.balance,
                                       'avatar': user.avatar,
                                       'is_admin': user.is_admin,
                                       'case_data': case,
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@caseRouter.patch('/{name}/retrieve')
async def patch_case_retrieve(db: Annotated[AsyncSession, Depends(get_db)],
                              user: UserModel | None = Depends(get_current_user_or_none),
                              name: str = Path()):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.name == name))
    case.is_active = True
    await db.commit()


@caseRouter.patch('/{name}/reject')
async def patch_reject_case(db: Annotated[AsyncSession, Depends(get_db)],
                            name: str = Path(),
                            user: UserModel | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.name == name))
    case.is_active = False
    await db.commit()
    await db.refresh(case)
    return case


@caseRouter.patch('/{name}/approve')
async def patch_approve_case(db: Annotated[AsyncSession, Depends(get_db)],
                             name: str = Path(),
                             user: UserModel | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.name == name))
    author = await db.scalar(select(UserModel)
                             .where(UserModel.id == case.author_id))
    if author:
        author.activity_points += 900
        author.cases_create += 1
        await db.execute(insert(NotificationModel)
                         .values(notification_receiver_id=author.id,
                                 type='text',
                                 text=f'Ваш кейс {case.name} был одобрен, поздравляю!'))

    case.is_approved = True
    await db.commit()
    await db.refresh(case)
    return case


@caseRouter.patch('/{name}')
async def patch_case(db: Annotated[AsyncSession, Depends(get_db)],
                     case_inp: CaseCreate,
                     user: UserModel | None = Depends(get_current_user_or_none),
                     name: str = Path()):
    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.name == name,
                                  CaseModel.is_active)
                           .options(selectinload(CaseModel.skins)))
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Case not found')

    if not user or not (user.is_admin or user.id == case.author_id):
        return RedirectResponse('/')
    try:
        case.name = case_inp.name
        case.price = case_inp.price
        case.math_exception = case_inp.math_exception
        case.sigma = case_inp.sigma
        case.is_approved = False
        await db.execute(delete(CaseSkinModel)
                         .where(CaseSkinModel.case_id == case.id))

        for skin_id in case_inp.skins:
            await db.execute(insert(CaseSkinModel).values(
                case_id=case.id,
                skin_id=skin_id
            ))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Название кейса уже занято') from exc


@caseRouter.delete('/{name}')
async def delete_case(db: Annotated[AsyncSession, Depends(get_db)],
                      name: str = Path(),
                      user: UserModel | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Not allowed')

    case = await db.scalar(select(CaseModel).where(
        CaseModel.is_active,
        CaseModel.name == name
    ))
    case.is_active = False
    case.is_approved = False
    await db.commit()

    return {'status': status.HTTP_200_OK,
            'detail': 'case was deleted'}


@caseRouter.get('/skin_case')
async def get_skin_case(db: Annotated[AsyncSession, Depends(get_db)]):
    skin_case = await db.scalars(select(CaseSkinModel))
    return skin_case.all()


@caseRouter.get('/{name}')
async def get_case(request: Request,
                   db: Annotated[AsyncSession, Depends(get_db)],
                   user: UserModel | None = Depends(get_current_user_or_none),
                   name: str = Path()):
    case = await db.scalar(select(CaseModel).where(
        CaseModel.name == name
    ))

    if not case:
        return RedirectResponse('/')
    if user and (not case.is_approved and not user.is_admin):
        return RedirectResponse('/')

    last_skins = await db.scalars(
        select(UserSkinModel)
        .options(selectinload(UserSkinModel.skin))
        .order_by(desc('id'))
        .limit(15)
    )

    result = await db.scalars(
        select(SkinModel)
        .join(SkinModel.cases)
        .where(CaseModel.id == case.id, SkinModel.is_active)
        .order_by(SkinModel.price)
    )
    skins = result.all()

    author = await db.scalar(select(UserModel)
                             .where(UserModel.id == case.author_id,
                                    UserModel.is_active))

    if user:
        notifications = await get_user_notifications(db, user.id)
        new_notifications = await get_user_new_notifications(db, user.id)
        new_messages = await get_unread_messages(db, user.id)

        return templates.TemplateResponse('case_opener.html', {'request': request,
                                                               'user': user,
                                                               'skins': skins,
                                                               'case_name': case.name,
                                                               'case_price': case.price,
                                                               'case_image': case.image,
                                                               'last_skins': last_skins,
                                                               'author': author,
                                                               'notifications': notifications.all(),
                                                               'notifications_cnt': len(new_notifications.all()),
                                                               'new_messages_cnt': len(new_messages.all())
                                                               })

    return templates.TemplateResponse('case_opener.html', {'request': request,
                                                           'skins': skins,
                                                           'case_name': case.name,
                                                           'case_price': case.price,
                                                           'case_image': case.image,
                                                           'last_skins': last_skins,
                                                           'author': author,
                                                           'user': None})


@caseRouter.post('/{name}')
async def post_open_case(db: Annotated[AsyncSession, Depends(get_db)],
                         num_cases: CaseOpen,
                         name: str = Path(),
                         user: UserModel = Depends(get_user)
                         ):
    case = await db.scalar(select(CaseModel).where(
        CaseModel.is_active,
        CaseModel.name == name
    ))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Case not found'
        )

    if user.balance < (case.price * num_cases.cnt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Not enough money'
        )
    user.case_opened += num_cases.cnt
    user.activity_points += num_cases.cnt

    new_balance = user.balance - (case.price * num_cases.cnt)
    user.balance = new_balance

    author = await db.scalar(select(UserModel)
                             .where(UserModel.id == case.author_id))
    if author:
        author.balance += (case.price * num_cases.cnt) / 10000  # 0.01 % цены идет автору
        author.author_case_opened += num_cases.cnt
    case.opened_count += num_cases.cnt

    result = await db.scalars(
        select(SkinModel)
        .join(SkinModel.cases)
        .where(CaseModel.id == case.id,
               SkinModel.is_active))
    skins = result.all()

    '''
    Функцию get_item_by_probability не имеет смысла эвэйтить там нет
    ни одного места которое могло бы выполняться асинхронно(only CPU)
    '''

    dropped_items = get_item_by_probability(skins,
                                            case.sigma,
                                            case.math_exception,
                                            num_cases.cnt)

    user_skin_ids = []

    for skin in dropped_items:
        if skin.price >= case.price:
            user.successful_cases_cnt += 1
            user.activity_points += 1
        result = await db.execute(
            insert(UserSkinModel)
            .values(user_id=user.id, skin_id=skin.id)
            .returning(UserSkinModel.id)
        )
        user_skin_id = result.scalar_one()
        user_skin_ids.append(user_skin_id)

    result_items = []
    for i, skin in enumerate(dropped_items):
        result_items.append({
            "id": user_skin_ids[i],
            "name": skin.name,
            "price": str(skin.price),
            "image": skin.image,
        })
    await db.commit()

    return {'new_balance': new_balance,
            'skins': result_items}


@caseRouter.post('/battle/{name}')
async def post_open_case_battle(db: Annotated[AsyncSession, Depends(get_db)],
                                battle_id: int,
                                name: str = Path()):
    battle = await db.scalar(select(BattleModel)
                             .where(BattleModel.id == battle_id,
                                    BattleModel.is_active))

    if not battle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Battle not found'
        )
    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.is_active,
                                  CaseModel.name == name
                                  ))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Case not found'
        )

    result = await db.execute(
        select(UserBattleModel.user_id)
        .where(UserBattleModel.battle_id == battle.id)
    )
    user_ids = result.scalars().all()

    result = await db.scalars(
        select(SkinModel)
        .join(SkinModel.cases)
        .where(CaseModel.id == case.id,
               SkinModel.is_active))
    skins = result.all()

    items_by_player = {}
    items_by_player_sum = {}
    max_val = 0
    winner_id = None
    dropped_items = get_item_by_probability(skins,
                                            case.sigma,
                                            case.math_exception,
                                            battle.players_cnt * battle.case_cnt)
    for i, user_id in enumerate(user_ids):
        user_skins = dropped_items[0 + i: battle.players_cnt * battle.case_cnt: battle.players_cnt]
        items_by_player[user_id] = [skin.id for skin in user_skins]
        user_skins_price_sum = sum(skin.price for skin in user_skins)
        items_by_player_sum[user_id] = user_skins_price_sum

    for user_id in user_ids:
        if items_by_player_sum[user_id] > max_val:
            max_val = items_by_player_sum[user_id]
            winner_id = user_id

    for skin in dropped_items:
        await db.execute(
            insert(UserSkinModel)
            .values(user_id=winner_id,
                    skin_id=skin.id))

    for round_i in range(battle.case_cnt):
        for user_id, skins in items_by_player.items():
            if len(skins) > round_i:
                await manager.send_case_result(
                    battle_id,
                    user_id,
                    [skins[round_i]],
                    round_i
                )
        await asyncio.sleep(5)
    await db.commit()

    await manager.send_battle_end(battle_id, winner_id)

    return {'winner': winner_id,
            'dropped_user_skins': items_by_player,
            'dropped_user_skins_sum': items_by_player_sum
            }


@caseRouter.get('/{name}/chances')
async def get_case_chances(db: Annotated[AsyncSession, Depends(get_db)],
                           name: str = Path()):
    case = await db.scalar(select(CaseModel).where(
        CaseModel.is_active,
        CaseModel.name == name
    ))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Case not found'
        )

    result = await db.scalars(
        select(SkinModel)
        .join(SkinModel.cases)
        .where(CaseModel.id == case.id,
               SkinModel.is_active))
    skins = result.all()

    probabilities = calculate_probabilities(skins,
                                            case.sigma,
                                            case.math_exception)
    skin_probability = {}
    for i, skin in enumerate(skins):
        skin_probability[skin.name] = f'{probabilities[i] * 100:.2f}%'

    return skin_probability
