from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_associations import case_skin_association
from db.db import Base


class Skin_model(Base):
    __tablename__ = 'skins'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    quality: Mapped[str]
    tag: Mapped[str]
    price: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    image: Mapped[str]

    cases = relationship("Case_model",
                         secondary=case_skin_association,
                         back_populates="skins")

    users = relationship("User_Skin_model", back_populates="skin")
