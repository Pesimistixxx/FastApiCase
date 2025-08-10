from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from app.skin.models import SkinModel
    from app.auth.models import UserModel
    from app.battles.models import BattleModel


class CaseModel(Base):
    __tablename__ = 'cases'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    price: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_approved: Mapped[bool] = mapped_column(default=False, server_default='False')
    math_exception: Mapped[int] = mapped_column(nullable=False, server_default='1')
    sigma: Mapped[int] = mapped_column(nullable=False, server_default='1')
    image: Mapped[str] = mapped_column(default='default.png')
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    opened_count: Mapped[int] = mapped_column(default=0, server_default='0', nullable=False)

    skin_associations: Mapped[List["app.models_associations.CaseSkinModel"]] = relationship(back_populates="case")
    author: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="case")
    battle: Mapped[["BattleModel"]] = relationship("BattleModel", back_populates="case")
    skins: Mapped[List["SkinModel"]] = relationship(
        "SkinModel",
        secondary="cases_skins",
        viewonly=True,
        overlaps="skin_associations")
