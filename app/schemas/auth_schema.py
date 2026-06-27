from pydantic import BaseModel, EmailStr


# Login Schema
class LoginSchema(BaseModel):
    email: EmailStr
    password: str


# Login Response
class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Refresh Token Request
class RefreshTokenSchema(BaseModel):
    refresh_token: str


# Refresh Token Response
class RefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Forgot Password Request
class ForgotPasswordSchema(BaseModel):
    email: EmailStr


# Verify OTP Request
class VerifyOtpSchema(BaseModel):
    email: EmailStr
    otp: str


# Reset Password Request
class ResetPasswordSchema(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str