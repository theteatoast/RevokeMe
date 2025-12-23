"""
Contract ABI definitions and helpers.
"""

# ERC20 ABI (minimal for approval operations)
ERC20_ABI = [
    {
        "name": "allowance",
        "type": "function",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable"
    },
    {
        "name": "symbol",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view"
    },
    {
        "name": "name",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view"
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view"
    }
]

# ERC721 ABI (minimal for approval operations)
ERC721_ABI = [
    {
        "name": "getApproved",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view"
    },
    {
        "name": "isApprovedForAll",
        "type": "function",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "operator", "type": "address"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view"
    },
    {
        "name": "setApprovalForAll",
        "type": "function",
        "inputs": [
            {"name": "operator", "type": "address"},
            {"name": "approved", "type": "bool"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    }
]

# ERC1155 ABI (minimal for approval operations)
ERC1155_ABI = [
    {
        "name": "isApprovedForAll",
        "type": "function",
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "operator", "type": "address"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view"
    },
    {
        "name": "setApprovalForAll",
        "type": "function",
        "inputs": [
            {"name": "operator", "type": "address"},
            {"name": "approved", "type": "bool"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    }
]


# Function selectors (first 4 bytes of keccak256 hash)
SELECTORS = {
    "allowance": "0xdd62ed3e",
    "approve": "0x095ea7b3",
    "getApproved": "0x081812fc",
    "isApprovedForAll": "0xe985e9c5",
    "setApprovalForAll": "0xa22cb465",
    "symbol": "0x95d89b41",
    "name": "0x06fdde03",
    "decimals": "0x313ce567",
}


# Max uint256 - represents unlimited approval
MAX_UINT256 = 2**256 - 1


def is_unlimited_allowance(value: int) -> bool:
    """Check if allowance value represents unlimited approval."""
    # Consider anything above 90% of max as unlimited
    # This catches various "max - 1" patterns
    return value >= MAX_UINT256 * 0.9


def format_allowance(value: int, decimals: int = 18) -> str:
    """Format allowance value for display."""
    if is_unlimited_allowance(value):
        return "Unlimited"
    
    # Format with proper decimals
    if decimals > 0:
        formatted = value / (10 ** decimals)
        if formatted >= 1_000_000_000:
            return f"{formatted / 1_000_000_000:.2f}B"
        elif formatted >= 1_000_000:
            return f"{formatted / 1_000_000:.2f}M"
        elif formatted >= 1_000:
            return f"{formatted / 1_000:.2f}K"
        else:
            return f"{formatted:.4f}"
    return str(value)


def generate_revoke_calldata(spender: str) -> str:
    """Generate calldata for revoking an ERC20 approval (approve(spender, 0))."""
    return (
        SELECTORS["approve"]
        + spender[2:].lower().zfill(64)
        + "0" * 64  # value = 0
    )


def generate_revoke_all_calldata(operator: str) -> str:
    """Generate calldata for revoking ApprovalForAll (setApprovalForAll(operator, false))."""
    return (
        SELECTORS["setApprovalForAll"]
        + operator[2:].lower().zfill(64)
        + "0" * 64  # approved = false
    )
