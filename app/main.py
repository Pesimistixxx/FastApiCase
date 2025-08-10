from typing import Annotated

import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.admin.router import adminRouter
from app.auth.models import User_model
from app.auth.security import get_current_user_or_none

from app.auth.router import authRouter
from app.battles.router import battleRouter
from app.case.models import Case_model
from app.case.router import caseRouter
from app.chat.models import Message_model
from app.chat.router import chatRouter
from app.contracts.router import contractRouter
from app.models_associations import User_Skin_model
from app.notification.models import Notification_model
from app.notification.router import notificationRouter
from app.skin.router import skinRouter
from app.tops.router import topRouter
from app.upgrades.router import upgradeRouter
from db.db_depends import get_db

app = FastAPI(docs_url=None,
              redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["azber.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')


app.include_router(authRouter)
app.include_router(caseRouter)
app.include_router(skinRouter)
app.include_router(upgradeRouter)
app.include_router(topRouter)
app.include_router(contractRouter)
app.include_router(adminRouter)
app.include_router(battleRouter)
app.include_router(notificationRouter)
app.include_router(chatRouter)


@app.get('/')
async def get_main_page(request: Request,
                        db: Annotated[AsyncSession, Depends(get_db)],
                        user: User_model | None = Depends(get_current_user_or_none),
                        ):

    last_skins = await db.scalars(
        select(User_Skin_model)
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc('id'))
        .limit(15)
    )

    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active,
        Case_model.is_approved
    ).order_by(desc('id')))

    if user:
        notifications = await db.scalars(select(Notification_model)
                                         .where(Notification_model.notification_receiver_id == user.id,
                                                Notification_model.is_active)
                                         .order_by(desc(Notification_model.created))
                                         .options(selectinload(Notification_model.notification_sender)))

        new_notifications = await db.scalars(select(Notification_model)
                                             .where(Notification_model.notification_receiver_id == user.id,
                                                    Notification_model.is_active,
                                                    ~Notification_model.is_checked)
                                             .order_by(Notification_model.created))
        new_messages = await db.scalars(
            select(
                Message_model.chat_id,
                func.count(Message_model.id).label('unread_count')
            )
            .where(
                Message_model.author_id != user.id,
                ~Message_model.is_checked
            )
            .group_by(Message_model.chat_id)
        )
        return templates.TemplateResponse('main.html', {'request': request,
                                                        'user': user,
                                                        'last_skins': last_skins,
                                                        'cases': cases,
                                                        'notifications_cnt': len(new_notifications.all()),
                                                        'new_messages_cnt': len(new_messages.all()),
                                                        'notifications': notifications.all(),
                                                        })

    return templates.TemplateResponse('main.html', {'request': request,
                                                    'last_skins': last_skins,
                                                    'cases': cases,
                                                    'user': None})


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
