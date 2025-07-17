from typing import Annotated

import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none

from app.auth.router import authRouter
from app.case.models import Case_model
from app.case.router import caseRouter
from app.models_associations import User_Skin_model
from app.skin.models import Skin_model
from app.skin.router import skinRouter, add_all_skins_to_db
from app.tops.router import topRouter
from app.upgrades.router import upgradeRouter
from db.db import async_session
from db.db_depends import get_db

app = FastAPI(docs_url=None,
              redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
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


@app.on_event("startup")
async def startup_event():
    async with async_session() as db:
        result = await db.execute(select(Skin_model))
        skins = result.scalars().first()
        if not skins:
            await add_all_skins_to_db(db)


@app.get('/')
async def get_main_page(request: Request,
                        db: Annotated[AsyncSession, Depends(get_db)],
                        user: User_model | None = Depends(get_current_user_or_none),
                        ):
    last_skins = await db.scalars(
        select(User_Skin_model)
        .where(User_Skin_model.is_active == True)
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc('id'))
        .limit(15)
    )

    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active == True
    ).order_by(desc('id')))

    if user:
        return templates.TemplateResponse('main.html', {'request': request,
                                                        'user': user,
                                                        'username': user.username,
                                                        'balance': user.balance,
                                                        'last_skins': last_skins,
                                                        'cases': cases})

    return templates.TemplateResponse('main.html', {'request': request,
                                                    'last_skins': last_skins,
                                                    'cases': cases})


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
