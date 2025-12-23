"""
Log Parser for blockchain event logs.
Parses approval events into structured data.
"""
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ApprovalType(str, Enum):
    ERC20 = "ERC20"
    ERC721 = "ERC721"
    ERC721_ALL = "ERC721_ALL"
    ERC1155_ALL = "ERC1155_ALL"


@dataclass
class ParsedApproval:
    """Parsed approval event data."""
    token_address: str
    owner: str
    spender: str
    approval_type: ApprovalType
    value: Optional[int] = None  # For ERC20 allowance amount
    token_id: Optional[int] = None  # For ERC721 specific token
    approved: bool = True  # For ApprovalForAll (can be set to false)
    block_number: int = 0
    tx_hash: Optional[str] = None
    log_index: int = 0

    @property
    def is_unlimited(self) -> bool:
        """Check if this is an unlimited approval."""
        if self.approval_type == ApprovalType.ERC20:
            # Max uint256 or very large values
            MAX_UINT256 = 2**256 - 1
            return self.value is not None and self.value >= MAX_UINT256 * 0.9
        elif self.approval_type in [ApprovalType.ERC721_ALL, ApprovalType.ERC1155_ALL]:
            return self.approved
        return False

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "owner": self.owner,
            "spender": self.spender,
            "approval_type": self.approval_type.value,
            "value": str(self.value) if self.value is not None else None,
            "token_id": self.token_id,
            "approved": self.approved,
            "block_number": self.block_number,
            "tx_hash": self.tx_hash,
            "is_unlimited": self.is_unlimited
        }


class LogParser:
    """Parser for blockchain event logs."""

    @staticmethod
    def unpad_address(padded: str) -> str:
        """Extract address from 32-byte padded topic."""
        if not padded or len(padded) < 42:
            return ""
        return "0x" + padded[26:].lower()

    def parse_approval_logs(self, logs: dict) -> list[ParsedApproval]:
        """
        Parse raw approval logs into structured approval objects.
        
        Args:
            logs: Dict with 'approvals' and 'approval_for_all' lists
            
        Returns:
            List of ParsedApproval objects
        """
        approvals = []
        
        # Parse ERC20/ERC721 Approval events
        for log in logs.get("approvals", []):
            parsed = self._parse_approval_event(log)
            if parsed:
                approvals.append(parsed)
        
        # Parse ApprovalForAll events
        for log in logs.get("approval_for_all", []):
            parsed = self._parse_approval_for_all_event(log)
            if parsed:
                approvals.append(parsed)
        
        return approvals

    def _parse_approval_event(self, log: dict) -> Optional[ParsedApproval]:
        """Parse ERC20/ERC721 Approval event."""
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None

            token_address = log.get("address", "").lower()
            owner = self.unpad_address(topics[1])
            spender = self.unpad_address(topics[2])
            
            data = log.get("data", "0x")
            block_number = int(log.get("blockNumber", "0x0"), 16)
            tx_hash = log.get("transactionHash")
            log_index = int(log.get("logIndex", "0x0"), 16)

            # Determine if ERC20 or ERC721 based on data
            # ERC20: data contains value (uint256)
            # ERC721: topics[3] contains tokenId OR data is empty/has tokenId
            
            if len(topics) == 4:
                # ERC721 with indexed tokenId
                token_id = int(topics[3], 16)
                return ParsedApproval(
                    token_address=token_address,
                    owner=owner,
                    spender=spender,
                    approval_type=ApprovalType.ERC721,
                    token_id=token_id,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    log_index=log_index
                )
            else:
                # ERC20 with value in data
                value = 0
                if data and data != "0x" and len(data) >= 66:
                    value = int(data, 16)
                
                return ParsedApproval(
                    token_address=token_address,
                    owner=owner,
                    spender=spender,
                    approval_type=ApprovalType.ERC20,
                    value=value,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    log_index=log_index
                )

        except Exception as e:
            print(f"Error parsing approval log: {e}")
            return None

    def _parse_approval_for_all_event(self, log: dict) -> Optional[ParsedApproval]:
        """Parse ApprovalForAll event (ERC721/ERC1155)."""
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None

            token_address = log.get("address", "").lower()
            owner = self.unpad_address(topics[1])
            operator = self.unpad_address(topics[2])
            
            data = log.get("data", "0x")
            block_number = int(log.get("blockNumber", "0x0"), 16)
            tx_hash = log.get("transactionHash")
            log_index = int(log.get("logIndex", "0x0"), 16)

            # Data contains boolean (approved)
            approved = True
            if data and data != "0x":
                approved = int(data, 16) == 1

            return ParsedApproval(
                token_address=token_address,
                owner=owner,
                spender=operator,
                approval_type=ApprovalType.ERC721_ALL,  # Could also be ERC1155
                approved=approved,
                block_number=block_number,
                tx_hash=tx_hash,
                log_index=log_index
            )

        except Exception as e:
            print(f"Error parsing ApprovalForAll log: {e}")
            return None

    def reconstruct_current_state(
        self, 
        approvals: list[ParsedApproval]
    ) -> dict[str, dict[str, ParsedApproval]]:
        """
        Reconstruct current approval state from event history.
        Later events override earlier ones for same token+spender pair.
        
        Returns:
            Dict[token_address, Dict[spender, ParsedApproval]]
        """
        state: dict[str, dict[str, ParsedApproval]] = {}
        
        # Sort by block number then log index
        sorted_approvals = sorted(
            approvals, 
            key=lambda x: (x.block_number, x.log_index)
        )
        
        for approval in sorted_approvals:
            token = approval.token_address
            spender = approval.spender
            
            if token not in state:
                state[token] = {}
            
            # For ERC20: value of 0 means revoked
            # For ApprovalForAll: approved=False means revoked
            if approval.approval_type == ApprovalType.ERC20 and approval.value == 0:
                # Revoked - remove from state
                state[token].pop(spender, None)
            elif approval.approval_type in [ApprovalType.ERC721_ALL, ApprovalType.ERC1155_ALL] and not approval.approved:
                # Revoked - remove from state
                state[token].pop(spender, None)
            else:
                # Active approval
                state[token][spender] = approval
        
        return state
