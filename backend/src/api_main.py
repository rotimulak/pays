"""FastAPI entry point for webhook server."""

import logging
import sys

import uvicorn

from src.api import create_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

app = create_api()


if __name__ == "__main__":
    uvicorn.run(
        "src.api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
