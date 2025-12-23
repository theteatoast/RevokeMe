class RiskEngine:
    """Service for calculating risk scores for token approvals."""

    def __init__(self):
        self.risk_factors = {
            "unlimited_approval": 0.4,
            "unknown_spender": 0.3,
            "old_approval": 0.2,
            "high_value_token": 0.1,
        }

    def calculate_risk(self, approvals: list) -> float:
        """
        Calculate overall risk score for a set of approvals.
        
        Args:
            approvals: List of approval objects
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        if not approvals:
            return 0.0

        # TODO: Implement risk calculation logic
        total_risk = 0.0
        for approval in approvals:
            total_risk += self._calculate_single_risk(approval)
        
        return min(total_risk / len(approvals), 1.0)

    def _calculate_single_risk(self, approval: dict) -> float:
        """Calculate risk score for a single approval."""
        risk = 0.0
        
        # Check for unlimited approval
        if approval.get("amount") == "unlimited":
            risk += self.risk_factors["unlimited_approval"]
        
        # TODO: Add more risk factors
        return risk
