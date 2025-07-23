from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_associations import Case_Skin_model
from db.db import Base

if TYPE_CHECKING:
    from app.skin.models import Skin_model
    from app.auth.models import User_model


class Case_model(Base):
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

    skin_associations: Mapped[List["Case_Skin_model"]] = relationship("Case_Skin_model", back_populates="case")
    author: Mapped[List["User_model"]] = relationship("User_model", back_populates="case")
    skins: Mapped[List["Skin_model"]] = relationship(
        "Skin_model",
        secondary="case_models",
        viewonly=True,
        overlaps="skin_associations")
