from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint

from db.base import Base

if TYPE_CHECKING:
    from app.models_associations import UserSkinModel, UserBattleModel, UserChatModel, UserAchievementModel
    from app.case.models import CaseModel
    from app.chat.models import MessageModel
    from app.notification.models import NotificationModel


class UserModel(Base):
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
    battles_won: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    battles_streak: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_cases_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_contracts_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_upgrades_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    cases_create: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    author_case_opened: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    achievements_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    activity_points: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)

    sessions: Mapped[List["SessionModel"]] = relationship(back_populates="user")
    case: Mapped[List["CaseModel"]] = relationship("CaseModel", back_populates="author")
    skins: Mapped[List["UserSkinModel"]] = relationship("UserSkinModel", back_populates="user")
    battles: Mapped[List["UserBattleModel"]] = relationship("UserBattleModel", back_populates="user")
    chats: Mapped[List["UserChatModel"]] = relationship("UserChatModel", back_populates="user")
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="user")
    achievements: Mapped["UserAchievementModel"] = relationship("UserAchievementModel", back_populates="user")

    friends_as_first: Mapped[List["FriendsModel"]] = relationship(
        back_populates="first_user",
        foreign_keys="FriendsModel.first_user_id"
    )

    friends_as_second: Mapped[List["FriendsModel"]] = relationship(
        back_populates="second_user",
        foreign_keys="FriendsModel.second_user_id"
    )

    requester: Mapped[List["FriendsModel"]] = relationship(
        back_populates="requester",
        foreign_keys="FriendsModel.requester_id"
    )
    notification_receiver: Mapped["NotificationModel"] = relationship(
        back_populates="notification_receiver",
        foreign_keys="NotificationModel.notification_receiver_id")

    notification_sender: Mapped["NotificationModel"] = relationship(
        back_populates="notification_sender",
        foreign_keys="NotificationModel.notification_sender_id")


class SessionModel(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["UserModel"] = relationship(back_populates="sessions")


class FriendsModel(Base):
    __tablename__ = 'friends'

    id: Mapped[int] = mapped_column(primary_key=True)
    first_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    second_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    is_accepted: Mapped[bool] = mapped_column(nullable=False, default=False, server_default='False')
    requester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    first_user: Mapped["UserModel"] = relationship(foreign_keys=[first_user_id], back_populates="friends_as_first")
    second_user: Mapped["UserModel"] = relationship(foreign_keys=[second_user_id], back_populates="friends_as_second")
    requester: Mapped["UserModel"] = relationship(foreign_keys=[requester_id], back_populates="requester")

    __table_args__ = (
        UniqueConstraint('first_user_id', 'second_user_id', name='uix_friendship'),
    )
