import asyncio
from typing import Dict, List, Tuple, Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketState, WebSocketDisconnect
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User_model
from app.battles.models import Battle_model
from app.models_associations import User_Battle_model


class LobbyManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        self.pending_disconnects: Dict[Tuple[int, int], asyncio.Task] = {}
        self.lock = asyncio.Lock()

    async def connect(self,
                      battle_id: int,
                      websocket: WebSocket,
                      db: AsyncSession,
                      user_id: int):
        if websocket.client_state == WebSocketState.DISCONNECTED:
            return
        await websocket.accept()
        disconnect_key = (battle_id, user_id)

        if disconnect_key in self.pending_disconnects:
            task = self.pending_disconnects.pop(disconnect_key)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error while waiting for disconnect task cancellation: {e}")

        async with self.lock:
            if battle_id not in self.active_connections:
                self.active_connections[battle_id] = {}
            if user_id in self.active_connections[battle_id]:
                old_ws = self.active_connections[battle_id][user_id]
                try:
                    if not old_ws.client_state == WebSocketState.DISCONNECTED:
                        await old_ws.close(code=1001)
                except Exception as e:
                    print(f"Error closing old connection: {e}")
            self.active_connections[battle_id][user_id] = websocket

        battle = await db.get(Battle_model, battle_id)
        if not battle:
            await websocket.close(code=4000)
            return

        await self.send_users_update(battle_id, db)

        result = await db.execute(select(User_Battle_model)
                                  .where(User_Battle_model.battle_id == battle_id))
        player_count = len(result.scalars().all())
        await self.broadcast(battle_id, {
            "type": "player_count",
            "count": player_count
        })


    async def schedule_disconnect(self,
                                  battle_id: int,
                                  user_id: int,
                                  db: AsyncSession):
        disconnect_key = (battle_id, user_id)

        if disconnect_key in self.pending_disconnects:
            task = self.pending_disconnects.pop(disconnect_key)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error while waiting for previous disconnect task cancellation: {e}")

        async def delayed_disconnect():
            await asyncio.sleep(10)
            async with self.lock:
                if (battle_id in self.active_connections and
                        user_id in self.active_connections[battle_id]):
                    print(f"User {user_id} reconnected, canceling disconnect")
                    return

            await self.disconnect_by_user(battle_id, user_id, db)

            async with self.lock:
                if disconnect_key in self.pending_disconnects and self.pending_disconnects[
                   disconnect_key] is asyncio.current_task():
                    del self.pending_disconnects[disconnect_key]

        task = asyncio.create_task(delayed_disconnect())
        async with self.lock:
            self.pending_disconnects[disconnect_key] = task

    async def disconnect_by_user(self,
                                 battle_id: int,
                                 user_id: int,
                                 db: AsyncSession):

        battle = await db.get(Battle_model, battle_id)
        if not battle:
            return

        user_battle = await db.scalar(
            select(User_Battle_model)
            .where(User_Battle_model.battle_id == battle_id,
                   User_Battle_model.user_id == user_id)
        )

        if not user_battle:
            return

        if user_id == battle.host and not battle.is_started:

            connections_to_close = []
            async with self.lock:
                if battle_id in self.active_connections:
                    connections_to_close = list(self.active_connections[battle_id].values())
                    del self.active_connections[battle_id]
                    keys_to_remove = [k for k in self.pending_disconnects.keys() if k[0] == battle_id]
                    for key in keys_to_remove:
                        task = self.pending_disconnects.pop(key)
                        if not task.done():
                            task.cancel()

            users_in_battle_result = await db.scalars(
                select(User_model)
                .join(User_Battle_model, User_model.id == User_Battle_model.user_id)
                .where(User_Battle_model.battle_id == battle_id)
            )
            users_in_battle = users_in_battle_result.all()

            for user in users_in_battle:
                user.balance += battle.price

            await db.execute(
                delete(User_Battle_model)
                .where(User_Battle_model.battle_id == battle_id)
            )
            await db.delete(battle)
            await db.commit()

            for ws in connections_to_close:
                try:
                    await ws.send_json({
                        "type": "lobby_deleted",
                        "reason": "Хост покинул лобби"
                    })
                    if ws.client_state != WebSocketState.DISCONNECTED:
                        await ws.close(code=4000)
                except (WebSocketDisconnect, RuntimeError) as e:
                    print(f"Error closing websocket or sending message: {e}")
                except Exception as e:
                    print(f"Unexpected error closing websocket: {e}")

        elif not battle.is_started:
            user = await db.scalar(select(User_model).where(User_model.id == user_id))
            if user:
                user.balance += battle.price

            await db.execute(
                delete(User_Battle_model)
                .where(User_Battle_model.battle_id == battle_id,
                       User_Battle_model.user_id == user_id)
            )
            await db.commit()

            async with self.lock:
                if (battle_id in self.active_connections and
                        user_id in self.active_connections[battle_id]):
                    del self.active_connections[battle_id][user_id]
                    if not self.active_connections[battle_id]:
                        del self.active_connections[battle_id]

            await self.send_users_update(battle_id, db)

            result = await db.execute(select(User_Battle_model)
                                      .where(User_Battle_model.battle_id == battle_id))
            player_count = len(result.scalars().all())
            await self.broadcast(battle_id, {
                "type": "player_count",
                "count": player_count
            })


    async def broadcast(self, battle_id: int, message: dict):
        async with self.lock:
            if battle_id in self.active_connections:
                connections = list(self.active_connections[battle_id].values())

        tasks = []
        for ws in connections:
            if ws.client_state != WebSocketState.DISCONNECTED:
                tasks.append(self._send_to_websocket(ws, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_websocket(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError) as e:
            print(f"Error sending message to websocket: {e}")
            async with self.lock:
                for battle_id, users in list(self.active_connections.items()):
                    for user_id, ws in list(users.items()):
                        if ws is websocket:
                            del self.active_connections[battle_id][user_id]
                            if not self.active_connections[battle_id]:
                                del self.active_connections[battle_id]
                            break
                    if websocket not in [ws for u_dict in self.active_connections.values() for ws in u_dict.values()]:
                        break
        except Exception as e:
            print(f"Unexpected error sending message to websocket: {e}")

    async def send_users_update(self,
                                battle_id: int,
                                db: AsyncSession):
        battle = await db.scalar(
            select(Battle_model)
            .where(Battle_model.id == battle_id)
            .options(selectinload(Battle_model.users).selectinload(User_Battle_model.user))
        )

        if not battle:
            return

        users_data = []
        for user_battle in battle.users:
            user = user_battle.user
            users_data.append({
                "id": user.id,
                "username": user.username,
                "avatar": user.avatar,
                "balance": float(user.balance)
            })

        await self.broadcast(battle_id, {
            "type": "update_users",
            "users": users_data
        })

    async def send_case_result(self, battle_id: int, user_id: int, skin_ids: List[int], round: int):
        await self.broadcast(battle_id, {
            "type": "case_result",
            "user_id": user_id,
            "skin_ids": skin_ids,
            "round": round
        })

    async def send_battle_end(self, battle_id: int, winner_id: int):
        await self.broadcast(battle_id, {
            "type": "battle_end",
            "winner_id": winner_id
        })

    def get_connection(self, battle_id: int, user_id: int) -> Optional[WebSocket]:
        if battle_id in self.active_connections:
            return self.active_connections[battle_id].get(user_id)
        return None

    async def cleanup_battle(self, battle_id: int):
        async with self.lock:
            if battle_id in self.active_connections:
                del self.active_connections[battle_id]
            keys_to_remove = [k for k in self.pending_disconnects.keys() if k[0] == battle_id]
            for key in keys_to_remove:
                task = self.pending_disconnects.pop(key)
                if not task.done():
                    task.cancel()


manager = LobbyManager()
