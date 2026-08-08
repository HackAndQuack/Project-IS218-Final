# app/auth/redis.py
import aioredis
from app.core.config import get_settings

settings = get_settings()

async def get_redis():
    if not hasattr(get_redis, "redis"):
        get_redis.redis = await aioredis.from_url(
            settings.REDIS_URL or "redis://localhost"
        )
    return get_redis.redis

async def add_to_blacklist(jti: str, exp: int):
    """Add a token's JTI to the blacklist. No-ops if Redis is unreachable (optional dependency)."""
    try:
        redis = await get_redis()
        await redis.set(f"blacklist:{jti}", "1", ex=exp)
    except Exception:
        pass

async def is_blacklisted(jti: str) -> bool:
    """Check if a token's JTI is blacklisted. Fails open (not blacklisted) if Redis is unreachable."""
    try:
        redis = await get_redis()
        return await redis.exists(f"blacklist:{jti}")
    except Exception:
        return False