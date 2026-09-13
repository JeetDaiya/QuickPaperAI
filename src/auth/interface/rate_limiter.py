from abc import ABC, abstractmethod


class IPRateLimiter(ABC):
    @abstractmethod
    async def check_and_increment(self, key: str, limit: int, window_seconds: int) -> bool:
        pass
