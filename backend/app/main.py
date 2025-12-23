"""
RevokeMe API
Token approval scanner and risk assessment
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import scan, validate

app = FastAPI(
    title="RevokeMe API",
    description="""
    A read-only security analysis tool that scans wallet token approvals.
    
    ## Features
    - Scan ERC20, ERC721, and ERC1155 approvals
    - Reconstruct live permission state from blockchain logs
    - Calculate risk scores for each approval
    - Generate actionable revocation links
    
    ## Trust Model
    - No wallet connection required
    - No transaction signing
    - Read-only blockchain queries
    - All data from on-chain sources
    """,
    version="0.1.0"
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://revokeme.vercel.app",  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(validate.router, prefix="/api", tags=["validation"])
app.include_router(scan.router, prefix="/api", tags=["scan"])


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "RevokeMe API",
        "version": "0.1.0",
        "description": "Read-only wallet approval scanner",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
