from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Modular Auth API",
    version="1.0.0"
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "message": "Docker & FastAPI are running smoothly!"
    }