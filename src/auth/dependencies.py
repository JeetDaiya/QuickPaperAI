import asyncio
from typing import Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from upstash_redis.asyncio import Redis

from src.auth.services.service import AuthService
from src.exception.global_exception_handler import AppError
from src.mail.interfaces.interface import EmailService
from src.mail.dependencies import get_email_service
from src.base_settings import settings
from src.auth.interface.interface import AuthInterface
from src.auth.interface.otp_store import OTPStore
from src.auth.adapters.custom_auth_service import CustomAuthAdapter
from src.auth.adapters.redis_otp_store import RedisOTPStore
from src.db.interfaces.interface import UserRepository, PaperRepository
from src.db.dependencies import get_user_repository, get_paper_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)
otp_store: Optional[OTPStore] = None


@lru_cache
def get_otp_store() -> OTPStore:
    global otp_store
    if otp_store is None:
        redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
        otp_store = RedisOTPStore(redis_client=redis_client)
        return otp_store
    else:
        return otp_store


@lru_cache
def get_authentication_adapter(user_repo: UserRepository = Depends(get_user_repository)) -> AuthInterface:
    return CustomAuthAdapter(
        algorithm=settings.ALGORITHM,
        secret_key=settings.SECRET_KEY,
        user_repo=user_repo,
        token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )


def get_auth_service(
        email_service : EmailService =  Depends(get_email_service),
        otp_storage : OTPStore = Depends(get_otp_store),
        auth : AuthInterface = Depends(get_authentication_adapter),
        user_repo : UserRepository = Depends(get_user_repository)
) -> AuthService:
    return AuthService(
        email_service=email_service,
        otp_store=otp_storage,
        auth=auth,
        user_repo=user_repo
    )


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthInterface = Depends(get_authentication_adapter)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


    if not token and (request.url.path.endswith("/stream") or "/download/" in request.url.path):
        token = request.query_params.get("token")

    if not token:
        raise credentials_exception

    try:
        user = await auth_service.verify_session(token=token)
        return user
    except (HTTPException, AppError) as e:
        raise e
    except Exception:
        raise credentials_exception


def extract_user_id(current_user: dict) -> str:
    user_id = str(current_user.get("id") or current_user.get("user_id") or "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User identity missing in session token")
    return user_id


async def verify_thread_ownership(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    paper_repo: PaperRepository = Depends(get_paper_repository)
):
    user_id = extract_user_id(current_user)

    try:
        session = await asyncio.to_thread(paper_repo.get_paper_session, thread_id=thread_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You do not own this paper session.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied or paper session not found.")
