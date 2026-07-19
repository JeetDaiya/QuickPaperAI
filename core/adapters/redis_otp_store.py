from core.interfaces.otp_store import OTPStore
from upstash_redis.asyncio import  Redis
from typing import Optional


class RedisOTPStore(OTPStore):
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    def _otp_key(self, email: str) -> str:
        return f"otp:{email}"

    def _cooldown_key(self, email: str) -> str:
        return f"cooldown:{email}"

    def _attempt_key(self, email: str) -> str:
        return f"attempts:{email}"

    def _lockout_key(self, email: str) -> str:
        return f"lockout:{email}"

    async def save_otp(self, email : str, otp_code: str, expire_seconds: int = 600) -> None:
       await self.redis_client.set(key=self._otp_key(email), value=otp_code, ex=expire_seconds)

    async  def get_otp(self, email: str) -> Optional[str]:
        return await self.redis_client.get(key=self._otp_key(email))



    async def set_send_cooldown(self, email: str, cooldown_seconds: int = 60) -> bool:
        key = self._cooldown_key(email)
        exists = await self.redis_client.exists(key)

        if exists:
            return True
        else:
            await self.redis_client.set(key=key, ex=cooldown_seconds, value="1")
            return False

    async def increment_failed_attempts(self, email: str, max_attempts : int = 3, lock_seconds: int = 900) -> bool:
        attempt_key = self._attempt_key(email)
        lockout_key =  self._lockout_key(email)
        attempts = await self.redis_client.incr(attempt_key)

        if attempts >= max_attempts:
            await self.redis_client.set(key=lockout_key, value="locked", ex=lock_seconds)
            await self.redis_client.delete(attempt_key)
            return True
        else:
            return False


    async def  is_locked_out(self, email: str) -> bool:
        lockout_key = self._lockout_key(email)
        exists = await self.redis_client.exists(lockout_key)
        return bool(exists)

    async def delete_otp(self, email: str) -> None:
        await self.redis_client.delete(self._otp_key(email))
        await self.redis_client.delete(self._cooldown_key(email))
        await self.redis_client.delete(self._attempt_key(email))
        await self.redis_client.delete(self._lockout_key(email))












