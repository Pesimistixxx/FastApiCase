from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base

case_skin_association = Table(
    'case_models', Base.metadata,
    Column('case_id', Integer, ForeignKey('cases.id')),
    Column('skin_id', Integer, ForeignKey('skins.id'))
)


class User_Skin_model(Base):
    __tablename__ = 'users_skins'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    skin_id: Mapped[int] = mapped_column(ForeignKey('skins.id'), primary_key=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user = relationship("User_model", back_populates="skins")
    skin = relationship("Skin_model", back_populates="users")