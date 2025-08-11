from typing import Annotated
import uvicorn
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin.router import adminRouter
from app.auth.models import UserModel
from app.auth.security import get_current_user_or_none

from app.auth.router import authRouter
from app.battles.router import battleRouter
from app.case.models import CaseModel
from app.case.router import caseRouter
from app.chat.router import chatRouter
from app.contracts.router import contractRouter
from app.models_associations import UserSkinModel
from app.notification.router import notificationRouter
from app.skin.router import skinRouter
from app.tops.router import topRouter
from app.upgrades.router import upgradeRouter
from app.utils.db_queries import get_unread_messages, get_user_new_notifications, get_user_notifications
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
                        user: UserModel | None = Depends(get_current_user_or_none),
                        ):

    last_skins = await db.scalars(
        select(UserSkinModel)
        .options(selectinload(UserSkinModel.skin))
        .order_by(desc('id'))
        .limit(15)
    )

    cases = await db.scalars(select(CaseModel).where(
        CaseModel.is_active,
        CaseModel.is_approved
    ).order_by(desc('id')))

    if user:
        notifications = await get_user_notifications(db, user.id)
        new_notifications = await get_user_new_notifications(db, user.id)
        new_messages = await get_unread_messages(db, user.id)

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
