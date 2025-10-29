# main.py
# Entry point for the backend service.
# - Initializes FastAPI app
# - Registers API routes (projects, skills, privacy, etc.)
# - Provides root health-check endpoint
# - Run with: uvicorn src.main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api.llm_routes import router as llm_router

app = FastAPI(
    title="Capstone Backend API",
    description="Backend service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
     allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")

def root():
    return {"status":"healthy", "message":"Backend API is running"}

@app.get("/health")
def health_check():
        return {"status":"ok"}


# Register API routes
app.include_router(llm_router)

if __name__ == "__main__":
    from src.cli.app import main as cli_main

    sys.exit(cli_main())
