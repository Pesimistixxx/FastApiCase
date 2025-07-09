from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_associations import Case_Skin_model
from db.db import Base


class Case_model(Base):
    __tablename__ = 'cases'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    price: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    math_exception: Mapped[int] = mapped_column(nullable=False, server_default='1')
    sigma: Mapped[int] = mapped_column(nullable=False, server_default='1')
    image: Mapped[str] = mapped_column(default='default.png')

    skin_associations: Mapped[List["Case_Skin_model"]] = relationship("Case_Skin_model", back_populates="case")

    skins: Mapped[List["Skin_model"]] = relationship(
        "Skin_model",
        secondary="case_models",
        viewonly=True,
        overlaps="skin_associations")