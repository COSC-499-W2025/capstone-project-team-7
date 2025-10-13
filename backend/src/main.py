# main.py
# Entry point for the backend service.
# - Initializes FastAPI app
# - Registers API routes (projects, skills, privacy, etc.)
# - Provides root health-check endpoint
# - Run with: uvicorn src.main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


# TODO: Register API routes here
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)