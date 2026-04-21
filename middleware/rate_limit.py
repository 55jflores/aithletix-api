from fastapi import Request
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

from middleware.auth import _PUBLIC_KEY


def get_user_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and _PUBLIC_KEY:
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                _PUBLIC_KEY,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )
            return payload.get("sub", get_remote_address(request))
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip)
