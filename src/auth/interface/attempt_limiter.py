from abc import ABC, abstractmethod


class FailedAttemptLimiter(ABC):
    @abstractmethod
    async def is_locked_out(self, key: str) -> bool:
        pass

    @abstractmethod
    async def register_failure(self, key: str, max_attempts: int, window_seconds: int, lock_seconds: int) -> bool:
        """Record one failure for `key`. Returns True if this failure just triggered a lockout."""
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        pass
