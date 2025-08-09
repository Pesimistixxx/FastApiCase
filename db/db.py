from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from db.config import settings

async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=True)
async_session = async_sessionmaker(bind=async_engine, class_=AsyncSession)
