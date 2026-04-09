from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DevTokenRequest(BaseModel):
    secret: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    display_name: str
    email: str


class RefreshResponse(BaseModel):
    token: str
