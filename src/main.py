"""
Dashboard Cast Service
Main entry point - runs the FastAPI webhook API
"""

import uvicorn
from src.api.main import app

if __name__ == "__main__":
    # Run uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
