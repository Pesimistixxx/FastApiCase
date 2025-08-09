from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.achievement.models import Achievement_model
from app.chat.models import Chat_model

from db.base import Base


class Case_Skin_model(Base):
    __tablename__ = 'cases_skins'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey('cases.id'))
    skin_id: Mapped[int] = mapped_column(Integer, ForeignKey('skins.id'))

    case: Mapped["app.case.models.Case_model"] = relationship("Case_model", back_populates="skin_associations")
    skin: Mapped["app.skin.models.Skin_model"] = relationship("Skin_model", back_populates="case_associations")


class User_Skin_model(Base):
    __tablename__ = 'users_skins'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    skin_id: Mapped[int] = mapped_column(ForeignKey('skins.id'))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["User_model"] = relationship("User_model", back_populates="skins")
    skin: Mapped["Skin_model"] = relationship("Skin_model", back_populates="users")


class User_Battle_model(Base):
    __tablename__ = 'users_battles'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    battle_id: Mapped[int] = mapped_column(ForeignKey('battles.id', ondelete="CASCADE"))

    user: Mapped["User_model"] = relationship("User_model", back_populates="battles")
    battle: Mapped["Battle_model"] = relationship("Battle_model", back_populates="users")


class User_Chat_model(Base):
    __tablename__ = 'users_chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'))
    unread_messages: Mapped[int] = mapped_column(nullable=False, default=0, server_default='0')

    user: Mapped["User_model"] = relationship("User_model", back_populates="chats")
    chat: Mapped["Chat_model"] = relationship(Chat_model, back_populates="users_associations")


class User_Achievement_model(Base):
    __tablename__ = 'users_achievements'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    chat_id: Mapped[int] = mapped_column(ForeignKey('achievements.id'))
    achievement_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())

    user: Mapped["User_model"] = relationship("User_model", back_populates="achievements")
    achievements: Mapped["Achievement_model"] = relationship(Achievement_model, back_populates="users")
