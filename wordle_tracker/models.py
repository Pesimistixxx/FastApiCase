from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class WordleModel(Base):
    __tablename__ = 'wordle_words'

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(nullable=False)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
