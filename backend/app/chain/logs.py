class LogParser:
    """Parser for blockchain event logs."""

    def parse_approval_logs(self, logs: list) -> list:
        """
        Parse raw approval logs into structured approval objects.
        
        Args:
            logs: List of raw log entries from RPC
            
        Returns:
            List of parsed approval objects
        """
        approvals = []
        
        for log in logs:
            approval = self._parse_single_log(log)
            if approval:
                approvals.append(approval)
        
        return approvals

    def _parse_single_log(self, log: dict) -> dict | None:
        """Parse a single approval log entry."""
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None

            # Parse owner and spender from topics
            owner = "0x" + topics[1][26:]
            spender = "0x" + topics[2][26:]
            
            # Parse amount from data
            data = log.get("data", "0x0")
            amount = int(data, 16)
            
            # Check for unlimited approval (max uint256)
            max_uint256 = 2**256 - 1
            amount_str = "unlimited" if amount == max_uint256 else str(amount)

            return {
                "token": log.get("address"),
                "owner": owner,
                "spender": spender,
                "amount": amount_str,
                "block_number": int(log.get("blockNumber", "0x0"), 16),
                "tx_hash": log.get("transactionHash"),
            }
        except Exception:
            return None
