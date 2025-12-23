import httpx
from app.config import settings


class RPCClient:
    """Client for interacting with blockchain RPC endpoints."""

    def __init__(self):
        self.rpc_url = settings.eth_rpc_url

    async def get_approval_logs(self, address: str, chain_id: int) -> list:
        """
        Fetch approval event logs for an address.
        
        Args:
            address: The wallet address
            chain_id: The chain ID
            
        Returns:
            List of raw log entries
        """
        # ERC20 Approval event signature
        approval_topic = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
        
        # TODO: Implement actual RPC call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getLogs",
                    "params": [{
                        "topics": [approval_topic, None, self._pad_address(address)],
                        "fromBlock": "earliest",
                        "toBlock": "latest"
                    }],
                    "id": 1
                }
            )
            result = response.json()
            return result.get("result", [])

    def _pad_address(self, address: str) -> str:
        """Pad address to 32 bytes for topic matching."""
        return "0x" + address[2:].lower().zfill(64)
