from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.chat.models import MessageModel
from app.models_associations import UserChatModel
from app.notification.models import NotificationModel


async def get_user_notifications(db, user_id):
    return await db.scalars(
        select(NotificationModel)
        .where(
            NotificationModel.notification_receiver_id == user_id,
            NotificationModel.is_active,
            ~NotificationModel.is_checked
        )
        .order_by(NotificationModel.created)
        .options(selectinload(NotificationModel.notification_sender))
    )


async def get_user_new_notifications(db, user_id):
    return await db.scalars(select(NotificationModel)
                            .where(NotificationModel.notification_receiver_id == user_id,
                                   NotificationModel.is_active,
                                   ~NotificationModel.is_checked)
                            .order_by(NotificationModel.created))


async def get_unread_messages(db, user_id):
    return await db.scalars(
        select(
            MessageModel.chat_id,
            func.count(MessageModel.id).label('unread_count')  # pylint: disable=not-callable
        )
        .join(
            UserChatModel,
            UserChatModel.chat_id == MessageModel.chat_id
        )
        .where(
            MessageModel.author_id != user_id,
            ~MessageModel.is_checked,
            UserChatModel.user_id == user_id
        )
        .group_by(MessageModel.chat_id)
    )
