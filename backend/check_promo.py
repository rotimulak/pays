import asyncio
from src.db.session import get_session
from src.db.models.promo import PromoCode
from sqlalchemy import select

async def check_promo_codes():
    async for session in get_session():
        result = await session.execute(select(PromoCode))
        codes = result.scalars().all()
        print('Promo codes in DB:')
        for c in codes:
            print(f'  Code: "{c.code}" (active: {c.is_active})')
        break

if __name__ == "__main__":
    asyncio.run(check_promo_codes())
