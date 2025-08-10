from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from app.models_associations import UserBattleModel
    from app.case.models import CaseModel


class BattleModel(Base):
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
    created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # pylint: disable=not-callable

    users: Mapped[List["UserBattleModel"]] = relationship("UserBattleModel",
                                                          back_populates="battle", cascade="all, delete")
    case: Mapped["CaseModel"] = relationship("CaseModel", back_populates="battle")
