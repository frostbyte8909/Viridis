from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

engine = create_async_engine(
    str(settings.database_url),
    pool_pre_ping=True,
    echo=False,
    pool_size=20,
    max_overflow=10
)
AsyncSessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
