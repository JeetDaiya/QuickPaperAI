from upstash_redis.asyncio import Redis

from src.auth.interface.attempt_limiter import FailedAttemptLimiter
from src.exception.exceptions import RepositoryError


class RedisFailedAttemptLimiter(FailedAttemptLimiter):
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    def _attempt_key(self, key: str) -> str:
        return f"attempts:{key}"

    def _lockout_key(self, key: str) -> str:
        return f"lockout:{key}"

    async def is_locked_out(self, key: str) -> bool:
        try:
            return bool(await self.redis_client.exists(self._lockout_key(key)))
        except Exception as e:
            raise RepositoryError(key=key) from e

    async def register_failure(self, key: str, max_attempts: int, window_seconds: int, lock_seconds: int) -> bool:
        try:
            attempt_key = self._attempt_key(key)
            attempts = await self.redis_client.incr(attempt_key)
            # Sliding window: TTL is refreshed on every failure so stale failures from an
            # abandoned attempt age out instead of persisting and locking out a later attempt.
            await self.redis_client.expire(attempt_key, window_seconds)

            if attempts >= max_attempts:
                await self.redis_client.set(key=self._lockout_key(key), value="locked", ex=lock_seconds)
                await self.redis_client.delete(attempt_key)
                return True
            return False
        except Exception as e:
            raise RepositoryError(key=key) from e

    async def reset(self, key: str) -> None:
        # Best-effort: this runs after a success, so a cleanup failure here shouldn't fail
        # the caller's request.
        try:
            await self.redis_client.delete(self._attempt_key(key))
            await self.redis_client.delete(self._lockout_key(key))
        except Exception as e:
            print(f"Failed to reset attempt limiter for {key}: {e}")
