import os

from fastapi import Request
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                os.environ.get("JWT_SECRET", ""),
                algorithms=["HS256"],
            )
            return payload.get("sub", get_remote_address(request))
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip)
