import secrets

from pydantic import BaseModel, EmailStr

from core.interfaces.db import UserRepository
from core.interfaces.mail import EmailService
from server.dependencies import get_user_repository, get_email_service
from server.schemas.user_schemas import UserLogin, UserRegister, UserResponse
from server.schemas.token_schemas import Token
from fastapi import APIRouter, HTTPException, status, Depends
from server.core.security import create_access_token, get_password_hash, verify_password
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from datetime import datetime
import os

auth_routes = APIRouter(prefix='/auth')

email_conf = ConnectionConfig(
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp-relay.brevo.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
class EmailRequest(BaseModel):
    email: EmailStr
    
class OTPVerification(BaseModel):
    email: EmailStr
    otp: str

mailer = FastMail(config=email_conf)


otp_storage = {}


def generate_otp(length: int = 6):
    return "".join(str(secrets.randbelow(10)) for _ in range(length))

async def send_email(email : str, email_service : EmailService):
    
    otp_code = generate_otp()
    otp_storage[email] = otp_code
    
    
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
    

    message = MessageSchema(
        subject="Your Account Verification OTP",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )

    await email_service.send_email(subject="Your Account Verification OTP", recipient=email, body=html_content)
    




@auth_routes.post('/register', response_model=UserResponse)
def register_user(user: UserRegister, user_repo : UserRepository = Depends(get_user_repository)):
    user_email = user.email
    db_user = user_repo.get_user(email=user_email)
    
    if db_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    else:
        password = user.password
        hashed_password = get_password_hash(plain_password=password)
        user_name = user.name
        new_user = user_repo.create_user(email=user_email, hashed_password=hashed_password, name=user_name)
        return new_user

@auth_routes.post('/login', response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), user_repo: UserRepository = Depends(get_user_repository)):
    user = user_repo.get_user(email=form_data.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")    

    password = form_data.password
    if not verify_password(plain_password=password, hashed_password=user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
    
@auth_routes.post("/send-email")
async def send_verification_email(email_req: EmailRequest, email_service : EmailService = Depends(get_email_service)):
    email = email_req.email
    
    try:
        await send_email(email=email, email_service=email_service)
        return {"message": "OTP sent successfully. Please check your email."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send email.")


@auth_routes.post("/verify-otp")
async def verify_otp(data: OTPVerification):
    # 1. Check if OTP was generated for this email
    record = otp_storage.get(data.email)
    
    if not record:
        raise HTTPException(status_code=400, detail="OTP not found or expired.")
        
    # 2. Check expiration
    if datetime.utcnow() > record["expires_at"]:
        del otp_storage[data.email] # Clean up
        raise HTTPException(status_code=400, detail="OTP has expired.")
        
    # 3. Validate OTP match
    if record["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
        
    # 4. Success! Clear the OTP from storage
    del otp_storage[data.email]
    
    # --- Integration with your existing Auth ---
    # Here is where you would:
    # 1. Save the user to your database as "is_active=True"
    # 2. Generate your JWT token
    # jwt_token = create_access_token(data={"sub": data.email})
    
    return {
        "message": "Email verified successfully!",
        "token": "your_generated_jwt_token_here" 
    }