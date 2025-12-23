"""
Scan API.
Main endpoint for scanning wallet approvals.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.approval_scanner import ApprovalScanner
from app.services.categorizer import Categorizer
from app.api.validate import is_valid_ethereum_address, to_checksum_address


router = APIRouter()


class ScanRequest(BaseModel):
    address: str
    chain_id: int = 1


class ScanResponse(BaseModel):
    wallet: str
    chain_id: int
    hygiene_score: int
    hygiene_label: str
    summary: dict
    approvals: dict


@router.post("/scan", response_model=ScanResponse)
async def scan_approvals(request: ScanRequest):
    """
    Scan a wallet for token approvals and assess risk.
    
    This endpoint:
    1. Validates the address
    2. Fetches all approval events from the blockchain
    3. Reconstructs current approval state
    4. Calculates risk scores for each approval
    5. Returns categorized results with action links
    
    No wallet connection required. Read-only scan.
    """
    # Validate address
    if not is_valid_ethereum_address(request.address):
        raise HTTPException(
            status_code=400, 
            detail="Invalid Ethereum address format"
        )
    
    # Validate chain
    if request.chain_id != 1:
        raise HTTPException(
            status_code=400,
            detail="Only Ethereum Mainnet (chain_id: 1) is supported"
        )
    
    try:
        # Normalize address
        address = request.address.lower()
        
        # Scan for approvals
        scanner = ApprovalScanner()
        approvals = await scanner.scan(address, request.chain_id)
        
        # Categorize and calculate risk
        categorizer = Categorizer()
        result = categorizer.categorize(address, approvals, request.chain_id)
        
        return ScanResponse(**result.to_dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )


class ShareCardRequest(BaseModel):
    address: str
    chain_id: int = 1


class ShareCardResponse(BaseModel):
    hygiene_score: int
    hygiene_label: str
    total_approvals: int
    dangerous_count: int
    risky_count: int
    safe_count: int
    share_text: str
    wallet_short: str


@router.post("/share-card", response_model=ShareCardResponse)
async def get_share_card(request: ShareCardRequest):
    """
    Get shareable summary card data for a wallet.
    Runs a quick scan and returns data optimized for sharing.
    """
    # Validate address
    if not is_valid_ethereum_address(request.address):
        raise HTTPException(
            status_code=400,
            detail="Invalid Ethereum address format"
        )
    
    try:
        address = request.address.lower()
        
        # Scan
        scanner = ApprovalScanner()
        approvals = await scanner.scan(address, request.chain_id)
        
        # Categorize
        categorizer = Categorizer()
        result = categorizer.categorize(address, approvals, request.chain_id)
        
        # Generate share card data
        card_data = categorizer.generate_share_card_data(result)
        
        return ShareCardResponse(**card_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate share card: {str(e)}"
        )
