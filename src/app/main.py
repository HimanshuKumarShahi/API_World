from fastapi import FastAPI
from datetime import datetime

app= FastAPI(
    title="Api_world",
    description="An open-source, modular, contract-driven API backend designed for hackathons, prototyping, and production usage. It provides a suite of plug-and-play modules (Auth, Banking, LMS, Store) backed by MongoDB",
    version="1.0.0"
)

@app.get("/health", tags=["System Health"])
async def health_check():
    """
    Check if the API server is running successfully.
    """
    return {
        "status": "ok",
        "service": "api_world",
        "timestamp": datetime.utcnow().isoformat()
    }