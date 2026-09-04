import asyncio
import base64
import hashlib
import uuid
from typing import Optional, Tuple

from fastapi import HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from supabase import SupabaseException

from src.auth.interface.interface import AuthService
from src.db.interfaces.interface import UserRepository


class CustomAuthService(AuthService):
    def __init__(self, user_repo : UserRepository, secret_key : str, algorithm: str, token_expire_minutes: int):
        self.user_repo = user_repo
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_minutes = token_expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


    def _prehash_password(self, plain_password: str) -> str:
        # bcrypt silently ignores input past 72 bytes; SHA-256 pre-hash (base64 to keep it
        # inside bcrypt's charset and under 72 bytes) means the full password contributes.
        digest = hashlib.sha256(plain_password.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("ascii")

    async def _get_hashed_password(self, plain_password: str) -> str:
        # bcrypt is CPU-bound; offload so it doesn't block the event loop.
        return await asyncio.to_thread(self.pwd_context.hash, self._prehash_password(plain_password))

    async def _verify_password(self, plain_password: str, hashed_password: str) -> Tuple[bool, bool]:
        # Returns (is_valid, used_legacy). Try the new pre-hashed scheme first; fall back to the
        # legacy raw-password scheme so pre-existing hashes still verify (caller re-hashes on hit).
        new_ok = await asyncio.to_thread(self.pwd_context.verify, self._prehash_password(plain_password), hashed_password)
        if new_ok:
            return True, False
        try:
            legacy_ok = await asyncio.to_thread(self.pwd_context.verify, plain_password, hashed_password)
        except Exception:
            legacy_ok = False
        return (True, True) if legacy_ok else (False, False)

    def _create_access_token(self, data : dict, token_type: str = "access", expires_minutes: Optional[int] = None):
        to_encode = data.copy()

        minutes = expires_minutes if expires_minutes is not None else self.token_expire_minutes
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=minutes)
        to_encode.update({
            "exp": expire,
            "type": token_type,
            "iat": now,
            "nbf": now,
            "jti": uuid.uuid4().hex,
        })

        encoded_jwt = jwt.encode(to_encode, key=self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    async def register_user(self, email: str, password: str, name: str) -> dict:
        try:
            db_user = self.user_repo.get_user(email=email)
        except SupabaseException as e:
            print(f"DB Error checking email {email}: {e}")
            raise HTTPException(status_code=500, detail="Database error during registration check")

        if db_user is not None:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password and create user in DB
        hashed_password = await self._get_hashed_password(password)
        try:
            new_user = self.user_repo.create_user(email=email, hashed_password=hashed_password, name=name)
            if not new_user:
                raise HTTPException(status_code=500, detail="Failed to create user record")
            return new_user
        except SupabaseException as e:
            print(f"DB Error creating user {email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to register user due to database error")

    async def authenticate_user(self, email: str, password: str) -> dict:
        try:
            user = self.user_repo.get_user(email=email)
        except SupabaseException as e:
            print(f"❌ DB Error fetching user {email}: {e}")
            raise HTTPException(status_code=500, detail="Database authentication error")

        if user is None:
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        if not user.get("is_active", False):
            raise HTTPException(
                status_code=403, 
                detail="Your email is not verified. Please verify your email first."
            )

        is_valid, used_legacy = await self._verify_password(password, user['hashed_password'])
        if not is_valid:
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        # Transparently migrate legacy (raw-password) hashes to the new pre-hash scheme on login.
        if used_legacy:
            try:
                upgraded = await self._get_hashed_password(password)
                self.user_repo.update_user_password(email=email, new_hashed_password=upgraded)
            except Exception as e:
                print(f"[WARN] Password hash upgrade failed for {email}: {e}")

        access_token = self._create_access_token(data={"sub" : email}, token_type="access")

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def verify_session(self, token: str, expected_type: str = "access") -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email = payload.get("sub")

            if not email:
                raise HTTPException(status_code=401, detail="Invalid token")

            if payload.get("type") != expected_type:
                raise HTTPException(status_code=401, detail="Invalid token type")

            user = self.user_repo.get_user(email=email)

        except JWTError:
            raise HTTPException(status_code=401, detail="Session expired or invalid Token")
        except SupabaseException as e:
            print(f"[ERROR] DB Error fetching session user: {e}")
            raise HTTPException(status_code=500, detail="Database session validation error")

        if not user:
            raise HTTPException(status_code=401, detail="User session not found")

        return user

    async def activate_user(self, email: str) -> None:
        try:
            self.user_repo.activate_user(email=email)
        except SupabaseException as e:
            print(f"DB Error activating user {email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to activate user account")

    def create_token_for_email(self, email: str, token_type: str = "access", expires_minutes: Optional[int] = None) -> dict:
        access_token = self._create_access_token(data={"sub": email}, token_type=token_type, expires_minutes=expires_minutes)
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def get_user(self, email: str) -> dict:
        try:
            user = self.user_repo.get_user(email=email)
            return user
        except SupabaseException as e:
            raise HTTPException(status_code=500, detail="Database error during retrieval")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def update_password(self, email: str, new_password: str) -> None:
        try:
            hashed_password = await self._get_hashed_password(new_password)
            self.user_repo.update_user_password(email=email, new_hashed_password=hashed_password)
        except SupabaseException as e:
            print(f"DB Error resetting password for {email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to reset password")




