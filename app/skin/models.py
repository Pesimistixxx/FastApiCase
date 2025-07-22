from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_associations import Case_Skin_model
from db.db import Base

if TYPE_CHECKING:
    from app.case.models import Case_model
    from app.models_associations import User_Skin_model


class Skin_model(Base):
    __tablename__ = 'skins'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    quality: Mapped[str]
    tag: Mapped[str]
    price: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    image: Mapped[str]

    case_associations: Mapped[List["Case_Skin_model"]] = relationship("Case_Skin_model", back_populates="skin")

    cases: Mapped[List["Case_model"]] = relationship(
        "Case_model",
        secondary="case_models",
        viewonly=True,
        overlaps="case_associations"
    )

    users: Mapped[List["User_Skin_model"]] = relationship("User_Skin_model", back_populates="skin")
