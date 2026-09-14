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
from src.auth.interface.rate_limiter import IPRateLimiter
from src.auth.interface.attempt_limiter import FailedAttemptLimiter
from src.auth.adapters.custom_auth_service import CustomAuthAdapter
from src.auth.adapters.redis_otp_store import RedisOTPStore
from src.auth.adapters.redis_rate_limiter import RedisIPRateLimiter
from src.auth.adapters.redis_attempt_limiter import RedisFailedAttemptLimiter
from src.db.interfaces.interface import UserRepository, PaperRepository, ChunkRepository
from src.db.dependencies import get_user_repository, get_paper_repository, get_chunk_repository
from src.exception.exceptions import PermissionError_, RateLimitError
from src.paper.schemas import PaperGenerateRequest
from src.paper.quota import first_n_chapter_names

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)
otp_store: Optional[OTPStore] = None
ip_rate_limiter: Optional[IPRateLimiter] = None
attempt_limiter: Optional[FailedAttemptLimiter] = None


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
def get_ip_rate_limiter() -> IPRateLimiter:
    global ip_rate_limiter
    if ip_rate_limiter is None:
        redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
        ip_rate_limiter = RedisIPRateLimiter(redis_client=redis_client)
        return ip_rate_limiter
    else:
        return ip_rate_limiter


@lru_cache
def get_attempt_limiter() -> FailedAttemptLimiter:
    global attempt_limiter
    if attempt_limiter is None:
        redis_client = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)
        attempt_limiter = RedisFailedAttemptLimiter(redis_client=redis_client)
        return attempt_limiter
    else:
        return attempt_limiter


def get_client_ip(request: Request) -> str:
    # The app sits behind exactly one trusted proxy (Caddy, see docs/DEPLOYMENT.md), which
    # *appends* the real client IP to any X-Forwarded-For it receives (standard reverse-proxy
    # behavior, same as nginx/Go's httputil.ReverseProxy) rather than replacing it. So the LAST
    # entry is the one Caddy itself observed; anything earlier is attacker-supplied and spoofable
    # — an attacker sending a fake leading value on every request could otherwise get a fresh
    # rate-limit bucket each time. Do not change this to [0] without adding a trusted-proxy-count
    # setting first.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def ip_rate_limit(scope: str, limit: int, window_seconds: int):
    """FastAPI dependency factory: throttles a route per client IP. Used on public,
    unauthenticated endpoints (register, send-email) that would otherwise let a single actor
    mint unlimited accounts/OTP emails."""
    async def _check(
        request: Request,
        rate_limiter: IPRateLimiter = Depends(get_ip_rate_limiter),
    ) -> None:
        ip = get_client_ip(request)
        allowed = await rate_limiter.check_and_increment(key=f"{scope}:{ip}", limit=limit, window_seconds=window_seconds)
        if not allowed:
            raise RateLimitError(message="Too many requests from this network. Please try again later.")

    return _check


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
        user_repo : UserRepository = Depends(get_user_repository),
        attempt_limiter : FailedAttemptLimiter = Depends(get_attempt_limiter)
) -> AuthService:
    return AuthService(
        email_service=email_service,
        otp_store=otp_storage,
        auth=auth,
        user_repo=user_repo,
        attempt_limiter=attempt_limiter
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


async def enforce_generation_quota(
    paper_request: PaperGenerateRequest,
    current_user: dict = Depends(get_current_user),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    paper_repo: PaperRepository = Depends(get_paper_repository),
):
    if current_user.get("is_superuser"):
        return

    all_chapters = await asyncio.to_thread(chunk_repo.get_subject_chapters, subject=paper_request.subject)
    allowed = set(first_n_chapter_names(all_chapters, 2))

    if not set(paper_request.chapters) <= allowed:
        chapter_list = ", ".join(sorted(allowed, key=int))
        raise PermissionError_(message=f"Free accounts can only generate chapters {chapter_list} of a subject.")

    user_id = extract_user_id(current_user)
    past = await asyncio.to_thread(paper_repo.get_user_generation_records, user_id=user_id)
    past_subjects = {r["subject"] for r in past if r.get("subject")}

    if past_subjects and paper_request.subject not in past_subjects:
        raise PermissionError_(message="Free accounts are limited to one subject.")

    past_chapters_this_subject = {
        c for r in past if r.get("subject") == paper_request.subject for c in (r.get("chapters") or [])
    }
    total_chapters = past_chapters_this_subject | set(paper_request.chapters)
    if len(total_chapters) > 2:
        raise PermissionError_(message="Free accounts are limited to 2 chapters total.")


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
