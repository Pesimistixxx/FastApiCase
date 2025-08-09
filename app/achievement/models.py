from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Achievement_model(Base):
    __tablename__ = 'achievements'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    image: Mapped[str] = mapped_column(default='default.png')
    description: Mapped[str] = mapped_column(nullable=True)

    users: Mapped[List["User_Achievement_model"]] = relationship("User_Achievement_model",
                                                                 back_populates="achievements")
