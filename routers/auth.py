import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext

from middleware.auth import verify_token
from models.auth import AuthResponse, DevTokenRequest, LoginRequest, RegisterRequest

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


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters",
        )

    email = request.email.lower()

    if email in users_db:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(request.password)
    user_id = str(uuid4())

    users_db[email] = {
        "user_id": user_id,
        "email": email,
        "display_name": request.display_name,
        "password_hash": password_hash,
    }

    token = create_token(user_id, email, request.display_name)

    return AuthResponse(
        token=token,
        user_id=user_id,
        display_name=request.display_name,
        email=email,
    )


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    email = request.email.lower()
    user = users_db.get(email)

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["user_id"], user["email"], user["display_name"])

    return AuthResponse(
        token=token,
        user_id=user["user_id"],
        display_name=user["display_name"],
        email=user["email"],
    )


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


@router.post("/refresh", response_model=AuthResponse)
def refresh(user: dict = Depends(verify_token)):
    display_name = user.get("display_name") or user.get("user_metadata", {}).get("display_name", "")

    token = create_token(
        user_id=user["sub"],
        email=user["email"],
        display_name=display_name,
    )

    return AuthResponse(
        token=token,
        user_id=user["sub"],
        display_name=display_name,
        email=user["email"],
    )
