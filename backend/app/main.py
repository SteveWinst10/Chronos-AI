import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    # Optionally add docs URL prefixes if needed
)

# CORS configuration to allow React dev server access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Include API router with versioned prefix (e.g., /api/v1)
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}. Go to /api/v1/health to see the system health."}

# Lifespan events for clean startup/shutdown (example placeholders)
@app.on_event("startup")
async def on_startup():
    # Initialize resources, database connections, etc.
    pass

@app.on_event("shutdown")
async def on_shutdown():
    # Cleanup resources
    pass

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
