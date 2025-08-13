from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from app.models_associations import UserChatModel
    from app.auth.models import UserModel


class ChatModel(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())

    users_associations: Mapped[List["UserChatModel"]] = relationship("UserChatModel", back_populates="chat")
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="chat")


class MessageModel(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'))
    message: Mapped[str] = mapped_column(nullable=False)
    message_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_checked: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_edited: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="messages")
    chat: Mapped["ChatModel"] = relationship("ChatModel", back_populates="messages")
