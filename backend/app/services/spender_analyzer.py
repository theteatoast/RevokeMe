"""
Spender Analyzer Service.
Analyzes spender addresses to determine contract status and verification.
"""
import httpx
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache

from app.config import settings


@dataclass
class SpenderAnalysis:
    """Analysis result for a spender address."""
    address: str
    is_contract: bool
    contract_name: Optional[str] = None
    verified: bool = False
    creation_date: Optional[str] = None
    source_code_available: bool = False


class SpenderAnalyzer:
    """Service for analyzing spender addresses."""

    # Known trusted spenders (major protocols)
    KNOWN_SPENDERS = {
        # Uniswap
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap: Universal Router",
        "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "Uniswap: Universal Router 2",
        "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap: Universal Router 3",
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2: Router 2",
        "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3: Router",
        
        # OpenSea
        "0x1e0049783f008a0085193e00003d00cd54003c71": "OpenSea: Seaport 1.4",
        "0x00000000000001ad428e4906ae43d8f9852d0dd6": "OpenSea: Seaport 1.5",
        "0x00000000000000adc04c56bf30ac9d3c0aaf14dc": "OpenSea: Seaport 1.6",
        
        # Blur
        "0x000000000000ad05ccc4f10045630fb830b95127": "Blur: Marketplace",
        "0x29469395eaf6f95920e59f858042f0e28d98a20b": "Blur: Blend",
        
        # 1inch
        "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch: Aggregation Router V5",
        "0x111111125421ca6dc452d289314280a0f8842a65": "1inch: Aggregation Router V6",
        
        # Aave
        "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": "Aave: AAVE Token",
        "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "Aave: Pool V3",
        
        # Compound
        "0xc00e94cb662c3520282e6f5717214004a7f26888": "Compound: COMP Token",
        
        # Permit2
        "0x000000000022d473030f116ddee9f6b43ac78ba3": "Uniswap: Permit2",
    }

    def __init__(self):
        self._cache: dict[str, SpenderAnalysis] = {}

    async def analyze(self, address: str) -> SpenderAnalysis:
        """
        Analyze a spender address.
        
        Args:
            address: The spender address to analyze
            
        Returns:
            SpenderAnalysis with contract info and verification status
        """
        address = address.lower()
        
        if address in self._cache:
            return self._cache[address]

        # Check if known spender
        if address in self.KNOWN_SPENDERS:
            analysis = SpenderAnalysis(
                address=address,
                is_contract=True,
                contract_name=self.KNOWN_SPENDERS[address],
                verified=True,
                source_code_available=True
            )
            self._cache[address] = analysis
            return analysis

        # For unknown addresses, we'd need to query Etherscan
        # For now, return basic analysis
        analysis = SpenderAnalysis(
            address=address,
            is_contract=True,  # Assume contract, will be verified by RPC
            verified=False
        )
        
        self._cache[address] = analysis
        return analysis

    async def analyze_with_etherscan(
        self, 
        address: str,
        api_key: Optional[str] = None
    ) -> SpenderAnalysis:
        """
        Analyze spender using Etherscan API for richer data.
        
        Args:
            address: The spender address
            api_key: Etherscan API key (uses settings if not provided)
            
        Returns:
            SpenderAnalysis with verification status from Etherscan
        """
        address = address.lower()
        api_key = api_key or getattr(settings, 'etherscan_api_key', None)
        
        if not api_key:
            return await self.analyze(address)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check contract verification
                response = await client.get(
                    "https://api.etherscan.io/api",
                    params={
                        "module": "contract",
                        "action": "getsourcecode",
                        "address": address,
                        "apikey": api_key
                    }
                )
                data = response.json()
                
                if data.get("status") == "1" and data.get("result"):
                    result = data["result"][0]
                    contract_name = result.get("ContractName")
                    verified = bool(contract_name and contract_name != "")
                    
                    analysis = SpenderAnalysis(
                        address=address,
                        is_contract=True,
                        contract_name=contract_name if verified else None,
                        verified=verified,
                        source_code_available=verified
                    )
                    self._cache[address] = analysis
                    return analysis

        except Exception:
            pass

        return await self.analyze(address)

    def is_known_protocol(self, address: str) -> bool:
        """Check if address belongs to a known protocol."""
        return address.lower() in self.KNOWN_SPENDERS

    def get_protocol_name(self, address: str) -> Optional[str]:
        """Get protocol name for known addresses."""
        return self.KNOWN_SPENDERS.get(address.lower())
