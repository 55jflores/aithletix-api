import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext

from middleware.auth import verify_token
from models.auth import AuthResponse, DevTokenRequest

router = APIRouter(prefix="/auth", tags=["auth"])

def _load_jwt_secret():
    raw = os.environ["SUPABASE_JWT_PUBLIC_KEY"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw

JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "ES256"
JWT_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# NOTE: Phase 4 placeholder only.
# This dict resets every time Railway redeploys.
# Supabase replaces this in Phase 4 Step 5 with persistent storage.
# Do not use this in production.
users_db: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str, email: str, display_name: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "display_name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)




@router.post("/dev-token", response_model=AuthResponse)
def dev_token(request: DevTokenRequest):
    expected = os.environ.get("DEV_TOKEN_SECRET", "")

    if not expected or request.secret != expected:
        raise HTTPException(status_code=403, detail="Invalid dev secret")

    token = create_token(
        user_id="dev-user-001",
        email="dev@athleteiq.app",
        display_name="Dev Athlete",
    )

    return AuthResponse(
        token=token,
        user_id="dev-user-001",
        display_name="Dev Athlete",
        email="dev@athleteiq.app",
    )
