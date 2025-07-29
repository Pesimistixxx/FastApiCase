import json
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Path, WebSocket, WebSocketDisconnect, status as ws_status
from fastapi.responses import RedirectResponse
from fastapi.websockets import WebSocketState
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none, verify_session
from app.battles.lobby_manager import manager
from app.battles.models import Battle_model
from app.battles.schemas import BattleCreate
from app.case.models import Case_model
from app.models_associations import User_Battle_model
from db.db_depends import get_db

battleRouter = APIRouter(prefix='/battle', tags=['battle, user, skins'])
templates = Jinja2Templates(directory='templates')


@battleRouter.get('/')
async def get_battle_list(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    battles = await db.scalars(select(Battle_model)
                               .where(Battle_model.is_active,
                                      ~Battle_model.is_started)
                               .options(
                                    selectinload(Battle_model.users)
                                    .selectinload(User_Battle_model.user)))

    battles_list = battles.all()
    user_battle_ids = set()
    for battle in battles_list:
        for ub in battle.users:
            if ub.user_id == user.id:
                user_battle_ids.add(battle.id)

    return templates.TemplateResponse('battle_list.html', {'request': request,
                                                           'user': user,
                                                           'balance': user.balance,
                                                           'username': user.username,
                                                           'is_admin': user.is_admin,
                                                           'battles': battles_list,
                                                           'user_battle_ids': user_battle_ids})


@battleRouter.get('/create')
async def get_create_battle(request: Request,
                            db: Annotated[AsyncSession, Depends(get_db)],
                            user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    cases = await db.scalars(select(Case_model)
                             .where(Case_model.is_active,
                                    Case_model.is_approved))
    return templates.TemplateResponse('battle_create.html', {'request': request,
                                                             'user': user,
                                                             'balance': user.balance,
                                                             'username': user.username,
                                                             'is_admin': user.is_admin,
                                                             'cases': cases.all()})


@battleRouter.post('/create')
async def post_create_battle(db: Annotated[AsyncSession, Depends(get_db)],
                             battle_create: BattleCreate,
                             user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    case = await db.scalar(select(Case_model)
                           .where(Case_model.id == battle_create.case_id,
                                  Case_model.is_active))
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

    new_battle = Battle_model(name=battle_create.name,
                              players_cnt=battle_create.players_cnt,
                              case_id=battle_create.case_id,
                              case_cnt=battle_create.case_cnt,
                              price=battle_create.case_cnt * case.price,
                              host=user.id)
    db.add(new_battle)
    await db.flush()
    new_battle_id = new_battle.id
    await db.execute(insert(User_Battle_model).values(
        user_id=user.id,
        battle_id=new_battle.id))

    await db.commit()
    return {"id": new_battle_id}


@battleRouter.post('/join/{id}')
async def post_join_battle(db: Annotated[AsyncSession, Depends(get_db)],
                           id: int = Path(),
                           user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/battle/', status_code=303)

    battle = await db.scalar(select(Battle_model)
                             .where(Battle_model.id == id,
                                    Battle_model.is_active,
                                    ~Battle_model.is_started)
                             .options(selectinload(Battle_model.users).selectinload(User_Battle_model.user)))

    if not battle or user.id in [ub.user_id for ub in battle.users] or user.balance < battle.price:
        return RedirectResponse('/battle/', status_code=303)
    user.balance -= battle.price

    await db.execute(insert(User_Battle_model).values(
        user_id=user.id,
        battle_id=battle.id))

    await db.commit()

    return RedirectResponse(f'/battle/{id}', status_code=303)


@battleRouter.get('/{id}')
async def get_battle_by_id(request: Request,
                           db: Annotated[AsyncSession, Depends(get_db)],
                           id: int = Path(),
                           user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    battle = await db.scalar(select(Battle_model)
                             .where(Battle_model.id == id,
                                    Battle_model.is_active,
                                    ~Battle_model.is_started)
                             .options(selectinload(Battle_model.users).selectinload(User_Battle_model.user)))

    if not battle or user.id not in [ub.user_id for ub in battle.users]:
        return RedirectResponse('/')

    case = await db.scalar(select(Case_model)
                           .where(Case_model.is_active,
                                  Case_model.is_approved,
                                  Case_model.id == battle.case_id)
                           .options(selectinload(Case_model.skins)))
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

    return templates.TemplateResponse('battle.html', {
        'request': request,
        'user': user,
        'balance': user.balance,
        'username': user.username,
        'is_admin': user.is_admin,
        'battle': battle,
        'user_battles': user_battles,
        'all_skins':  all_skins_serializable,
        'case': case
    })


@battleRouter.websocket('/{id}/ws')
async def websocket_lobby(websocket: WebSocket,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          id: int = Path()):
    cookies = websocket.cookies
    session_cookie = cookies.get('session_id')
    if not session_cookie:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = await verify_session(session_cookie, db)
        if not user:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
            return

    except Exception as e:
        print(f"Session verification error: {e}")
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    battle = await db.scalar(select(Battle_model)
                             .where(Battle_model.id == id)
                             .options(selectinload(Battle_model.users)))
    if not battle:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    user_in_battle = any(ub.user_id == user.id for ub in battle.users)
    if not user_in_battle:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(id, websocket, db, user.id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "start_battle" and user.id == battle.host:
                    battle_to_start = await db.get(Battle_model, id)
                    if battle_to_start and not battle_to_start.is_started:
                        battle_to_start.is_started = True
                        db.add(battle_to_start)
                        await db.commit()

            except json.JSONDecodeError:
                print("Invalid JSON received")
    except WebSocketDisconnect as e:
        if e.code == 4002:
            print(f"User {user.id} explicitly left battle {id} immediately")
            await manager.disconnect_by_user(id, user.id, db)
        elif e.code != 1000 and e.code != 1001:
            await manager.schedule_disconnect(id, user.id, db)
    except Exception as e:
        print(f"Unexpected error in WebSocket: {e}")
        await manager.schedule_disconnect(id, user.id, db)
    finally:
        async with manager.lock:
            if id in manager.active_connections:
                if user.id in manager.active_connections[id]:
                    if manager.active_connections[id][user.id] == websocket:
                        del manager.active_connections[id][user.id]

                if not manager.active_connections[id]:
                    del manager.active_connections[id]

        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1000)
            except Exception as e:
                print(f"Error closing WebSocket: {e}")

        await db.close()
