from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.approval_scanner import ApprovalScanner
from app.services.risk_engine import RiskEngine

router = APIRouter()


class ScanRequest(BaseModel):
    address: str
    chain_id: int = 1


class ScanResponse(BaseModel):
    address: str
    approvals: list
    risk_score: float


@router.post("/scan", response_model=ScanResponse)
async def scan_approvals(request: ScanRequest):
    """Scan an address for token approvals and assess risk."""
    try:
        scanner = ApprovalScanner()
        approvals = await scanner.scan(request.address, request.chain_id)
        
        risk_engine = RiskEngine()
        risk_score = risk_engine.calculate_risk(approvals)
        
        return ScanResponse(
            address=request.address,
            approvals=approvals,
            risk_score=risk_score
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
