import asyncio
import datetime
import os
import pytz
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

from db.db_depends import get_db

load_dotenv()

Base = declarative_base()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Session_model(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)


async def clean_expired_sessions(db: AsyncSession):
    try:
        await db.execute(delete(Session_model).where(
            Session_model.expires <= datetime.datetime.now()
        ))

        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при очистки сессий: {e}")
        await db.rollback()


async def start_scheduler():
    tz = pytz.timezone(os.getenv("TIMEZONE", "UTC"))
    scheduler = AsyncIOScheduler(timezone=tz)

    async def job():
        logger.info("Начало очистки бд от старых сессий")
        async for db in get_db():
            await clean_expired_sessions(db=db)
        logger.info("Конец очистки бд от старых сессий")

    #scheduler.add_job(job, 'interval', minutes=5, next_run_time=datetime.datetime.now())
    scheduler.add_job(job, 'interval', minutes=5)

    scheduler.start()


async def db_cleaner_scheduler():
    logger.info("Запуск основного цикла(очистка)")
    await start_scheduler()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Шедулер остановлен(очистка)")


if __name__ == "__main__":
    asyncio.run(db_cleaner_scheduler())
