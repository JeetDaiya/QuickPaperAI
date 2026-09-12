import secrets
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.services.service import AuthService
from src.mail.interfaces.interface import EmailService
from src.dependencies import get_current_user, \
    get_auth_service
from src.auth.user_schemas import (
    UserRegister, UserResponse, EmailRequest, OTPVerification, 
     ResetPasswordRequest, FCMTokenRequest, NotificationToggleRequest
)
from src.auth.token_schemas import Token
from src.auth.email_template import render_otp_email

auth_routes = APIRouter(prefix='/auth')


def generate_otp(length: int = 6):
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


async def send_email(email: str, otp_code: str, email_service: EmailService):
    html_content = render_otp_email(otp_code=otp_code)
    await email_service.send_email(subject="Your Account Verification OTP", recipient=email, body=html_content)


@auth_routes.post('/register', response_model=UserResponse)
async def register_user(user: UserRegister, auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.register_user(user=user)


@auth_routes.post('/login', response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)):
    email = form_data.username
    password = form_data.password
    return await auth_service.login_user(email=email, password=password)


@auth_routes.post("/send-email")
async def send_verification_email(
    email_req: EmailRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    email = email_req.email.lower().strip()
    purpose = email_req.purpose
    return await auth_service.send_verification_email(email=email, purpose=purpose)

@auth_routes.post("/verify-otp")
async def verify_otp(
    data: OTPVerification,
    auth_service: AuthService = Depends(get_auth_service)
):
    email = data.email.lower().strip()
    purpose = data.purpose
    otp = data.otp
    return await auth_service.verify_otp(email=email, otp=otp, purpose=purpose)



@auth_routes.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    email = data.email.lower().strip()
    new_password = data.new_password

    return await auth_service.reset_password(email=email, new_password=new_password, token=data.token)


@auth_routes.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@auth_routes.post("/device-token")
async def save_device_token(
    data: FCMTokenRequest,
    current_user: dict = Depends(get_current_user),
    auth_service : AuthService = Depends(get_auth_service),
):
    user_id = str(current_user["id"])
    token = data.token
    return await auth_service.save_device_token(token=token, user_id=user_id)


@auth_routes.post("/notification-settings")
async def update_notification_settings(
    notification_toggle_request : NotificationToggleRequest,
    current_user: dict = Depends(get_current_user),
    auth_service : AuthService = Depends(get_auth_service),
):
    user_id = str(current_user["id"])
    notifications_enabled = notification_toggle_request.notifications_enabled
    return  await auth_service.update_notification_settings(user_id=user_id,notifications_enabled=notifications_enabled)



@auth_routes.get("/notification-settings")
async def get_notification_settings(
    current_user: dict = Depends(get_current_user),
    auth_service : AuthService = Depends(get_auth_service),

):
    user_id = str(current_user["id"])
    return await auth_service.get_notification_settings(user_id=user_id)
