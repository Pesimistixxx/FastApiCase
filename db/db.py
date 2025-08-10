from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from db.config import settings

async_engine = create_async_engine(settings.async_database_url, echo=True)
async_session = async_sessionmaker(bind=async_engine, class_=AsyncSession)
