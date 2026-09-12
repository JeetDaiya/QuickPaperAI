import asyncio
import secrets
from src.auth.email_template import render_otp_email
from src.auth.interface.interface import AuthInterface
from src.auth.interface.otp_store import OTPStore
from src.auth.user_schemas import UserRegister, OTPPurpose
from src.db.interfaces.interface import UserRepository
from src.exception.exceptions import RateLimitError, InternalServerError_, ValidationError_, AuthError
from src.exception.global_exception_handler import AppError
from src.mail.interfaces.interface import EmailService


class AuthService:
    def __init__(self, auth: AuthInterface, email_service: EmailService, otp_store: OTPStore, user_repo : UserRepository):
        self.auth = auth
        self.email_service = email_service
        self.otp_store = otp_store
        self.user_repo = user_repo

    @staticmethod
    def _generate_otp(length: int = 6):
        return "".join(str(secrets.randbelow(10)) for _ in range(length))

    async def send_email(self, email: str, otp_code: str):
        html_content = render_otp_email(otp_code=otp_code)
        await self.email_service.send_email(subject="Your Account Verification OTP", recipient=email, body=html_content)


    async def register_user(self, user : UserRegister):
        user_email = user.email
        user_name = user.name
        password = user.password
        new_user = await self.auth.register_user(email=user_email, password=password, name=user_name)
        return new_user

    async def login_user(self, email: str, password: str):
        token = await self.auth.authenticate_user(email=email, password=password)
        return token

    async def send_verification_email(self, email: str, purpose : OTPPurpose):
        GENERIC_MSG = "If an account matches this email, a verification code has been sent. Please check your email."


        user = await self.auth.get_user(email=email)

        if await self.otp_store.set_send_cooldown(email=email, purpose=purpose.value):
            raise RateLimitError(message="Please wait 60 seconds before request another code", email=email, purpose=purpose.value)

        if purpose == OTPPurpose.SIGNUP:
            eligible = bool(user) and not user.get("is_active", False)
        elif purpose == OTPPurpose.RESET_PASSWORD:
            eligible = bool(user) and user.get("is_active", False)
        else:
            eligible = False

        if not eligible:
            return {"message": GENERIC_MSG}

        try:
            otp_code = self._generate_otp()
            await self.otp_store.save_otp(email=email, otp_code=otp_code, purpose=purpose.value)
            await self.send_email(email=email, otp_code=otp_code)
            return {"message": GENERIC_MSG}
        except AppError:
            await self.otp_store.delete_otp(email=email, purpose=purpose.value)
            raise
        except Exception as e:
            await self.otp_store.delete_otp(email=email, purpose=purpose.value)
            raise InternalServerError_(email=email, purpose=purpose.value) from e

    async def verify_otp(self, email: str, purpose: OTPPurpose, otp:str):

        if await self.otp_store.is_locked_out(email=email, purpose=purpose.value):
            raise RateLimitError(message="Too many failed verification, Please try again after 15 minutes.", email=email, purpose=purpose.value)

        stored_otp = await self.otp_store.get_otp(email=email, purpose=purpose.value)
        if not stored_otp:
            raise ValidationError_(message="OTP not found or expired. Please request a new code.", email=email, purpose=purpose.value)

        if not self.otp_store.verify_otp(otp, stored_otp):
            is_now_locked = await self.otp_store.increment_failed_attempts(email=email, purpose=purpose.value)
            if is_now_locked:
                raise RateLimitError(message="Too many failed verification, Please try again after 15 minutes.", email=email, purpose=purpose.value)
            else:
                raise ValidationError_(message="Invalid OTP.", email=email, purpose=purpose.value)

        await self.otp_store.delete_otp(email=email, purpose=purpose.value)

        if purpose == OTPPurpose.SIGNUP:
            await self.auth.activate_user(email=email)
            token_data = self.auth.create_token_for_email(email=email)
            return {
                "message": "Email verified successfully!",
                "access_token": token_data["access_token"],
                "token_type": token_data["token_type"]
            }
        elif purpose == OTPPurpose.RESET_PASSWORD:
            reset_token = self.auth.create_token_for_email(email=email, token_type="reset", expires_minutes=15)
            return {
                "message": "OTP verified successfully. You can now reset your password.",
                "reset_token": reset_token["access_token"],
            }
        else:
            raise ValidationError_(message="Invalid Purpose")

    async def reset_password(self, email: str, new_password: str, token:str):
        user = await self.auth.verify_session(token, expected_type="reset")

        if user.get("email") != email:
            raise AuthError(message="Invalid reset request parameters.")

        await self.auth.update_password(email=email, new_password=new_password)
        return {"message": "Password reset successfully."}

    async def save_device_token(self, user_id: str, token: str):
        await asyncio.to_thread(self.user_repo.save_fcm_token, user_id=user_id, token=token)
        return {"message": "FCM device token registered successfully."}

    async def update_notification_settings(self, user_id: str, notifications_enabled: bool):
        success = await asyncio.to_thread(self.user_repo.update_notification_perms, user_id=user_id,
                                          notifications_enabled=notifications_enabled)

        return {"message": "Notification preferences updated successfully."}

    async def get_notification_settings(self, user_id: str):
        token_data = await asyncio.to_thread(self.user_repo.get_fcm_token, user_id=user_id)
        perms_data = await asyncio.to_thread(self.user_repo.get_notification_perms, user_id=user_id)

        fcm_token = token_data[0].get("fcm_token") if token_data else None
        notifications_enabled = perms_data[0].get("notifications_enabled", True) if perms_data else True

        return {
            "fcm_token": fcm_token,
            "notifications_enabled": notifications_enabled
        }