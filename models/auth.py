from pydantic import BaseModel, EmailStr

class DevTokenRequest(BaseModel):
    secret: str

class AuthResponse(BaseModel):
    token: str
    user_id: str
    display_name: str
    email: str
