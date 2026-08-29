import secrets
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.interface.interface import AuthService
from src.mail.interfaces.interface import EmailService
from src.auth.interface.otp_store import OTPStore
from src.db.interfaces.interface import UserRepository
from src.dependencies import get_email_service, get_otp_store, get_authentication_service, get_current_user, get_user_repository
from src.auth.user_schemas import (
    UserRegister, UserResponse, EmailRequest, OTPVerification, 
    OTPPurpose, ResetPasswordRequest, FCMTokenRequest, NotificationToggleRequest
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
async def register_user(user: UserRegister, auth_service: AuthService = Depends(get_authentication_service)):
    user_email = user.email
    user_name = user.name
    password = user.password
    new_user = await auth_service.register_user(email=user_email, password=password, name=user_name)
    return new_user


@auth_routes.post('/login', response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_authentication_service)):
    email = form_data.username
    password = form_data.password
    token = await auth_service.authenticate_user(email=email, password=password)
    return token


@auth_routes.post("/send-email")
async def send_verification_email(
    email_req: EmailRequest, 
    email_service: EmailService = Depends(get_email_service), 
    otp_store: OTPStore = Depends(get_otp_store), 
    auth_service: AuthService = Depends(get_authentication_service)
):
    email = email_req.email.lower().strip()
    purpose = email_req.purpose
    user = await auth_service.get_user(email=email)

    if purpose == OTPPurpose.SIGNUP:
        if not user:
            raise HTTPException(status_code=404, detail="User not found, please register first")
        if user.get("is_active", False):
            raise HTTPException(status_code=400, detail="User already verified, please log in again")

    elif purpose == OTPPurpose.RESET_PASSWORD:
        if not user:
            raise HTTPException(status_code=404, detail="User not found, please register first")
        if user and not user.get("is_active", False):
            raise HTTPException(status_code=400, detail="User is not verified, please verify your account first")

    if await otp_store.set_send_cooldown(email=email, purpose=purpose.value):
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before request another code")

    try:
        otp_code = generate_otp()
        await otp_store.save_otp(email=email, otp_code=otp_code, purpose=purpose.value)
        await send_email(email=email, otp_code=otp_code, email_service=email_service)
        return {"message": "OTP sent successfully. Please check your email."}
    except Exception as e:
        await otp_store.delete_otp(email=email, purpose=purpose.value)
        raise HTTPException(status_code=500, detail="Failed to send email.")


@auth_routes.post("/verify-otp")
async def verify_otp(
    data: OTPVerification, 
    otp_store: OTPStore = Depends(get_otp_store),
    auth_service: AuthService = Depends(get_authentication_service)
):
    email = data.email.lower().strip()
    purpose = data.purpose

    if await otp_store.is_locked_out(email=email, purpose=purpose.value):
        raise HTTPException(status_code=403, detail="Too many failed verification, Please try again after 15 minutes.")

    stored_otp = await otp_store.get_otp(email=email, purpose=purpose.value)
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP not found or expired. Please request a new code.")

    if not otp_store.verify_otp(data.otp, stored_otp):
        is_now_locked = await otp_store.increment_failed_attempts(email=email, purpose=purpose.value)
        if is_now_locked:
            raise HTTPException(status_code=403, detail="Too many verification attempts. Your verification code is locked for 15 minutes.")
        else:
            raise HTTPException(status_code=400, detail="Invalid OTP.")

    await otp_store.delete_otp(email=email, purpose=purpose.value)

    if purpose == OTPPurpose.SIGNUP:
        await auth_service.activate_user(email=email)
        token_data = auth_service.create_token_for_email(email=email)
        return {
            "message": "Email verified successfully!",
            "access_token": token_data["access_token"],
            "token_type": token_data["token_type"]
        }
    elif purpose == OTPPurpose.RESET_PASSWORD:
        reset_token = auth_service.create_token_for_email(email=email, token_type="reset", expires_minutes=15)
        return {
            "message": "OTP verified successfully. You can now reset your password.",
            "reset_token": reset_token["access_token"],
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid purpose.")


@auth_routes.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_authentication_service)
):
    try:
        user = await auth_service.verify_session(data.token, expected_type="reset")
    except HTTPException as e:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    
    if user.get("email").lower().strip() != data.email.lower().strip():
        raise HTTPException(status_code=400, detail="Invalid reset request parameters.")

    await auth_service.update_password(email=data.email.lower().strip(), new_password=data.new_password)
    return {"message": "Password reset successfully."}


@auth_routes.post("/device-token")
async def save_device_token(
    data: FCMTokenRequest,
    current_user: dict = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    user_id = str(current_user["id"])
    success = user_repo.save_fcm_token(user_id=user_id, token=data.token)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save FCM device token.")
    return {"message": "FCM device token registered successfully."}


@auth_routes.post("/notification-settings")
async def update_notification_settings(
    notification_toggle_request : NotificationToggleRequest,
    current_user: dict = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    user_id = str(current_user["id"])
    notifications_enabled = notification_toggle_request.notifications_enabled
    success = user_repo.update_notification_perms(user_id=user_id, notifications_enabled=notifications_enabled)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update notification settings.")
    return {"message": "Notification preferences updated successfully."}


@auth_routes.get("/notification-settings")
async def get_notification_settings(
    current_user: dict = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),

):
    user_id = str(current_user["id"])
    token_data = user_repo.get_fcm_token(user_id=user_id)
    perms_data = user_repo.get_notification_perms(user_id=user_id)
    
    fcm_token = token_data[0].get("fcm_token") if token_data else None
    notifications_enabled = perms_data[0].get("notifications_enabled", True) if perms_data else True
    
    return {
        "fcm_token": fcm_token,
        "notifications_enabled": notifications_enabled
    }
