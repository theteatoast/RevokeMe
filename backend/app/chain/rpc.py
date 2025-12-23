"""
RPC Client for blockchain interactions.
Handles all JSON-RPC calls to Ethereum nodes.
"""
import httpx
from typing import Optional
from app.config import settings


# Event signatures (keccak256 hashes)
APPROVAL_ERC20 = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_ERC721 = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"  # Same as ERC20
APPROVAL_FOR_ALL = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
TRANSFER_ERC20 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class RPCClient:
    """Client for interacting with blockchain RPC endpoints."""

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.eth_rpc_url
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _call(self, method: str, params: list) -> dict:
        """Make a JSON-RPC call."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": self._next_id()
                }
            )
            result = response.json()
            if "error" in result:
                raise Exception(f"RPC Error: {result['error']}")
            return result.get("result")

    @staticmethod
    def pad_address(address: str) -> str:
        """Pad address to 32 bytes for topic matching."""
        return "0x" + address[2:].lower().zfill(64)

    @staticmethod  
    def unpad_address(padded: str) -> str:
        """Extract address from 32-byte padded topic."""
        return "0x" + padded[26:].lower()

    async def get_approval_logs(
        self, 
        address: str, 
        from_block: str = "0x0",  # Block 0
        to_block: str = "latest"
    ) -> dict:
        """
        Fetch all approval event logs where address is the owner.
        Returns ERC20 approvals, ERC721 approvals, and ApprovalForAll events.
        """
        padded_address = self.pad_address(address)
        
        # Use a reasonable block range to avoid RPC timeouts
        # Most RPCs limit "earliest" queries - use last ~2 years of blocks
        # (~7200 blocks/day * 730 days = ~5.2M blocks)
        try:
            current_block = await self._call("eth_blockNumber", [])
            current_block_int = int(current_block, 16)
            # Go back ~2 years or use 0 if chain is newer
            from_block = hex(max(0, current_block_int - 5_000_000))
        except Exception:
            from_block = "0x0"
        
        approval_logs = []
        approval_for_all_logs = []
        
        try:
            # ERC20/ERC721 Approval events (owner is topic1)
            approval_logs = await self._call("eth_getLogs", [{
                "topics": [APPROVAL_ERC20, padded_address],
                "fromBlock": from_block,
                "toBlock": to_block
            }])
        except Exception as e:
            print(f"Error fetching approval logs: {e}")
            approval_logs = []
        
        try:
            # ApprovalForAll events (owner is topic1)
            approval_for_all_logs = await self._call("eth_getLogs", [{
                "topics": [APPROVAL_FOR_ALL, padded_address],
                "fromBlock": from_block,
                "toBlock": to_block
            }])
        except Exception as e:
            print(f"Error fetching ApprovalForAll logs: {e}")
            approval_for_all_logs = []
        
        return {
            "approvals": approval_logs or [],
            "approval_for_all": approval_for_all_logs or []
        }

    async def get_allowance(
        self, 
        token_address: str, 
        owner: str, 
        spender: str
    ) -> int:
        """Get current ERC20 allowance."""
        # allowance(address,address) selector: 0xdd62ed3e
        data = (
            "0xdd62ed3e"
            + owner[2:].lower().zfill(64)
            + spender[2:].lower().zfill(64)
        )
        
        result = await self._call("eth_call", [
            {"to": token_address, "data": data},
            "latest"
        ])
        
        if result and result != "0x":
            return int(result, 16)
        return 0

    async def get_approved(self, token_address: str, token_id: int) -> Optional[str]:
        """Get approved address for a specific ERC721 token."""
        # getApproved(uint256) selector: 0x081812fc
        data = "0x081812fc" + hex(token_id)[2:].zfill(64)
        
        try:
            result = await self._call("eth_call", [
                {"to": token_address, "data": data},
                "latest"
            ])
            if result and result != "0x" and result != "0x" + "0" * 64:
                return self.unpad_address(result)
        except Exception:
            pass
        return None

    async def is_approved_for_all(
        self, 
        token_address: str, 
        owner: str, 
        operator: str
    ) -> bool:
        """Check if operator is approved for all tokens."""
        # isApprovedForAll(address,address) selector: 0xe985e9c5
        data = (
            "0xe985e9c5"
            + owner[2:].lower().zfill(64)
            + operator[2:].lower().zfill(64)
        )
        
        try:
            result = await self._call("eth_call", [
                {"to": token_address, "data": data},
                "latest"
            ])
            if result:
                return int(result, 16) == 1
        except Exception:
            pass
        return False

    async def get_code(self, address: str) -> str:
        """Get contract bytecode. Empty string means EOA."""
        result = await self._call("eth_getCode", [address, "latest"])
        return result or "0x"

    async def is_contract(self, address: str) -> bool:
        """Check if address is a contract."""
        code = await self.get_code(address)
        return code != "0x" and len(code) > 2

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self._call("eth_blockNumber", [])
        return int(result, 16)

    async def get_block_timestamp(self, block_number: int) -> int:
        """Get timestamp for a block."""
        result = await self._call("eth_getBlockByNumber", [
            hex(block_number), 
            False
        ])
        if result and "timestamp" in result:
            return int(result["timestamp"], 16)
        return 0

    async def get_token_info(self, token_address: str) -> dict:
        """Get ERC20 token name, symbol, decimals."""
        info = {"address": token_address, "name": None, "symbol": None, "decimals": 18}
        
        # symbol() - 0x95d89b41
        try:
            result = await self._call("eth_call", [
                {"to": token_address, "data": "0x95d89b41"},
                "latest"
            ])
            if result and len(result) > 2:
                info["symbol"] = self._decode_string(result)
        except Exception:
            pass

        # name() - 0x06fdde03
        try:
            result = await self._call("eth_call", [
                {"to": token_address, "data": "0x06fdde03"},
                "latest"
            ])
            if result and len(result) > 2:
                info["name"] = self._decode_string(result)
        except Exception:
            pass

        # decimals() - 0x313ce567
        try:
            result = await self._call("eth_call", [
                {"to": token_address, "data": "0x313ce567"},
                "latest"
            ])
            if result and result != "0x":
                info["decimals"] = int(result, 16)
        except Exception:
            pass

        return info

    def _decode_string(self, data: str) -> Optional[str]:
        """Decode ABI-encoded string from eth_call result."""
        try:
            if len(data) < 66:
                return None
            # Skip 0x prefix
            hex_data = data[2:]
            # For dynamic string: offset (32 bytes) + length (32 bytes) + data
            if len(hex_data) >= 128:
                length = int(hex_data[64:128], 16)
                string_hex = hex_data[128:128 + length * 2]
                return bytes.fromhex(string_hex).decode('utf-8').rstrip('\x00')
            # For short strings that might be directly encoded
            return bytes.fromhex(hex_data).decode('utf-8').rstrip('\x00')
        except Exception:
            return None
