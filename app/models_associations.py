from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.achievement.models import AchievementModel
from app.chat.models import ChatModel

from db.base import Base


class CaseSkinModel(Base):
    __tablename__ = 'cases_skins'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey('cases.id'))
    skin_id: Mapped[int] = mapped_column(Integer, ForeignKey('skins.id'))

    case: Mapped["app.case.models.CaseModel"] = relationship("CaseModel", back_populates="skin_associations")
    skin: Mapped["app.skin.models.SkinModel"] = relationship("SkinModel", back_populates="case_associations")


class UserSkinModel(Base):
    __tablename__ = 'users_skins'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    skin_id: Mapped[int] = mapped_column(ForeignKey('skins.id'))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="skins")
    skin: Mapped["SkinModel"] = relationship("SkinModel", back_populates="users")


class UserBattleModel(Base):
    __tablename__ = 'users_battles'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    battle_id: Mapped[int] = mapped_column(ForeignKey('battles.id', ondelete="CASCADE"))

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="battles")
    battle: Mapped["BattleModel"] = relationship("BattleModel", back_populates="users")


class UserChatModel(Base):
    __tablename__ = 'users_chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'))
    unread_messages: Mapped[int] = mapped_column(nullable=False, default=0, server_default='0')

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="chats")
    chat: Mapped["ChatModel"] = relationship(ChatModel, back_populates="users_associations")


class UserAchievementModel(Base):
    __tablename__ = 'users_achievements'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    achievement_id: Mapped[int] = mapped_column(ForeignKey('achievements.id'))
    achievement_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="achievements")
    achievements: Mapped["AchievementModel"] = relationship(AchievementModel, back_populates="users")
