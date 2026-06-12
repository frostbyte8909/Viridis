import asyncio
from app.db.session import AsyncSessionLocal
from app.models.db import Tenant, Plan, ApiKey
import hashlib
from app.config import settings

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        # Just create tenant/plan
        tenant = Tenant(name="Load Test Tenant", tier="enterprise")
        
        # We need a massive plan for normal/hog, and a restricted plan for brute/spike?
        # The stress test hits /admit. 
        # Let's just create a generic plan with high limits so they actually get tested by the Sliding Window, 
        # or maybe we should set them realistically.
        # "brute forcer tries to blast past sliding window", so sliding window = 100
        # "sneaky spiker tries to exhaust token bucket", so burst = 50, refill = 5
        
        plan_normal = Plan(
            name="Normal Plan", requests_per_minute=100000, burst_capacity=1000, burst_refill_rate=100.0, max_concurrency=2000, cooldown_seconds=0, tier="test"
        )
        plan_brute = Plan(
            name="Brute Plan", requests_per_minute=100, burst_capacity=500, burst_refill_rate=10.0, max_concurrency=5000, cooldown_seconds=0, tier="test"
        )
        plan_spike = Plan(
            name="Spike Plan", requests_per_minute=100000, burst_capacity=50, burst_refill_rate=5.0, max_concurrency=5000, cooldown_seconds=0, tier="test"
        )
        plan_hog = Plan(
            name="Hog Plan", requests_per_minute=100000, burst_capacity=5000, burst_refill_rate=100.0, max_concurrency=10, cooldown_seconds=0, tier="test"
        )
        
        session.add_all([tenant, plan_normal, plan_brute, plan_spike, plan_hog])
        await session.commit()
        await session.refresh(tenant)
        await session.refresh(plan_normal)
        await session.refresh(plan_brute)
        await session.refresh(plan_spike)
        await session.refresh(plan_hog)

        # Keys
        keys_to_seed = [
            ("viridis_dummykey123", plan_normal),
            ("viridis_brute123", plan_brute),
            ("viridis_spike123", plan_spike),
            ("viridis_hog123", plan_hog),
        ]
        
        for raw_key, plan in keys_to_seed:
            key_hash = hashlib.sha256(f"{raw_key}{settings.server_pepper}".encode()).hexdigest()
            api_key = ApiKey(
                tenant_id=tenant.id,
                plan_id=plan.id,
                key_hash=key_hash,
                key_prefix=raw_key[:8],
                scopes=["all"],
                is_active=True
            )
            session.add(api_key)
            
        await session.commit()
        print("Seeded stress test keys.")

if __name__ == "__main__":
    asyncio.run(seed())
