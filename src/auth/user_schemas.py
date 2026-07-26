from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict
from enum import Enum


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OTPVerification(BaseModel):
    email: EmailStr
    otp: str


class OTPPurpose(str, Enum):
    SIGNUP = "signup"
    RESET_PASSWORD = "reset_password"


class EmailRequest(BaseModel):
    email: EmailStr
    purpose: OTPPurpose


class OTPVerification(BaseModel):
    email: EmailStr
    otp: str
    purpose: OTPPurpose


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str


    