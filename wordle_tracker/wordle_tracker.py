import asyncio
import datetime
import os
import logging
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from wordle_tracker.models import WordleModel
from db.db_depends import get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def fetch_wordle_answer(db: AsyncSession, client: httpx.AsyncClient):
    logger.info("Начало выполнения функции(получение слова)")
    try:
        date = datetime.date.today()
        url = f"https://www.nytimes.com/svc/wordle/v2/{date:%Y-%m-%d}.json"
        response = await client.get(url)
        print(f"Answer: {response.json()['solution']}")
        await db.execute(insert(WordleModel)
                         .values(word=response.json()['solution'],
                                 created=datetime.date.today()))
        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при получении слова: {e}")
        await db.rollback()
    logger.info("Конец выполнения функции(получение слова)")


async def start_scheduler():
    tz = pytz.timezone(os.getenv("TIMEZONE", "UTC"))
    scheduler = AsyncIOScheduler(timezone=tz)

    async def job():
        logger.info("Выполняется задача получения слова")
        async for db in get_db():
            async with httpx.AsyncClient() as client:
                await fetch_wordle_answer(db=db, client=client)
        logger.info("Задача получения слова завершена")

    scheduler.add_job(job, 'cron', hour=0, minute=5, timezone=tz)
    scheduler.start()


async def wordle_tracker_scheduler():
    logger.info("Запуск основного цикла(получение слова)")
    await start_scheduler()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Шедулер остановлен(получение слова)")


if __name__ == "__main__":
    asyncio.run(wordle_tracker_scheduler())
