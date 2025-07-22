from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from db.db_depends import get_db
from app.auth.security import get_current_user_or_none

topRouter = APIRouter(prefix='/top', tags=['users', 'top'])
templates = Jinja2Templates(directory='templates')


@topRouter.get('/')
async def get_top(db: Annotated[AsyncSession, Depends(get_db)],
                  request: Request,
                  user: User_model | None = Depends(get_current_user_or_none)):
    top_cases_open = await db.scalars(select(User_model).order_by(desc(User_model.case_opened)).limit(10))
    top_upgrades_cnt = await db.scalars(select(User_model).order_by(desc(User_model.upgrades_cnt)).limit(10))
    top_contracts_cnt = await db.scalars(select(User_model).order_by(desc(User_model.contracts_cnt)).limit(10))
    top_case_created = await db.scalars(select(User_model).order_by(desc(User_model.cases_create)).limit(10))
    top_case_luck = await db.scalars(select(User_model)
                                     .where(User_model.case_opened >= 100)
                                     .order_by(
        desc(User_model.successful_cases_cnt / (User_model.case_opened + 1)))
                                     .limit(10))
    top_upgrades_luck = await db.scalars(select(User_model)
                                         .where(User_model.upgrades_cnt >= 50)
                                         .order_by(
        desc(User_model.successful_upgrades_cnt / (User_model.upgrades_cnt + 1)))
                                         .limit(10))
    top_contracts_luck = await db.scalars(select(User_model).where(User_model.contracts_cnt >= 50).order_by(
        desc(User_model.successful_contracts_cnt / (User_model.contracts_cnt + 1))).limit(10))
    activity_points = await db.scalars(select(User_model).order_by(desc(User_model.activity_points)).limit(10))

    top_cases_open_dict = {user.username: user.case_opened for user in top_cases_open.all()}
    top_upgrades_cnt_dict = {user.username: user.upgrades_cnt for user in top_upgrades_cnt.all()}
    top_contracts_cnt_dict = {user.username: user.contracts_cnt for user in top_contracts_cnt.all()}
    top_case_created_dict = {user.username: user.cases_create for user in top_case_created.all()}
    top_case_luck_dict = {user.username: f'{user.successful_cases_cnt / (user.case_opened + 1) * 100:.2f}' for user in
                          top_case_luck}
    top_upgrades_luck_dict = {user.username: f'{user.successful_upgrades_cnt / (user.upgrades_cnt + 1) * 100:.2f}' for
                              user in top_upgrades_luck}
    top_contracts_luck_dict = {user.username: f'{user.successful_contracts_cnt / (user.contracts_cnt + 1) * 100:.2f}'
                               for user in top_contracts_luck}
    activity_points_dict = {user.username: user.activity_points for user in activity_points.all()}
    if user:
        return templates.TemplateResponse('tops.html', {'request': request,
                                                        'user': user,
                                                        'balance': user.balance,
                                                        'username': user.username,
                                                        'top_cases_open': top_cases_open_dict,
                                                        'top_case_created': top_case_created_dict,
                                                        'top_upgrades_cnt': top_upgrades_cnt_dict,
                                                        'top_contracts_cnt': top_contracts_cnt_dict,
                                                        'top_case_luck': top_case_luck_dict,
                                                        'top_upgrades_luck': top_upgrades_luck_dict,
                                                        'top_contracts_luck': top_contracts_luck_dict,
                                                        'top_activity': activity_points_dict})

    return templates.TemplateResponse('tops.html', {'request': request,
                                                    'top_cases_open': top_cases_open_dict,
                                                    'top_case_created': top_case_created_dict,
                                                    'top_upgrades_cnt': top_upgrades_cnt_dict,
                                                    'top_contracts_cnt': top_contracts_cnt_dict,
                                                    'top_case_luck': top_case_luck_dict,
                                                    'top_upgrades_luck': top_upgrades_luck_dict,
                                                    'top_contracts_luck': top_contracts_luck_dict,
                                                    'top_activity': activity_points_dict})
