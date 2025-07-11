import asyncio
import datetime
import os
import pytz
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base

from db.db_depends import get_db

load_dotenv()

Base = declarative_base()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Skin_model(Base):
    __tablename__ = 'skins'

    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String)
    price = Column(Float)
    is_active = Column(Boolean, default=True)


async def fetch_steam_prices(db: AsyncSession, client: httpx.AsyncClient):
    try:
        result = await db.execute(select(Skin_model).where(Skin_model.is_active == True))
        items = result.scalars().all()

        for item in items:
            params = {
                'appid': 730,
                'currency': 5,
                'market_hash_name': item.tag
            }

            response = await client.get('https://steamcommunity.com/market/priceoverview/', params=params)
            data = response.json()

            if response.status_code == 429 or response.status_code == 502:
                logger.warning("Too many requests. Waiting...")
                await asyncio.sleep(60)

            if data['success'] and 'median_price' in data:
                price = float(data['median_price'].split(' ')[0].replace(',', '.'))
                item.price = price
                await db.flush()

            await asyncio.sleep(10)

        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении цен: {e}")
        await db.rollback()


async def start_scheduler():
    tz = pytz.timezone(os.getenv("TIMEZONE", "UTC"))
    scheduler = AsyncIOScheduler(timezone=tz)

    async def job():
        logger.info("Выполняется задача обновления цен")
        async for db in get_db():
            async with httpx.AsyncClient() as client:
                await fetch_steam_prices(db=db, client=client)
        logger.info("Задача обновления цен завершена")

    #scheduler.add_job(job, 'interval', minutes=60, next_run_time=datetime.datetime.now())
    scheduler.add_job(job, 'interval', minutes=60)
    scheduler.start()


async def price_tracker_scheduler():
    logger.info("Запуск основного цикла(обновление цен)")
    await start_scheduler()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Шедулер остановлен(обновление цен)")


if __name__ == "__main__":
    asyncio.run(price_tracker_scheduler())
