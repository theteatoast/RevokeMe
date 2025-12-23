"""
Address Validation API.
Fast endpoint for validating Ethereum addresses.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class ValidateRequest(BaseModel):
    address: str


class ValidateResponse(BaseModel):
    valid: bool
    checksum: str | None = None
    error: str | None = None


def is_valid_ethereum_address(address: str) -> bool:
    """Check if string is a valid Ethereum address format."""
    if not address:
        return False
    # Must start with 0x and be 42 characters
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return False
    return True


def to_checksum_address(address: str) -> str:
    """Convert address to EIP-55 checksum format."""
    import hashlib
    
    # Remove 0x prefix and lowercase
    address = address[2:].lower()
    
    # Hash the address
    hash_hex = hashlib.sha3_256(address.encode()).hexdigest()
    
    # Apply checksum
    checksum = '0x'
    for i, char in enumerate(address):
        if char in '0123456789':
            checksum += char
        elif int(hash_hex[i], 16) >= 8:
            checksum += char.upper()
        else:
            checksum += char.lower()
    
    return checksum


def validate_checksum(address: str) -> bool:
    """Validate that an address has correct checksum (if mixed case)."""
    if address == address.lower() or address == address.upper():
        # All lowercase or all uppercase = no checksum applied
        return True
    
    # Has mixed case - verify checksum
    try:
        expected = to_checksum_address(address)
        return address == expected
    except Exception:
        return False


@router.post("/validate", response_model=ValidateResponse)
async def validate_address(request: ValidateRequest):
    """
    Validate an Ethereum address.
    
    Returns:
        - valid: Whether the address is valid
        - checksum: The checksummed version of the address
        - error: Error message if invalid
    """
    address = request.address.strip()
    
    # Check basic format
    if not is_valid_ethereum_address(address):
        return ValidateResponse(
            valid=False,
            error="Invalid address format. Must be 0x followed by 40 hex characters."
        )
    
    # Validate checksum if present
    if not validate_checksum(address):
        return ValidateResponse(
            valid=False,
            error="Invalid checksum. Address may be mistyped."
        )
    
    # Generate proper checksum
    try:
        checksum = to_checksum_address(address)
    except Exception:
        checksum = address.lower()
    
    return ValidateResponse(
        valid=True,
        checksum=checksum
    )


# Supported chains for MVP
SUPPORTED_CHAINS = {
    1: "Ethereum Mainnet"
}


class ChainValidateRequest(BaseModel):
    chain_id: int


class ChainValidateResponse(BaseModel):
    supported: bool
    name: str | None = None
    error: str | None = None


@router.post("/validate-chain", response_model=ChainValidateResponse)
async def validate_chain(request: ChainValidateRequest):
    """Validate that a chain is supported."""
    if request.chain_id in SUPPORTED_CHAINS:
        return ChainValidateResponse(
            supported=True,
            name=SUPPORTED_CHAINS[request.chain_id]
        )
    
    return ChainValidateResponse(
        supported=False,
        error=f"Chain ID {request.chain_id} not supported. Currently only Ethereum Mainnet (1) is supported."
    )
