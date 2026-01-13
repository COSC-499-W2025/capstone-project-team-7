# main.py
# Entry point for the backend service.
# - Initializes FastAPI app
# - Registers API routes (projects, skills, privacy, etc.)
# - Provides root health-check endpoint
# - Run with: uvicorn src.main:app --reload
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api.consent_routes import router as consent_router
from api.llm_routes import router as llm_router
from api.portfolio_routes import router as portfolio_router
from api.spec_routes import router as spec_router
from api.project_routes import router as project_router
from api.upload_routes import router as upload_router

app = FastAPI(
    title="Capstone Backend API",
    description="Backend service",
    version="1.0.0"
)

allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")

def root():
    return {"status":"healthy", "message":"Backend API is running"}

@app.get("/health")
def health_check():
        return {"status":"ok"}


# Register API routes
app.include_router(consent_router)
app.include_router(llm_router)
app.include_router(portfolio_router)
app.include_router(spec_router)
app.include_router(project_router)
app.include_router(upload_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
