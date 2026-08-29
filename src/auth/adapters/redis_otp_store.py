import hashlib
import hmac

from src.auth.interface.otp_store import OTPStore
from upstash_redis.asyncio import  Redis
from typing import Optional


class RedisOTPStore(OTPStore):
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    def _otp_key(self, email: str, purpose: str) -> str:
        return f"otp:{purpose}:{email}"

    def _cooldown_key(self, email: str, purpose: str) -> str:
        return f"cooldown:{purpose}:{email}"

    def _attempt_key(self, email: str, purpose: str) -> str:
        return f"attempts:{purpose}:{email}"

    def _lockout_key(self, email: str, purpose: str) -> str:
        return f"lockout:{purpose}:{email}"

    def _hash_otp(self, otp_code: str) -> str:
        return hashlib.sha256(otp_code.encode("utf-8")).hexdigest()

    async def save_otp(self, email : str, otp_code: str, purpose: str, expire_seconds: int = 600) -> None:
       await self.redis_client.set(key=self._otp_key(email, purpose), value=self._hash_otp(otp_code), ex=expire_seconds)

    async def get_otp(self, email: str, purpose: str) -> Optional[str]:
        return await self.redis_client.get(key=self._otp_key(email, purpose))

    def verify_otp(self, submitted_otp: str, stored_value: str) -> bool:
        # Constant-time comparison of hashes to avoid timing side-channels.
        return hmac.compare_digest(self._hash_otp(submitted_otp), stored_value)

    async def set_send_cooldown(self, email: str, purpose: str, cooldown_seconds: int = 60) -> bool:
        key = self._cooldown_key(email, purpose)
        # Atomic check-and-set: SET NX returns a truthy result only if the key was created,
        # closing the race where two concurrent requests both pass a separate exists() check.
        result = await self.redis_client.set(key=key, value="1", ex=cooldown_seconds, nx=True)
        was_set = bool(result)
        return not was_set  # True == already cooling down

    async def increment_failed_attempts(self, email: str, purpose: str, max_attempts : int = 3, lock_seconds: int = 900) -> bool:
        attempt_key = self._attempt_key(email, purpose)
        lockout_key =  self._lockout_key(email, purpose)
        attempts = await self.redis_client.incr(attempt_key)
        # Give the counter its own sliding-window TTL on every increment so stale failures
        # from an abandoned flow age out instead of persisting and locking out a later attempt.
        await self.redis_client.expire(attempt_key, 600)

        if attempts >= max_attempts:
            await self.redis_client.set(key=lockout_key, value="locked", ex=lock_seconds)
            await self.redis_client.delete(attempt_key)
            return True
        else:
            return False


    async def  is_locked_out(self, email: str, purpose: str) -> bool:
        lockout_key = self._lockout_key(email, purpose)
        exists = await self.redis_client.exists(lockout_key)
        return bool(exists)

    async def delete_otp(self, email: str, purpose: str) -> None:
        await self.redis_client.delete(self._otp_key(email, purpose))
        await self.redis_client.delete(self._cooldown_key(email, purpose))
        await self.redis_client.delete(self._attempt_key(email, purpose))
        await self.redis_client.delete(self._lockout_key(email, purpose))
