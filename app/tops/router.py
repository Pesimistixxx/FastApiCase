from typing import Annotated
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.auth.models import UserModel
from app.case.models import CaseModel
from app.auth.security import get_current_user_or_none
from app.utils.db_queries import get_user_notifications, get_unread_messages, get_user_new_notifications
from db.db_depends import get_db

topRouter = APIRouter(prefix='/top', tags=['users', 'top'])
templates = Jinja2Templates(directory='templates')


@topRouter.get('/')
async def get_top(db: Annotated[AsyncSession, Depends(get_db)],
                  request: Request,
                  user: UserModel | None = Depends(get_current_user_or_none)):
    top_cases_open = await db.scalars(select(UserModel).order_by(desc(UserModel.case_opened)).limit(10))
    top_upgrades_cnt = await db.scalars(select(UserModel).order_by(desc(UserModel.upgrades_cnt)).limit(10))
    top_contracts_cnt = await db.scalars(select(UserModel).order_by(desc(UserModel.contracts_cnt)).limit(10))
    top_case_created = await db.scalars(select(UserModel).order_by(desc(UserModel.cases_create)).limit(10))
    top_case_luck = await db.scalars(select(UserModel)
                                     .where(UserModel.case_opened >= 100)
                                     .order_by(
        desc(UserModel.successful_cases_cnt / (UserModel.case_opened + 1)))
        .limit(10))
    top_upgrades_luck = await db.scalars(select(UserModel)
                                         .where(UserModel.upgrades_cnt >= 50)
                                         .order_by(
        desc(UserModel.successful_upgrades_cnt / (UserModel.upgrades_cnt + 1)))
        .limit(10))
    top_contracts_luck = await db.scalars(select(UserModel).where(UserModel.contracts_cnt >= 50).order_by(
        desc(UserModel.successful_contracts_cnt / (UserModel.contracts_cnt + 1))).limit(10))
    top_activity = await db.scalars(select(UserModel).order_by(desc(UserModel.activity_points)).limit(10))
    top_authors = await db.scalars(select(UserModel)
                                   .order_by(desc(UserModel.author_case_opened))
                                   .limit(10))
    top_cases = await db.scalars(select(CaseModel)
                                 .order_by(desc(CaseModel.opened_count))
                                 .limit(10))
    top_battles = await db.scalars(select(UserModel).order_by(desc(UserModel.battles_cnt)).limit(10))
    top_battles_luck = await db.scalars(select(UserModel).where(UserModel.battles_cnt >= 50).order_by(
        desc(UserModel.battles_won / (UserModel.battles_cnt + 1))).limit(10))
    top_battles_streak = await db.scalars(select(UserModel).order_by(desc(UserModel.battles_streak)).limit(10))
    top_achievements = await db.scalars(select(UserModel).order_by(desc(UserModel.achievements_cnt)).limit(10))

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
    top_battles_luck_dict = {user.username: f'{user.battles_won / (user.battles_cnt + 1) * 100:.2f}'
                             for user in top_battles_luck}
    top_activity_dict = {user.username: user.activity_points for user in top_activity.all()}
    top_authors_dict = {user.username: user.author_case_opened for user in top_authors.all()}
    top_cases_dict = {case.name: case.opened_count for case in top_cases.all()}
    top_battles_dict = {user.username: user.battles_cnt for user in top_battles.all()}
    top_battles_streak_dict = {user.username: user.battles_streak for user in top_battles_streak.all()}
    top_achievements_dict = {user.username: user.achievements_cnt for user in top_achievements.all()}

    if user:
        notifications = await get_user_notifications(db, user.id)
        new_notifications = await get_user_new_notifications(db, user.id)
        new_messages = await get_unread_messages(db, user.id)

        return templates.TemplateResponse('top.html', {'request': request,
                                                       'user': user,
                                                       'top_cases_open': top_cases_open_dict,
                                                       'top_case_created': top_case_created_dict,
                                                       'top_upgrades_cnt': top_upgrades_cnt_dict,
                                                       'top_contracts_cnt': top_contracts_cnt_dict,
                                                       'top_case_luck': top_case_luck_dict,
                                                       'top_upgrades_luck': top_upgrades_luck_dict,
                                                       'top_contracts_luck': top_contracts_luck_dict,
                                                       'top_activity': top_activity_dict,
                                                       'top_authors': top_authors_dict,
                                                       'top_cases': top_cases_dict,
                                                       'top_battles_cnt': top_battles_dict,
                                                       'top_battles_luck': top_battles_luck_dict,
                                                       'top_battles_streak': top_battles_streak_dict,
                                                       'top_achievements_cnt': top_achievements_dict,
                                                       'notifications_cnt': len(new_notifications.all()),
                                                       'new_messages_cnt': len(new_messages.all()),
                                                       'notifications': notifications.all(),
                                                       })

    return templates.TemplateResponse('top.html', {'request': request,
                                                   'top_cases_open': top_cases_open_dict,
                                                   'top_case_created': top_case_created_dict,
                                                   'top_upgrades_cnt': top_upgrades_cnt_dict,
                                                   'top_contracts_cnt': top_contracts_cnt_dict,
                                                   'top_case_luck': top_case_luck_dict,
                                                   'top_upgrades_luck': top_upgrades_luck_dict,
                                                   'top_contracts_luck': top_contracts_luck_dict,
                                                   'top_activity': top_activity_dict,
                                                   'top_authors': top_authors_dict,
                                                   'top_cases': top_cases_dict,
                                                   'top_battles_cnt': top_battles_dict,
                                                   'top_battles_luck': top_battles_luck_dict,
                                                   'top_battles_streak': top_battles_streak_dict,
                                                   'top_achievements_cnt': top_achievements_dict,
                                                   'user': None})
