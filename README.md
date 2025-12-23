# RevokeMe

A read-only wallet security analysis tool that scans ERC20, ERC721, and ERC1155 token approvals to identify risky permissions.

## Features

- 🔍 **Scan Approvals** - Detect all active token permissions from blockchain logs
- ⚠️ **Risk Assessment** - Score approvals based on allowance, spender type, and age
- 📊 **Hygiene Score** - Overall wallet security rating (0-100)
- 🔗 **Revoke Links** - Direct links to revoke.cash for easy revocation

## Trust Model

- ✅ No wallet connection required
- ✅ No transaction signing
- ✅ Read-only blockchain queries
- ✅ All data from on-chain sources

## Getting Started

### Backend

```bash
cd backend

# Install dependencies
pip install -e .

# Copy environment file
cp .env.example .env

# Run development server
uvicorn app.main:app --reload
```

API available at http://localhost:8000

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend available at http://localhost:3000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/validate` | POST | Validate Ethereum address |
| `/api/scan` | POST | Scan wallet for approvals |
| `/api/share-card` | POST | Get shareable summary data |
| `/health` | GET | Health check |

## Risk Scoring

Approvals are scored based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Unlimited allowance | +40 | Max uint256 approval |
| EOA spender | +35 | Non-contract spender |
| Unknown spender | +20 | Unverified contract |
| ApprovalForAll | +25 | Blanket NFT permission |
| Old approval (6m+) | +15-25 | Stale permissions |

Categories:
- 🟢 **Safe** (0-30): Low risk, verified spenders
- 🟡 **Risky** (31-60): Moderate concerns
- 🔴 **Dangerous** (61-100): Immediate attention needed

## Tech Stack

- **Backend**: Python, FastAPI, httpx
- **Frontend**: Next.js 14, TypeScript, CSS
- **Data**: Direct blockchain RPC queries (no indexer required)

## License

MIT
