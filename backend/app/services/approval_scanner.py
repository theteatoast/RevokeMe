"""
Approval Scanner Service.
Scans blockchain for token approvals and reconstructs current state.
"""
import asyncio
from dataclasses import dataclass
from typing import Optional
import time

from app.chain.rpc import RPCClient
from app.chain.logs import LogParser, ParsedApproval, ApprovalType
from app.chain.contracts import is_unlimited_allowance, format_allowance


@dataclass
class TokenInfo:
    """Token information."""
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    decimals: int = 18
    token_type: str = "ERC20"

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "symbol": self.symbol or "Unknown",
            "name": self.name or "Unknown Token",
            "decimals": self.decimals,
            "type": self.token_type
        }


@dataclass
class SpenderInfo:
    """Spender information."""
    address: str
    is_contract: bool = False
    name: Optional[str] = None
    verified: bool = False

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "is_contract": self.is_contract,
            "name": self.name or ("Contract" if self.is_contract else "EOA"),
            "verified": self.verified
        }


@dataclass
class ActiveApproval:
    """An active approval with all relevant details."""
    token: TokenInfo
    spender: SpenderInfo
    approval_type: ApprovalType
    allowance_raw: Optional[int] = None
    allowance_formatted: str = "0"
    is_unlimited: bool = False
    block_number: int = 0
    timestamp: int = 0
    age_days: int = 0
    tx_hash: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "token": self.token.to_dict(),
            "spender": self.spender.to_dict(),
            "approval_type": self.approval_type.value,
            "allowance": self.allowance_formatted,
            "allowance_raw": str(self.allowance_raw) if self.allowance_raw else None,
            "is_unlimited": self.is_unlimited,
            "block_number": self.block_number,
            "age_days": self.age_days,
            "tx_hash": self.tx_hash
        }


class ApprovalScanner:
    """Service for scanning token approvals."""

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_client = RPCClient(rpc_url)
        self.log_parser = LogParser()
        self._token_cache: dict[str, TokenInfo] = {}
        self._spender_cache: dict[str, SpenderInfo] = {}

    async def scan(self, address: str, chain_id: int = 1) -> list[ActiveApproval]:
        """
        Scan for all active token approvals for a given address.
        
        Args:
            address: The wallet address to scan
            chain_id: The chain ID (1 for Ethereum mainnet)
            
        Returns:
            List of ActiveApproval objects representing current permissions
        """
        address = address.lower()
        
        try:
            # Step 1: Fetch all approval logs
            raw_logs = await self.rpc_client.get_approval_logs(address)
        except Exception as e:
            print(f"Error fetching approval logs: {e}")
            # Return empty list if RPC fails
            return []
        
        # Step 2: Parse logs into approval events
        parsed_approvals = self.log_parser.parse_approval_logs(raw_logs)
        
        # Step 3: Reconstruct current state (latest approval per token+spender)
        current_state = self.log_parser.reconstruct_current_state(parsed_approvals)
        
        # Step 4: Verify current allowances on-chain and enrich data
        active_approvals = []
        
        try:
            current_block = await self.rpc_client.get_block_number()
        except Exception:
            current_block = 0
            
        current_time = int(time.time())
        
        for token_address, spenders in current_state.items():
            for spender_address, parsed in spenders.items():
                try:
                    approval = await self._verify_and_enrich(
                        parsed, 
                        address,
                        current_block,
                        current_time
                    )
                    if approval:
                        active_approvals.append(approval)
                except Exception as e:
                    print(f"Error verifying approval {token_address} -> {spender_address}: {e}")
                    continue
        
        # Sort by risk factors (unlimited first, then by age)
        active_approvals.sort(
            key=lambda x: (not x.is_unlimited, -x.age_days),
            reverse=False
        )
        
        return active_approvals

    async def _verify_and_enrich(
        self,
        parsed: ParsedApproval,
        owner: str,
        current_block: int,
        current_time: int
    ) -> Optional[ActiveApproval]:
        """Verify approval is still active and enrich with additional data."""
        
        token_address = parsed.token_address
        spender_address = parsed.spender
        
        # Check current on-chain state
        if parsed.approval_type == ApprovalType.ERC20:
            # Verify current allowance
            current_allowance = await self.rpc_client.get_allowance(
                token_address, owner, spender_address
            )
            if current_allowance == 0:
                return None  # Already revoked
                
            is_unlimited = is_unlimited_allowance(current_allowance)
            
        elif parsed.approval_type in [ApprovalType.ERC721_ALL, ApprovalType.ERC1155_ALL]:
            # Verify ApprovalForAll is still active
            is_approved = await self.rpc_client.is_approved_for_all(
                token_address, owner, spender_address
            )
            if not is_approved:
                return None  # Already revoked
            
            current_allowance = None
            is_unlimited = True  # ApprovalForAll is always unlimited
            
        else:
            # ERC721 specific token approval - skip for now
            return None

        # Get token info
        token_info = await self._get_token_info(token_address, parsed.approval_type)
        
        # Get spender info
        spender_info = await self._get_spender_info(spender_address)
        
        # Calculate age
        age_days = 0
        timestamp = 0
        if parsed.block_number > 0:
            try:
                timestamp = await self.rpc_client.get_block_timestamp(parsed.block_number)
                age_days = (current_time - timestamp) // 86400
            except Exception:
                # Estimate from blocks (~12 sec per block)
                blocks_ago = current_block - parsed.block_number
                age_days = (blocks_ago * 12) // 86400

        # Format allowance
        if current_allowance is not None:
            allowance_formatted = format_allowance(current_allowance, token_info.decimals)
        else:
            allowance_formatted = "All Tokens"

        return ActiveApproval(
            token=token_info,
            spender=spender_info,
            approval_type=parsed.approval_type,
            allowance_raw=current_allowance,
            allowance_formatted=allowance_formatted,
            is_unlimited=is_unlimited,
            block_number=parsed.block_number,
            timestamp=timestamp,
            age_days=age_days,
            tx_hash=parsed.tx_hash
        )

    async def _get_token_info(
        self, 
        address: str, 
        approval_type: ApprovalType
    ) -> TokenInfo:
        """Get token info with caching."""
        if address in self._token_cache:
            return self._token_cache[address]
        
        info = await self.rpc_client.get_token_info(address)
        
        # Determine token type
        if approval_type in [ApprovalType.ERC721, ApprovalType.ERC721_ALL]:
            token_type = "ERC721"
        elif approval_type == ApprovalType.ERC1155_ALL:
            token_type = "ERC1155"
        else:
            token_type = "ERC20"
        
        token_info = TokenInfo(
            address=address,
            symbol=info.get("symbol"),
            name=info.get("name"),
            decimals=info.get("decimals", 18),
            token_type=token_type
        )
        
        self._token_cache[address] = token_info
        return token_info

    async def _get_spender_info(self, address: str) -> SpenderInfo:
        """Get spender info with caching."""
        if address in self._spender_cache:
            return self._spender_cache[address]
        
        is_contract = await self.rpc_client.is_contract(address)
        
        # TODO: Add Etherscan API lookup for contract name/verification
        spender_info = SpenderInfo(
            address=address,
            is_contract=is_contract,
            name=None,
            verified=False  # Would need Etherscan API to verify
        )
        
        self._spender_cache[address] = spender_info
        return spender_info
