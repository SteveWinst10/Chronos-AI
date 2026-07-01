# main.py
import uvicorn
from fastapi import FastAPI
from api.router import api_router

# Initialize the FastAPI app
app = FastAPI(title="News AI Backend")

# Connect your routers
app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "Welcome to Person 2's Backend API. Go to /api/news to see the live stream."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)