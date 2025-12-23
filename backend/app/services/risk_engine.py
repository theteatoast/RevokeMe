"""
Risk Engine Service.
Calculates risk scores for token approvals based on multiple factors.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.approval_scanner import ActiveApproval
from app.chain.logs import ApprovalType


class RiskCategory(str, Enum):
    SAFE = "safe"
    RISKY = "risky"  
    DANGEROUS = "dangerous"


@dataclass
class RiskFactor:
    """A single risk factor with its contribution to the score."""
    name: str
    weight: int
    reason: str
    applies: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "weight": self.weight,
            "reason": self.reason
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for an approval."""
    score: int  # 0-100
    category: RiskCategory
    factors: list[RiskFactor]
    reasons: list[str]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "category": self.category.value,
            "reasons": self.reasons,
            "factors": [f.to_dict() for f in self.factors if f.applies]
        }


class RiskEngine:
    """Service for calculating risk scores for token approvals."""

    # Risk factor weights (must sum to max 100 when all apply)
    WEIGHTS = {
        "unlimited_allowance": 40,
        "eoa_spender": 35,
        "unknown_spender": 20,
        "approval_for_all": 25,
        "old_approval_6m": 15,
        "old_approval_1y": 20,
        "very_old_approval": 25,
    }

    # Category thresholds
    SAFE_THRESHOLD = 30
    RISKY_THRESHOLD = 60

    def calculate_risk(self, approval: ActiveApproval) -> RiskAssessment:
        """
        Calculate risk score for a single approval.
        
        Args:
            approval: The active approval to assess
            
        Returns:
            RiskAssessment with score, category, and contributing factors
        """
        factors = []
        total_score = 0

        # Factor 1: Unlimited allowance
        if approval.is_unlimited:
            if approval.approval_type == ApprovalType.ERC20:
                factor = RiskFactor(
                    name="unlimited_allowance",
                    weight=self.WEIGHTS["unlimited_allowance"],
                    reason="Unlimited token approval allows spender to transfer any amount",
                    applies=True
                )
            else:
                factor = RiskFactor(
                    name="approval_for_all",
                    weight=self.WEIGHTS["approval_for_all"],
                    reason="Blanket NFT approval allows spender to transfer all tokens in collection",
                    applies=True
                )
            factors.append(factor)
            total_score += factor.weight

        # Factor 2: EOA as spender (very dangerous)
        if not approval.spender.is_contract:
            factor = RiskFactor(
                name="eoa_spender",
                weight=self.WEIGHTS["eoa_spender"],
                reason="Spender is an externally owned account (EOA), not a contract",
                applies=True
            )
            factors.append(factor)
            total_score += factor.weight

        # Factor 3: Unknown/unverified spender
        if not approval.spender.verified and approval.spender.is_contract:
            factor = RiskFactor(
                name="unknown_spender",
                weight=self.WEIGHTS["unknown_spender"],
                reason="Spender contract is not verified on block explorer",
                applies=True
            )
            factors.append(factor)
            total_score += factor.weight

        # Factor 4: Age of approval
        if approval.age_days > 365:
            factor = RiskFactor(
                name="very_old_approval",
                weight=self.WEIGHTS["very_old_approval"],
                reason=f"Approval is over {approval.age_days // 365} year(s) old",
                applies=True
            )
            factors.append(factor)
            total_score += factor.weight
        elif approval.age_days > 180:
            factor = RiskFactor(
                name="old_approval_6m",
                weight=self.WEIGHTS["old_approval_6m"],
                reason=f"Approval is {approval.age_days} days old (6+ months)",
                applies=True
            )
            factors.append(factor)
            total_score += factor.weight

        # Cap score at 100
        total_score = min(total_score, 100)

        # Determine category
        if total_score <= self.SAFE_THRESHOLD:
            category = RiskCategory.SAFE
        elif total_score <= self.RISKY_THRESHOLD:
            category = RiskCategory.RISKY
        else:
            category = RiskCategory.DANGEROUS

        # Extract reason strings
        reasons = [f.reason for f in factors if f.applies]

        return RiskAssessment(
            score=total_score,
            category=category,
            factors=factors,
            reasons=reasons
        )

    def calculate_hygiene_score(self, assessments: list[RiskAssessment]) -> int:
        """
        Calculate overall wallet hygiene score (0-100, higher is better).
        
        Args:
            assessments: List of risk assessments for all approvals
            
        Returns:
            Hygiene score where 100 = perfect, 0 = very risky
        """
        if not assessments:
            return 100  # No approvals = perfect hygiene

        # Weight by category severity
        danger_count = sum(1 for a in assessments if a.category == RiskCategory.DANGEROUS)
        risky_count = sum(1 for a in assessments if a.category == RiskCategory.RISKY)
        safe_count = sum(1 for a in assessments if a.category == RiskCategory.SAFE)
        
        total = len(assessments)
        
        # Dangerous approvals have heavy penalty
        # Risky approvals have moderate penalty
        # Safe approvals have minor penalty (any approval is some risk)
        penalty = (
            danger_count * 25 +  # Each dangerous = -25
            risky_count * 10 +   # Each risky = -10
            safe_count * 2       # Each safe = -2
        )
        
        hygiene = max(0, 100 - penalty)
        return hygiene

    def get_hygiene_label(self, score: int) -> str:
        """Get human-readable label for hygiene score."""
        if score >= 90:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 30:
            return "Poor"
        else:
            return "Critical"
