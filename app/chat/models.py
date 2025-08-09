from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from app.models_associations import User_Chat_model
    from app.auth.models import User_model


class Chat_model(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())

    users_associations: Mapped[List["User_Chat_model"]] = relationship("User_Chat_model", back_populates="chat")
    messages: Mapped[List["Message_model"]] = relationship("Message_model", back_populates="chat")


class Message_model(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'))
    message: Mapped[str] = mapped_column(nullable=False)
    message_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_checked: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_edited: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped["User_model"] = relationship("User_model", back_populates="messages")
    chat: Mapped["Chat_model"] = relationship("Chat_model", back_populates="messages")
