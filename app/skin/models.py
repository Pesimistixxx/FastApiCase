from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class SkinModel(Base):
    __tablename__ = 'skins'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    quality: Mapped[str]
    tag: Mapped[str]
    price: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    image: Mapped[str]
    is_trackable: Mapped[bool] = mapped_column(nullable=False, default=True, server_default='True')

    case_associations: Mapped[List["CaseSkinModel"]] = relationship(back_populates="skin")

    cases: Mapped[List["CaseModel"]] = relationship(
        "CaseModel",
        secondary="cases_skins",
        viewonly=True,
        overlaps="case_associations"
    )

    users: Mapped[List["UserSkinModel"]] = relationship("UserSkinModel", back_populates="skin")
