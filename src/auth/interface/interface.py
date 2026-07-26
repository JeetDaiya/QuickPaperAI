from abc import  ABC, abstractmethod
from typing import Optional


class AuthService(ABC):
    @abstractmethod
    async def register_user(self, email: str, password: str, name: str) -> dict:
        pass

    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> dict:
        pass

    @abstractmethod
    async def verify_session(self, token: str) -> dict:
        pass

    @abstractmethod
    async def activate_user(self, email: str) -> None:
        pass

    @abstractmethod
    def create_token_for_email(self, email: str) -> dict:
        pass

    @abstractmethod
    async def get_user(self, email: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def update_password(self, email: str, new_password: str) -> None:
        pass



