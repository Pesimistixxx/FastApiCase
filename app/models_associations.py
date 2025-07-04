from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base


class Case_Skin_model(Base):
    __tablename__ = 'case_models'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey('cases.id'))
    skin_id: Mapped[int] = mapped_column(Integer, ForeignKey('skins.id'))

    case: Mapped["Case_model"] = relationship("Case_model", back_populates="skin_associations")
    skin: Mapped["Skin_model"] = relationship("Skin_model", back_populates="case_associations")


class User_Skin_model(Base):
    __tablename__ = 'users_skins'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    skin_id: Mapped[int] = mapped_column(ForeignKey('skins.id'))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["User_model"] = relationship("User_model", back_populates="skins")
    skin: Mapped["Skin_model"] = relationship("Skin_model", back_populates="users")
