from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base

if TYPE_CHECKING:
    from app.models_associations import User_Battle_model
    from app.case.models import Case_model


class Battle_model(Base):
    __tablename__ = 'battles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, default='battle')
    players_cnt: Mapped[int] = mapped_column(nullable=False, default=2)
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id'), nullable=False)
    case_cnt: Mapped[int] = mapped_column(nullable=False, default=1)
    price: Mapped[int] = mapped_column(nullable=False, server_default='0', default=0)
    is_active: Mapped[bool] = mapped_column(default=True, server_default='True')
    is_started: Mapped[bool] = mapped_column(default=False, server_default='False')
    host: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    users: Mapped[List["User_Battle_model"]] = relationship("User_Battle_model", back_populates="battle")
    case: Mapped["Case_model"] = relationship("Case_model", back_populates="battle")
