from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint

from db.base import Base

if TYPE_CHECKING:
    from app.models_associations import User_Skin_model, User_Battle_model, User_Chat_model, User_Achievement_model
    from app.case.models import Case_model
    from app.chat.models import Message_model
    from app.notification.models import Notification_model


class User_model(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(default=0.0, server_default='0.0')
    password: Mapped[str] = mapped_column(nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default='True')
    is_creator: Mapped[bool] = mapped_column(default=False, server_default='True')
    avatar: Mapped[str] = mapped_column(default='default.png', server_default='default.png')
    case_opened: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    upgrades_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    contracts_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    battles_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_cases_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_contracts_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_upgrades_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    cases_create: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    author_case_opened: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    activity_points: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)

    sessions: Mapped[List["Session_model"]] = relationship(back_populates="user")
    case: Mapped[List["Case_model"]] = relationship("Case_model", back_populates="author")
    skins: Mapped[List["User_Skin_model"]] = relationship("User_Skin_model", back_populates="user")
    battles: Mapped[List["User_Battle_model"]] = relationship("User_Battle_model", back_populates="user")
    chats: Mapped[List["User_Chat_model"]] = relationship("User_Chat_model", back_populates="user")
    messages: Mapped[List["Message_model"]] = relationship("Message_model", back_populates="user")
    achievements: Mapped["User_Achievement_model"] = relationship("User_Achievement_model", back_populates="user")

    friends_as_first: Mapped[List["Friends_model"]] = relationship(
        back_populates="first_user",
        foreign_keys="Friends_model.first_user_id"
    )

    friends_as_second: Mapped[List["Friends_model"]] = relationship(
        back_populates="second_user",
        foreign_keys="Friends_model.second_user_id"
    )

    requester: Mapped[List["Friends_model"]] = relationship(
        back_populates="requester",
        foreign_keys="Friends_model.requester_id"
    )
    notification_receiver: Mapped["Notification_model"] = relationship(
        back_populates="notification_receiver",
        foreign_keys="Notification_model.notification_receiver_id")

    notification_sender: Mapped["Notification_model"] = relationship(
        back_populates="notification_sender",
        foreign_keys="Notification_model.notification_sender_id")


class Session_model(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User_model"] = relationship(back_populates="sessions")


class Friends_model(Base):
    __tablename__ = 'friends'

    id: Mapped[int] = mapped_column(primary_key=True)
    first_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    second_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    is_accepted: Mapped[bool] = mapped_column(nullable=False, default=False, server_default='False')
    requester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    first_user: Mapped["User_model"] = relationship(foreign_keys=[first_user_id], back_populates="friends_as_first")
    second_user: Mapped["User_model"] = relationship(foreign_keys=[second_user_id], back_populates="friends_as_second")
    requester: Mapped["User_model"] = relationship(foreign_keys=[requester_id], back_populates="requester")

    __table_args__ = (
        UniqueConstraint('first_user_id', 'second_user_id', name='uix_friendship'),
    )
