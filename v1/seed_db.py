import asyncio
from app.db.session import AsyncSessionLocal
from app.models.db import Tenant, Plan
from app.services.key_service import issue_raw_key, create_api_key_record

async def seed():
    async with AsyncSessionLocal() as session:
        tenant = Tenant(name="Acme Corp", tier="enterprise")
        plan = Plan(
            name="Enterprise Burst",
            requests_per_minute=6000,
            burst_capacity=100,
            burst_refill_rate=10.0,
            max_concurrency=50,
            cooldown_seconds=0,
            tier="enterprise"
        )
        session.add(tenant)
        session.add(plan)
        await session.commit()
        await session.refresh(tenant)
        await session.refresh(plan)

        raw_key = issue_raw_key()
        api_key = create_api_key_record(tenant.id, plan.id, raw_key)
        session.add(api_key)
        await session.commit()
        
        print(f"RAW_KEY={raw_key}")

if __name__ == "__main__":
    asyncio.run(seed())
