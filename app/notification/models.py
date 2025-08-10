from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class NotificationModel(Base):
    __tablename__ = 'notifications'

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_checked: Mapped[bool] = mapped_column(nullable=False, default=False)
    notification_receiver_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    notification_sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime,
                                              server_default=func.now(),  # pylint: disable=not-callable
                                              default=func.now(),  # pylint: disable=not-callable
                                              nullable=False)

    notification_receiver: Mapped["UserModel"] = relationship(foreign_keys=[notification_receiver_id],
                                                              back_populates="notification_receiver")
    notification_sender: Mapped["UserModel"] = relationship(foreign_keys=[notification_sender_id],
                                                            back_populates="notification_sender")
