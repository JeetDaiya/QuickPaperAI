from upstash_redis.asyncio import Redis

from src.auth.interface.rate_limiter import IPRateLimiter
from src.exception.exceptions import RepositoryError


class RedisIPRateLimiter(IPRateLimiter):
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    async def check_and_increment(self, key: str, limit: int, window_seconds: int) -> bool:
        try:
            redis_key = f"ratelimit:{key}"
            count = await self.redis_client.incr(redis_key)
            # Fixed window: TTL is set only on the first hit, so the window expires exactly
            # window_seconds after it opened. Refreshing it on every hit (as RedisOTPStore's
            # failed-attempt counter does) would mean continued traffic — including the blocked
            # requests themselves — keeps pushing the window out, locking the key out forever
            # under sustained load instead of resetting after one window.
            if count == 1:
                await self.redis_client.expire(redis_key, window_seconds)
            return count <= limit
        except Exception as e:
            raise RepositoryError(key=key) from e
