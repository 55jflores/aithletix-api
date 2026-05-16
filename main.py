from dotenv import load_dotenv
load_dotenv()

import os
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from middleware.rate_limit import limiter
from routers import health, coaching, baseurl, auth, healthkit_insight, nutrition, privacy, pr_insight


app = FastAPI(
    title="Aithletix API",
    description="Biomechanics coaching powered by Claude",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'self'" 
        response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health.router)
app.include_router(baseurl.router)
app.include_router(auth.router)
app.include_router(coaching.router, prefix="/coaching")
app.include_router(healthkit_insight.router, prefix="/healthkit")
app.include_router(nutrition.router, prefix="/nutrition")
app.include_router(pr_insight.router, prefix="/training")
app.include_router(privacy.router)
