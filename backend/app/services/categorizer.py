"""
Categorizer Service.
Categorizes approvals and generates actionable output.
"""
from dataclasses import dataclass
from typing import Optional

from app.services.approval_scanner import ActiveApproval
from app.services.risk_engine import RiskEngine, RiskAssessment, RiskCategory


@dataclass
class CategorizedApproval:
    """An approval with risk assessment and action links."""
    approval: ActiveApproval
    risk: RiskAssessment
    revoke_url: str
    etherscan_url: str

    def to_dict(self) -> dict:
        approval_dict = self.approval.to_dict()
        risk_dict = self.risk.to_dict()
        
        return {
            **approval_dict,
            "risk_score": risk_dict["score"],
            "category": risk_dict["category"],
            "risk_reasons": risk_dict["reasons"],
            "revoke_url": self.revoke_url,
            "etherscan_url": self.etherscan_url
        }


@dataclass
class ScanSummary:
    """Summary of scan results."""
    total_approvals: int
    dangerous_count: int
    risky_count: int
    safe_count: int
    hygiene_score: int
    hygiene_label: str


@dataclass 
class ScanResult:
    """Complete scan result with categorized approvals."""
    wallet: str
    chain_id: int
    summary: ScanSummary
    dangerous: list[CategorizedApproval]
    risky: list[CategorizedApproval]
    safe: list[CategorizedApproval]

    def to_dict(self) -> dict:
        return {
            "wallet": self.wallet,
            "chain_id": self.chain_id,
            "hygiene_score": self.summary.hygiene_score,
            "hygiene_label": self.summary.hygiene_label,
            "summary": {
                "total_approvals": self.summary.total_approvals,
                "dangerous": self.summary.dangerous_count,
                "risky": self.summary.risky_count,
                "safe": self.summary.safe_count
            },
            "approvals": {
                "dangerous": [a.to_dict() for a in self.dangerous],
                "risky": [a.to_dict() for a in self.risky],
                "safe": [a.to_dict() for a in self.safe]
            }
        }


class Categorizer:
    """Service for categorizing approvals and generating results."""

    # Chain configurations
    CHAINS = {
        1: {
            "name": "Ethereum",
            "explorer": "https://etherscan.io",
            "revoke_base": "https://revoke.cash/address"
        },
        137: {
            "name": "Polygon",
            "explorer": "https://polygonscan.com",
            "revoke_base": "https://revoke.cash/address"
        },
        42161: {
            "name": "Arbitrum",
            "explorer": "https://arbiscan.io",
            "revoke_base": "https://revoke.cash/address"
        },
        10: {
            "name": "Optimism",
            "explorer": "https://optimistic.etherscan.io",
            "revoke_base": "https://revoke.cash/address"
        },
        8453: {
            "name": "Base",
            "explorer": "https://basescan.org",
            "revoke_base": "https://revoke.cash/address"
        }
    }

    def __init__(self):
        self.risk_engine = RiskEngine()

    def categorize(
        self, 
        wallet: str,
        approvals: list[ActiveApproval],
        chain_id: int = 1
    ) -> ScanResult:
        """
        Categorize approvals and generate complete scan result.
        
        Args:
            wallet: The wallet address that was scanned
            approvals: List of active approvals
            chain_id: The chain ID
            
        Returns:
            ScanResult with categorized approvals and summary
        """
        chain_config = self.CHAINS.get(chain_id, self.CHAINS[1])
        
        dangerous = []
        risky = []
        safe = []
        all_assessments = []

        for approval in approvals:
            # Calculate risk
            assessment = self.risk_engine.calculate_risk(approval)
            all_assessments.append(assessment)
            
            # Generate URLs
            revoke_url = self._generate_revoke_url(
                wallet, 
                approval.token.address,
                chain_id,
                chain_config
            )
            etherscan_url = self._generate_etherscan_url(
                approval.spender.address,
                chain_config
            )
            
            categorized = CategorizedApproval(
                approval=approval,
                risk=assessment,
                revoke_url=revoke_url,
                etherscan_url=etherscan_url
            )
            
            # Sort into buckets
            if assessment.category == RiskCategory.DANGEROUS:
                dangerous.append(categorized)
            elif assessment.category == RiskCategory.RISKY:
                risky.append(categorized)
            else:
                safe.append(categorized)

        # Sort each category by risk score (highest first)
        dangerous.sort(key=lambda x: x.risk.score, reverse=True)
        risky.sort(key=lambda x: x.risk.score, reverse=True)
        safe.sort(key=lambda x: x.risk.score, reverse=True)

        # Calculate hygiene score
        hygiene_score = self.risk_engine.calculate_hygiene_score(all_assessments)
        hygiene_label = self.risk_engine.get_hygiene_label(hygiene_score)

        summary = ScanSummary(
            total_approvals=len(approvals),
            dangerous_count=len(dangerous),
            risky_count=len(risky),
            safe_count=len(safe),
            hygiene_score=hygiene_score,
            hygiene_label=hygiene_label
        )

        return ScanResult(
            wallet=wallet,
            chain_id=chain_id,
            summary=summary,
            dangerous=dangerous,
            risky=risky,
            safe=safe
        )

    def _generate_revoke_url(
        self, 
        wallet: str, 
        token: str,
        chain_id: int,
        config: dict
    ) -> str:
        """Generate revoke.cash URL for the approval."""
        base = config["revoke_base"]
        # revoke.cash format: /address/{wallet}?chainId={chainId}
        return f"{base}/{wallet}?chainId={chain_id}"

    def _generate_etherscan_url(self, address: str, config: dict) -> str:
        """Generate block explorer URL for the spender."""
        return f"{config['explorer']}/address/{address}"

    def generate_share_text(self, result: ScanResult) -> str:
        """Generate shareable text for social media."""
        dangerous = result.summary.dangerous_count
        risky = result.summary.risky_count
        score = result.summary.hygiene_score
        
        if dangerous > 0:
            return f"🚨 My wallet has {dangerous} dangerous approval(s)! Hygiene score: {score}/100. Check yours at RevokeMe"
        elif risky > 0:
            return f"⚠️ Found {risky} risky approval(s) in my wallet. Score: {score}/100. Scan yours at RevokeMe"
        else:
            return f"✅ My wallet is clean! Hygiene score: {score}/100. Check yours at RevokeMe"

    def generate_share_card_data(self, result: ScanResult) -> dict:
        """Generate data for shareable summary card."""
        return {
            "hygiene_score": result.summary.hygiene_score,
            "hygiene_label": result.summary.hygiene_label,
            "total_approvals": result.summary.total_approvals,
            "dangerous_count": result.summary.dangerous_count,
            "risky_count": result.summary.risky_count,
            "safe_count": result.summary.safe_count,
            "share_text": self.generate_share_text(result),
            "wallet_short": f"{result.wallet[:6]}...{result.wallet[-4:]}"
        }
