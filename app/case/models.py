from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_associations import case_skin_association
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

    skins = relationship("Skin_model",
                         secondary=case_skin_association,
                         back_populates="cases")
