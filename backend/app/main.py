import uvicorn
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


configure_logging()

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}. Go to /api/news to see the live stream."}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
