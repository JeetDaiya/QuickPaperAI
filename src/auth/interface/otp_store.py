from abc import ABC, abstractmethod
from typing import Optional



class OTPStore(ABC):
    @abstractmethod
    async def save_otp(self, email : str, otp_code: str, expire_seconds: int = 600) -> None:
        pass

    @abstractmethod
    async def get_otp(self, email: str) -> Optional[str]:
        pass

    @abstractmethod
    async def delete_otp(self, email: str):
        pass

    @abstractmethod
    async def set_send_cooldown(self, email: str, cooldown_seconds: int = 60)-> bool:
        pass

    @abstractmethod
    async def increment_failed_attempts(self, email: str, max_attempts : int = 3, lock_seconds: int = 900) -> bool:
        pass

    @abstractmethod
    async def is_locked_out(self, email: str) -> bool:
        pass


