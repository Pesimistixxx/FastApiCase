from datetime import datetime
from typing import List

from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey, DateTime

from db.db import Base


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
    successful_cases_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_contracts_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    successful_upgrades_cnt: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)
    cases_create: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)

    sessions: Mapped[List["Session_model"]] = relationship(back_populates="user")
    skins: Mapped[List["User_Skin_model"]] = relationship("User_Skin_model", back_populates="user")


class Session_model(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User_model"] = relationship(back_populates="sessions")