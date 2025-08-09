import asyncio
import datetime
import os
import pytz
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from db.db_depends import get_db
from app.case.models import Case_model  # noqa: F401
from app.skin.models import Skin_model  # noqa: F401
from app.models_associations import Case_Skin_model  # noqa: F401
from app.notification.models import Notification_model  # noqa: F401
from app.models_associations import User_Skin_model
from app.battles.models import Battle_model
from app.auth.models import Session_model, User_model

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def clean_expired_sessions(db: AsyncSession):
    try:
        await db.execute(delete(Session_model).where(
            Session_model.expires <= datetime.datetime.now()
        ))

        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при очистки сессий: {e}")
        await db.rollback()


async def clean_unused_skins(db: AsyncSession):
    try:
        await db.execute(delete(User_Skin_model)
                         .where(~User_Skin_model.is_active))
        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при очистки сессий: {e}")
        await db.rollback()


async def clean_expired_battles(db: AsyncSession):
    try:
        result = await db.scalars(select(Battle_model)
                                  .where(Battle_model.created
                                         + datetime.timedelta(hours=1)
                                         <= datetime.datetime.now())
                                  .options(selectinload(Battle_model.users)))

        deletable_battles = result.all()

        battle_ids = [battle.id for battle in deletable_battles]
        user_ids = [user.id for battle in deletable_battles if battle.is_active for user in battle.users]

        total_refund = sum(battle.price for battle in deletable_battles if battle.is_active for _ in battle.users)
        await db.execute(
            update(User_model)
            .where(User_model.id.in_(user_ids))
            .values(balance=User_model.balance + total_refund)
        )

        await db.execute(delete(Battle_model).where(Battle_model.id.in_(battle_ids)))
        await db.commit()

    except Exception as e:
        logger.error(f"Ошибка при очистки сессий: {e}")
        await db.rollback()


async def start_scheduler():
    tz = pytz.timezone(os.getenv("TIMEZONE", "UTC"))
    scheduler = AsyncIOScheduler(timezone=tz)

    async def clean_expired_sessions_job():
        logger.info("Начало очистки бд от старых сессий")
        async for db in get_db():
            await clean_expired_sessions(db=db)
        logger.info("Конец очистки бд от старых сессий")

    async def clean_expired_battles_job():
        logger.info("Начало очистки бд от старых баттлов")
        async for db in get_db():
            await clean_expired_battles(db=db)
        logger.info("Конец очистки бд от старых баттлов")

    async def clean_unused_skins_job():
        logger.info("Начало очистки бд от неиспользуемых скинов")
        async for db in get_db():
            await clean_unused_skins(db=db)
        logger.info("Конец очистки бд от неиспользуемых скинов")

    scheduler.add_job(clean_expired_sessions_job, 'interval', minutes=5, next_run_time=datetime.datetime.now())
    scheduler.add_job(clean_expired_battles_job, 'interval', hours=1, next_run_time=datetime.datetime.now())
    scheduler.add_job(clean_unused_skins_job, 'interval', hours=1, next_run_time=datetime.datetime.now())

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
