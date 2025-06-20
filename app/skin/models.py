from sqlalchemy.orm import Mapped, mapped_column

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