from typing import Annotated

import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.staticfiles import StaticFiles

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none

from app.auth.router import authRouter
from app.case.models import Case_model
from app.case.router import caseRouter
from app.models_associations import User_Skin_model
from app.skin.router import skinRouter
from db.db_depends import get_db

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')


app.include_router(authRouter)
app.include_router(caseRouter)
app.include_router(skinRouter)


@app.get('/')
async def get_main_page(request: Request,
                        db:Annotated[AsyncSession, Depends(get_db)],
                        user: User_model | None = Depends(get_current_user_or_none),
                        ):
    last_skins = await db.scalars(
        select(User_Skin_model)
        .where(User_Skin_model.is_active == True)
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc('id'))
        .limit(5)
    )

    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active == True
    ))

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
