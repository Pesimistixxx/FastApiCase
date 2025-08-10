from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from app.case.models import Case_model
from app.chat.models import Message_model
from app.notification.models import Notification_model
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
    top_activity = await db.scalars(select(User_model).order_by(desc(User_model.activity_points)).limit(10))
    top_authors = await db.scalars(select(User_model)
                                   .order_by(desc(User_model.author_case_opened))
                                   .limit(10))
    top_cases = await db.scalars(select(Case_model)
                                 .order_by(desc(Case_model.opened_count))
                                 .limit(10))

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
    top_activity_dict = {user.username: user.activity_points for user in top_activity.all()}
    top_authors_dict = {user.username: user.author_case_opened for user in top_authors.all()}
    top_cases_dict = {case.name: case.opened_count for case in top_cases.all()}

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
                                                   'user': None})
