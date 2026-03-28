# main.py
# Entry point for the backend service.
# - Initializes FastAPI app
# - Registers API routes (projects, skills, privacy, etc.)
# - Provides root health-check endpoint
# - Run with: uvicorn src.main:app --reload
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

sys.path.insert(0, str(Path(__file__).parent))
if load_dotenv:
    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    load_dotenv(backend_root / ".env", override=False)
    load_dotenv(project_root / ".env", override=False)
from api.auth_routes import router as auth_router
from api.analysis_routes import router as analysis_router
from api.consent_routes import router as consent_router
from api.llm_routes import router as llm_router
from api.portfolio_routes import router as portfolio_router
from api.resume_routes import router as resume_router
from api.user_resume_routes import router as user_resume_router
from api.spec_routes import router as spec_router
from api.project_routes import router as project_router
from api.upload_routes import router as upload_router
from api.selection_routes import router as selection_router
from api.profile_routes import router as profile_router
from api.encryption_routes import router as encryption_router
from api.settings_routes import router as settings_router
from api.portfolio_settings_routes import router as portfolio_settings_router
from security.rate_limit import limiter

app = FastAPI(
    title="Capstone Backend API",
    description="Backend service",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

allowed_hosts = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]
if not allowed_hosts:
    allowed_hosts = ["localhost", "127.0.0.1", "testserver"]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.get("/")

def root():
    return {"status":"healthy", "message":"Backend API is running"}

@app.get("/health")
def health_check():
        return {"status":"ok"}


# Register API routes
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(consent_router)
app.include_router(llm_router)
app.include_router(portfolio_router)
app.include_router(resume_router)
app.include_router(user_resume_router)
app.include_router(spec_router)
app.include_router(project_router)
app.include_router(upload_router)
app.include_router(selection_router)
app.include_router(profile_router)
app.include_router(encryption_router)
app.include_router(settings_router)
app.include_router(portfolio_settings_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        app_dir=str(Path(__file__).parent),
    )
