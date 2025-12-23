from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import scan

app = FastAPI(
    title="RevokeMe API",
    description="Token approval scanner and risk assessment",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router, prefix="/api", tags=["scan"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
