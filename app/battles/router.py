import json
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.websockets import WebSocketState
from sqlalchemy import select, insert, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.auth.models import UserModel
from app.auth.security import get_current_user_or_none, verify_session
from app.battles.lobby_manager import manager
from app.battles.models import BattleModel
from app.battles.schemas import BattleCreate
from app.case.models import CaseModel
from app.models_associations import UserBattleModel
from app.utils.db_queries import get_user_notifications, get_unread_messages, get_user_new_notifications
from db.db_depends import get_db

battleRouter = APIRouter(prefix='/battle', tags=['battle, user, skins'])
templates = Jinja2Templates(directory='templates')


@battleRouter.get('/')
async def get_battle_list(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    battles_users_cnt = (select(func.count(UserBattleModel.user_id))  # pylint: disable=not-callable
                         .where(UserBattleModel.battle_id == BattleModel.id)
                         .scalar_subquery())
    battles = await db.scalars(select(BattleModel)
                               .where(BattleModel.is_active,
                                      ~BattleModel.is_started,
                                      battles_users_cnt < BattleModel.players_cnt)
                               .options(selectinload(BattleModel.users)
                                        .selectinload(UserBattleModel.user)))
    battles_list = battles.all()
    user_battle_ids = set()
    for battle in battles_list:
        for ub in battle.users:
            if ub.user_id == user.id:
                user_battle_ids.add(battle.id)

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('battle_list.html',
                                      {'request': request,
                                       'user': user,
                                       'battles': battles_list,
                                       'user_battle_ids': user_battle_ids,
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@battleRouter.get('/create')
async def get_create_battle(request: Request,
                            db: Annotated[AsyncSession, Depends(get_db)],
                            user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    cases = await db.scalars(select(CaseModel)
                             .where(CaseModel.is_active,
                                    CaseModel.is_approved))

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('battle_create.html',
                                      {'request': request,
                                       'user': user,
                                       'cases': cases.all(),
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@battleRouter.post('/create')
async def post_create_battle(db: Annotated[AsyncSession, Depends(get_db)],
                             battle_create: BattleCreate,
                             user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.id == battle_create.case_id,
                                  CaseModel.is_active))
    if not case:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'case not found'
        }
    if user.balance < battle_create.case_cnt * case.price:
        return {
            'status': status.HTTP_400_BAD_REQUEST,
            'detail': 'not enough money'
        }
    user.balance -= battle_create.case_cnt * case.price

    new_battle = BattleModel(name=battle_create.name,
                             players_cnt=battle_create.players_cnt,
                             case_id=battle_create.case_id,
                             case_cnt=battle_create.case_cnt,
                             price=battle_create.case_cnt * case.price,
                             host=user.id)
    db.add(new_battle)
    await db.flush()
    new_battle_id = new_battle.id
    await db.execute(insert(UserBattleModel).values(
        user_id=user.id,
        battle_id=new_battle.id))

    await db.commit()
    return {"id": new_battle_id}


@battleRouter.post('/join/{battle_id}')
async def post_join_battle(db: Annotated[AsyncSession, Depends(get_db)],
                           battle_id: int = Path(),
                           user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/battle/', status_code=303)

    battle = await db.scalar(select(BattleModel)
                             .where(BattleModel.id == battle_id,
                                    BattleModel.is_active,
                                    ~BattleModel.is_started)
                             .options(selectinload(BattleModel.users).selectinload(UserBattleModel.user)))

    if (not battle or user.id in [ub.user_id for ub in battle.users]
            or user.balance < battle.price
            or len(battle.users) >= battle.players_cnt):
        return RedirectResponse('/battle/', status_code=303)
    user.balance -= battle.price

    await db.execute(insert(UserBattleModel).values(
        user_id=user.id,
        battle_id=battle.id))

    await db.commit()

    return RedirectResponse(f'/battle/{battle_id}', status_code=303)


@battleRouter.get('/{battle_id}')
async def get_battle_by_id(request: Request,
                           db: Annotated[AsyncSession, Depends(get_db)],
                           battle_id: int = Path(),
                           user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    battle = await db.scalar(select(BattleModel)
                             .where(BattleModel.id == battle_id,
                                    BattleModel.is_active,
                                    ~BattleModel.is_started)
                             .options(selectinload(BattleModel.users).selectinload(UserBattleModel.user)))

    if not battle or user.id not in [ub.user_id for ub in battle.users]:
        return RedirectResponse('/')

    case = await db.scalar(select(CaseModel)
                           .where(CaseModel.is_active,
                                  CaseModel.is_approved,
                                  CaseModel.id == battle.case_id)
                           .options(selectinload(CaseModel.skins)))
    user_battles = [ub.user for ub in battle.users]

    all_skins_serializable = [
        {
            "id": skin.id,
            "name": skin.name,
            "price": str(skin.price),
            "image": skin.image,
        }
        for skin in case.skins
    ]

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('battle.html',
                                      {'request': request,
                                       'user': user,
                                       'battle': battle,
                                       'user_battles': user_battles,
                                       'all_skins': all_skins_serializable,
                                       'case': case,
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@battleRouter.websocket('/{battle_id}/ws')
async def websocket_lobby(websocket: WebSocket,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          battle_id: int = Path()):
    cookies = websocket.cookies
    session_cookie = cookies.get('session_id')
    if not session_cookie:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = await verify_session(session_cookie, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except Exception as e:
        print(f"Session verification error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    battle = await db.scalar(select(BattleModel)
                             .where(BattleModel.id == battle_id)
                             .options(selectinload(BattleModel.users)))
    if not battle:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_in_battle = any(ub.user_id == user.id for ub in battle.users)
    if not user_in_battle:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(battle_id, websocket, db, user.id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "start_battle" and user.id == battle.host:
                    battle_to_start = await db.scalar(select(BattleModel)
                                                      .where(BattleModel.id == battle_id)
                                                      .options(selectinload(BattleModel.users)))
                    if battle_to_start and not battle_to_start.is_started:
                        battle_to_start.is_started = True
                        await db.refresh(battle_to_start, ['users'])
                        user_ids = [ub.user_id for ub in battle_to_start.users]
                        print(user_ids)
                        await db.execute(update(UserModel).where(UserModel.id.in_(user_ids)).values(
                            battles_cnt=UserModel.battles_cnt + 1
                        ))
                        await db.commit()
                        await manager.send_battle_started(battle_id)

            except json.JSONDecodeError:
                print("Invalid JSON received")
    except WebSocketDisconnect as e:
        if e.code == 4002:
            print(f"User {user.id} explicitly left battle {battle_id} immediately")
            await manager.disconnect_by_user(battle_id, user.id, db)
        elif e.code not in (1000, 1001):
            await manager.schedule_disconnect(battle_id, user.id, db)
    except Exception as e:
        print(f"Unexpected error in WebSocket: {e}")
        await manager.schedule_disconnect(battle_id, user.id, db)
    finally:
        async with manager.lock:
            if battle_id in manager.active_connections:
                if user.id in manager.active_connections[battle_id]:
                    if manager.active_connections[battle_id][user.id] == websocket:
                        del manager.active_connections[battle_id][user.id]

                if not manager.active_connections[battle_id]:
                    del manager.active_connections[battle_id]

        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1000)
            except Exception as e:
                print(f"Error closing WebSocket: {e}")

        await db.close()
