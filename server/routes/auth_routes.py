import secrets


from core.interfaces.auth import AuthService
from core.interfaces.mail import EmailService
from core.interfaces.otp_store import OTPStore
from server.dependencies import get_email_service, get_otp_store, get_authentication_service
from server.schemas.user_schemas import UserRegister, UserResponse, EmailRequest, OTPVerification, OTPPurpose, ResetPasswordRequest
from server.schemas.token_schemas import Token
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

auth_routes = APIRouter(prefix='/auth')

def generate_otp(length: int = 6):
    return "".join(str(secrets.randbelow(10)) for _ in range(length))

async def send_email(email : str, otp_code: str, email_service : EmailService):
    
    html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verification Code &mdash; QuickPaperAI</title>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f3f1eb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; width: 100% !important;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f3f1eb; padding: 40px 10px;">
                <tr>
                <td align="center">
                    <!-- Main Email Container -->
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 540px; background-color: #faf8f5; border: 1px solid #e2ded5; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); overflow: hidden;">
                    
                    <!-- Vermillion Top Accent Line -->
                    <tr>
                        <td height="4" style="background-color: #d34e36; line-height: 4px; font-size: 4px;">&nbsp;</td>
                    </tr>
                    
                    <!-- Header (Brand Name & Monospace Stamp Label) -->
                    <tr>
                        <td style="padding: 35px 40px 20px 40px; border-bottom: 1px dashed #e2ded5;">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                            <tr>
                            <td>
                                <span style="font-family: Georgia, serif; font-size: 22px; font-style: italic; font-weight: bold; color: #161b22; letter-spacing: -0.5px;">QuickPaperAI</span>
                            </td>
                            <td align="right">
                                <span style="font-family: 'Courier New', Courier, monospace; font-size: 10px; font-weight: bold; text-transform: uppercase; color: #d34e36; letter-spacing: 2px; border: 1px solid #d34e36; padding: 2px 6px; border-radius: 2px;">OTP PASS</span>
                            </td>
                            </tr>
                        </table>
                        </td>
                    </tr>
                    
                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                        <p style="margin: 0 0 10px 0; font-family: 'Courier New', Courier, monospace; font-size: 11px; font-weight: bold; text-transform: uppercase; color: #737880; letter-spacing: 3px;">
                            01 &mdash; Security Verification
                        </p>
                        <h1 style="margin: 0 0 20px 0; font-family: Georgia, serif; font-size: 28px; font-weight: normal; line-height: 1.2; color: #161b22;">
                            Confirm your identity
                        </h1>
                        <p style="margin: 0 0 30px 0; font-size: 15px; line-height: 1.6; color: #4a4d52;">
                            A sign-in attempt was initiated for your QuickPaperAI account. Use the verification code below to authorize access to your Examiner's Desk.
                        </p>
                        
                        <!-- OTP Box Section -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fcfbfa; border: 1px solid #e8e5dc; border-radius: 3px; margin: 30px 0;">
                            <tr>
                            <td align="center" style="padding: 25px 20px;">
                                <div style="font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: bold; letter-spacing: 8px; color: #161b22; line-height: 1.1;">
                                {otp_code}
                                </div>
                                <div style="margin-top: 10px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 11px; color: #d34e36; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 500;">
                                Code expires in 10 minutes
                                </div>
                            </td>
                            </tr>
                        </table>
                        
                        <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #737880;">
                            If you did not make this request, please ignore this email or contact support if you suspect unauthorized activity.
                        </p>
                        </td>
                    </tr>
                    
                    <!-- Footer Details -->
                    <tr>
                        <td style="padding: 25px 40px 35px 40px; background-color: #f7f5ef; border-top: 1px solid #e2ded5;">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                            <tr>
                            <td style="font-family: 'Courier New', Courier, monospace; font-size: 10px; color: #737880; line-height: 1.6; text-transform: uppercase; letter-spacing: 1.5px;">
                                QuickPaperAI Desk System<br>
                                Syllabus Presets &bull; AI Grading<br>
                                <span style="color: #a0a4a8;">Protected under secure key session</span>
                            </td>
                            <td align="right" valign="bottom" style="font-family: 'Courier New', Courier, monospace; font-size: 10px; color: #a0a4a8; text-transform: uppercase; letter-spacing: 1.5px;">
                                &copy; 2026
                            </td>
                            </tr>
                        </table>
                        </td>
                    </tr>
                    </table>
                </td>
                </tr>
            </table>
            </body>
        </html>

    """
    

    await email_service.send_email(subject="Your Account Verification OTP", recipient=email, body=html_content)
    

@auth_routes.post('/register', response_model=UserResponse)
async def register_user(user: UserRegister, auth_service: AuthService = Depends(get_authentication_service)):
    user_email = user.email
    user_name = user.name
    password = user.password

    new_user = await auth_service.register_user(email=user_email, password=password, name=user_name)

    return new_user

@auth_routes.post('/login', response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), auth_service : AuthService = Depends(get_authentication_service)):
    email = form_data.username

    password = form_data.password

    token = await auth_service.authenticate_user(email=email, password=password)

    return token
    
@auth_routes.post("/send-email")
async def send_verification_email(email_req: EmailRequest, email_service : EmailService = Depends(get_email_service), otp_store : OTPStore = Depends(get_otp_store), auth_service: AuthService = Depends(get_authentication_service)):
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

    if await otp_store.set_send_cooldown(email=email):
        raise HTTPException(
            status_code=429,
            detail="Please wait 60 seconds before request another code"
        )

    try:
        otp_code = generate_otp()
        await otp_store.save_otp(email=email, otp_code=otp_code)
        await send_email(email=email, otp_code=otp_code, email_service=email_service)
        return {"message": "OTP sent successfully. Please check your email."}
    except Exception as e:
        await otp_store.delete_otp(email=email)
        raise HTTPException(status_code=500, detail="Failed to send email.")


@auth_routes.post("/verify-otp")
async def verify_otp(
    data: OTPVerification, 
    otp_store : OTPStore = Depends(get_otp_store),
    auth_service: AuthService = Depends(get_authentication_service)
):
    # 1. Check if OTP was generated for this email
    email = data.email.lower().strip()
    purpose = data.purpose

    if await otp_store.is_locked_out(email=email):
            raise HTTPException(
                status_code=403,
                detail="Too many failed verification, Please try again after 15 minutes."
            )

    stored_otp = await otp_store.get_otp(email=email)
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP not found or expired. Please request a new code.")
        
    # 2. Check expiration
        
    # 3. Validate OTP match
    if stored_otp != data.otp:
        is_now_locked = await otp_store.increment_failed_attempts(email=email)
        if is_now_locked:
            raise HTTPException(
                status_code=403,
                detail="Too many verification attempts. Your verification code is locked for 15 minutes."
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid OTP.")

    # 4. Success! Clear the OTP from storage
    await otp_store.delete_otp(email=email)

    if purpose == OTPPurpose.SIGNUP:
        await auth_service.activate_user(email=email)
        token_data = auth_service.create_token_for_email(email=email)
        return {
            "message": "Email verified successfully!",
            "access_token": token_data["access_token"],
            "token_type": token_data["token_type"]
        }
    elif purpose == OTPPurpose.RESET_PASSWORD:
        reset_token = auth_service.create_token_for_email(email=email)
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
    # 1. Verify reset token
    try:
        user = await auth_service.verify_session(data.token)
    except HTTPException as e:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    
    # 2. Check email match
    if user.get("email").lower().strip() != data.email.lower().strip():
        raise HTTPException(status_code=400, detail="Invalid reset request parameters.")

    # 3. Perform password reset
    await auth_service.update_password(email=data.email.lower().strip(), new_password=data.new_password)
    return {"message": "Password reset successfully."}

