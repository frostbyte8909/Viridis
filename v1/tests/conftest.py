import pytest
import asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, Base
from app.core.redis import redis_manager

# Use real Redis + Postgres (from GitHub Actions services or docker-compose)
REDIS_URL = "redis://localhost:6379"
DATABASE_URL = "postgresql+asyncpg://viridis:viridis_test@localhost:5432/viridis_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def redis_client():
    """Real Redis client."""
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    await client.ping()  # Verify connection
    # Load Lua scripts for token bucket
    redis_manager.redis = client
    await redis_manager._load_scripts()
    yield client
    await client.aclose()

@pytest.fixture(scope="session")
async def db_engine():
    """Real PostgreSQL engine."""
    engine = create_async_engine(DATABASE_URL)
    # create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Transaction-wrapped PostgreSQL session."""
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    SessionLocal = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture(scope="function")
def test_client(db_session, redis_client):
    """FastAPI TestClient with overridden dependencies."""
    app.dependency_overrides[get_db] = lambda: db_session
    
    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()

@pytest.fixture(scope="function", autouse=True)
async def cleanup_redis(redis_client):
    """Cleanup Redis keys before/after each test."""
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()
