import asyncio
import datetime
from typing import Dict, Tuple
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession


class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        self.pending_disconnects: Dict[Tuple[int, int], asyncio.Task] = {}
        self.lock = asyncio.Lock()
        self.max_reconnect_attempts = 10

    async def connect(self,
                      chat_id: int,
                      websocket: WebSocket,
                      db: AsyncSession,
                      user_id: int):
        if websocket.client_state == WebSocketState.DISCONNECTED:
            return

        await websocket.accept()
        disconnect_key = (chat_id, user_id)

        if disconnect_key in self.pending_disconnects:
            task = self.pending_disconnects.pop(disconnect_key)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        async with self.lock:
            if chat_id not in self.active_connections:
                self.active_connections[chat_id] = {}

            if user_id in self.active_connections[chat_id]:
                old_ws = self.active_connections[chat_id][user_id]
                try:
                    if old_ws.client_state != WebSocketState.DISCONNECTED:
                        await old_ws.close(code=1001)
                except Exception:
                    pass

            self.active_connections[chat_id][user_id] = websocket

    async def schedule_disconnect(self,
                                  chat_id: int,
                                  user_id: int,
                                  db: AsyncSession):
        disconnect_key = (chat_id, user_id)

        if disconnect_key in self.pending_disconnects:
            task = self.pending_disconnects.pop(disconnect_key)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        async def delayed_disconnect():
            await asyncio.sleep(10)
            async with self.lock:
                if (chat_id in self.active_connections
                        and user_id in self.active_connections[chat_id]):
                    print(f"User {user_id} reconnected, canceling disconnect")
                    return

            await self.disconnect_by_user(chat_id, user_id, db)

            async with self.lock:
                if disconnect_key in self.pending_disconnects:
                    del self.pending_disconnects[disconnect_key]

        task = asyncio.create_task(delayed_disconnect())
        self.pending_disconnects[disconnect_key] = task

    async def disconnect_by_user(self,
                                 chat_id: int,
                                 user_id: int,
                                 db: AsyncSession):
        async with self.lock:
            if (chat_id in self.active_connections
                    and user_id in self.active_connections[chat_id]):
                del self.active_connections[chat_id][user_id]

                if not self.active_connections[chat_id]:
                    del self.active_connections[chat_id]

    async def broadcast(self,
                        chat_id: int,
                        message: dict,
                        exclude_user_id: int = None):
        async with self.lock:
            if chat_id not in self.active_connections:
                return

            connections = list(self.active_connections[chat_id].items())

        tasks = []
        for user_id, ws in connections:
            if exclude_user_id is not None and user_id == exclude_user_id:
                continue

            if ws.client_state != WebSocketState.DISCONNECTED:
                try:
                    tasks.append(ws.send_json(message))
                except Exception as e:
                    print(f"Error sending message to user {user_id}: {e}")
                    ws._should_remove = True

        async with self.lock:
            for user_id, ws in list(self.active_connections[chat_id].items()):
                if hasattr(ws, '_should_remove'):
                    del self.active_connections[chat_id][user_id]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_typing_status(self, chat_id: int, user_id: int, is_typing: bool):
        await self.broadcast(
            chat_id=chat_id,
            message={
                "type": "typing_status",
                "user_id": user_id,
                "is_typing": is_typing
            },
            exclude_user_id=user_id
        )

    async def cleanup_chat(self, chat_id: int):
        async with self.lock:
            if chat_id in self.active_connections:
                del self.active_connections[chat_id]

            keys_to_remove = [k for k in self.pending_disconnects.keys() if k[0] == chat_id]
            for key in keys_to_remove:
                task = self.pending_disconnects.pop(key)
                if not task.done():
                    task.cancel()

    async def send_user_activity(self, chat_id: int, user_id: int):
        async with self.lock:
            if chat_id not in self.active_connections:
                return

            message = {
                "type": "user_activity",
                "user_id": user_id,
                "timestamp": datetime.datetime.now().isoformat()
            }

            tasks = []
            for uid, ws in self.active_connections[chat_id].items():
                if uid != user_id and ws.client_state != WebSocketState.DISCONNECTED:
                    try:
                        tasks.append(ws.send_json(message))
                    except Exception:
                        pass

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)


chat_manager = ChatConnectionManager()
