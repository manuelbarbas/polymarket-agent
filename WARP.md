# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

An autonomous AI-powered prediction market trading agent for Polymarket that demonstrates true economic autonomy through the x402 protocol. The agent pays for its own AI inference using USDC micropayments on SKALE (gasless Layer 2), analyzes prediction markets using AI models via BlockRun, calculates optimal position sizes using Kelly Criterion, and executes trades on Polygon.

**Key Features:**
- Self-sovereign AI payments via x402 protocol (no API keys, wallet = authentication)
- SKALE blockchain integration for gasless USDC payments to AI providers
- Polymarket trading with Gnosis Safe proxy wallet support
- AI-powered market analysis (currently GPT-5.2, with multi-model consensus planned)
- Kelly Criterion position sizing for risk management
- Web dashboard + CLI interface

## Architecture

### Dual-Chain Wallet System
The agent operates across **two blockchains simultaneously**:

**1. SKALE Chain (AI Payments)**
- **Purpose**: Pay for AI inference via BlockRun using x402 protocol
- **Currency**: USDC (gasless transfers)
- **Wallet**: `SKALE_CHAIN_WALLET_KEY` or `BLOCKRUN_WALLET_KEY`
- **Network**: SKALE Europa Hub
- **Why SKALE**: Zero gas fees for USDC transfers, optimized for AI micropayments

**2. Polygon Chain (Trading)**
- **Purpose**: Execute trades on Polymarket
- **Currency**: USDC (for trades), POL (for gas)
- **Wallet**: `POLYGON_WALLET_PRIVATE_KEY` (signer) + `POLYMARKET_PROXY_WALLET` (Gnosis Safe)
- **Network**: Polygon PoS

**Important**: The same private key can be used for both chains (same address on both networks).

### Polymarket Proxy Wallet Architecture
Polymarket uses a **Gnosis Safe** for security and account abstraction:

- **Signer Wallet (EOA)**: Your private key that signs transactions
  - Set via `POLYGON_WALLET_PRIVATE_KEY`
  - Needs POL for gas
  - Must be authorized as owner of the Gnosis Safe
  
- **Proxy Wallet (Gnosis Safe)**: Smart contract that holds trading funds
  - Set via `POLYMARKET_PROXY_WALLET`
  - Holds USDC for trades
  - Created automatically by Polymarket on first login
  - Only authorized signers can execute trades

- **Signature Type Detection**: `signature_type=2` when proxy ≠ signer, else `0`
  - Located in `src/trading/executor.py:_ensure_initialized()`

**Critical Setup Requirement:**
- The signer wallet MUST be the same wallet you used to create your Polymarket account
- The proxy wallet address is found in Polymarket Settings → Wallet
- If signer is not authorized for the proxy, you'll get `invalid signature` errors

### AI Model Architecture
**Current Implementation (v1.0):**
- Single model: `openai/gpt-5.2` via BlockRun
- Pays per request using x402 protocol on SKALE
- Located in `src/analysis/ai_analyzer.py`

**Planned (v2.0):**
- Multi-model consensus voting for reliability
- Models: GPT-5.2, Gemini 2.0 Flash, Claude 3.5 Haiku (or latest available)
- Configurable model selection (enable/disable individual models)
- Adjustable parameters per model (temperature, confidence thresholds)
- Consensus logic: Agent only trades when 2+ models agree
- Customizable strategies based on user preferences

### x402 Payment Protocol Flow
The agent uses the **x402 HTTP payment protocol** for AI inference:

1. Agent makes AI request to BlockRun API
2. BlockRun returns `402 Payment Required` with payment details (amount, recipient)
3. Agent signs USDC transfer on SKALE using EIP-3009 `transferWithAuthorization`
4. Payment signature is attached to retry request
5. BlockRun validates payment, processes AI request, transfers USDC atomically
6. Response returned to agent

**Key Benefits:**
- No API keys needed - wallet address = identity
- Pay-per-use pricing (no subscriptions)
- Gasless payments on SKALE
- Atomic settlement (payment + service delivery)

## Development Commands

### Setup & Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your wallet keys and settings
```

### Running the Agent

**Web Dashboard (Recommended)**:
```bash
python3 app.py
# Visit http://127.0.0.1:5001 (or 5000 if 5001 is taken)
# Basic auth: credentials from ADMIN_USER/ADMIN_PASS in .env
```

**CLI Commands**:
```bash
# Check configuration and wallet balances
python3 main.py --status

# Fetch markets and run AI analysis only (no trading, costs ~$0.01 in USDC on SKALE)
python3 main.py --analyze

# Dry run (simulate without executing trades)
python3 main.py

# Live trading (requires confirmation)
python3 main.py --live
```

### Testing & Validation

There is no formal test suite. To validate:
```bash
# Check configuration and wallet setup
python3 main.py --status

# Validate AI analysis works (costs ~$0.01 USDC on SKALE per analysis)
python3 main.py --analyze

# Check wallet balances
python3 -c "from src.trading.wallet import get_wallet; w=get_wallet(); print(w.get_balances())"

# Test Kelly Criterion calculator
python3 -m src.utils.kelly

# Regenerate Polymarket API credentials if needed
python3 regenerate_creds.py
```

### Deployment

**Deploy to Google Cloud Run (Tokyo region - not geoblocked)**:
```bash
# Edit PROJECT_ID in deploy-tokyo.sh first
./deploy-tokyo.sh
```

**Why Tokyo?** Polymarket's CLOB API blocks order placement (`POST /order`) from US, EU, UK, Singapore, and Australia due to regulatory restrictions. Tokyo (`asia-northeast1`) is an allowed region. `GET` requests work from anywhere.

## Project Structure

```
polymarket-agent/
├── app.py                      # Flask web dashboard - main entry point for UI
├── main.py                     # CLI entry point - run agent from command line
├── src/
│   ├── agent.py                # Main orchestrator - coordinates all components
│   ├── market/
│   │   └── polymarket.py       # Gamma API client - fetches market data
│   ├── analysis/
│   │   └── ai_analyzer.py      # BlockRun integration - handles AI consensus
│   ├── trading/
│   │   ├── wallet.py           # Polygon wallet management
│   │   └── executor.py         # Trade execution via py-clob-client
│   ├── signals/
│   │   └── trades.py           # Whale/smart money tracking (optional)
│   └── utils/
│       └── kelly.py            # Position sizing calculator
└── templates/
    ├── index.html              # Dashboard UI
    └── setup.html              # Setup guide UI
```

## Critical Implementation Details

### API Credentials for Polymarket
Polymarket requires API credentials for trading. The agent handles this two ways:

**Option A: Auto-derive (automatic)**:
- Agent calls `client.create_or_derive_api_creds()` on first run
- Credentials are logged to console
- **Important**: Save these to `.env` to avoid re-deriving

**Option B: Pre-generate (recommended for production)**:
```python
from py_clob_client.client import ClobClient
client = ClobClient(
    "https://clob.polymarket.com",
    key=PRIVATE_KEY,
    chain_id=137,
    signature_type=2,
    funder=PROXY_WALLET
)
creds = client.create_or_derive_api_creds()
# Save to .env: POLYMARKET_API_KEY, POLYMARKET_API_SECRET, POLYMARKET_PASSPHRASE
```

### Signature Types in py-clob-client
The executor auto-detects signature type:
- `signature_type=0`: EOA (signer == funder) - direct wallet
- `signature_type=1`: POLY_PROXY - email/magic link wallets (rare)
- `signature_type=2`: GNOSIS_SAFE - standard Polymarket proxy (most users)

Logic in `src/trading/executor.py:_ensure_initialized()`:
```python
sig_type = 2 if self.wallet_address != self.signer_address else 0
```

### Token ID Extraction
Markets provide token IDs for YES/NO outcomes. The code checks multiple fields in order:
1. `tokens[].token_id` array
2. `clobTokenIds` (can be JSON array string or comma-separated)
3. `outcomes[].token_id` array

Located in `src/market/polymarket.py:_parse_token_ids()`. If no token IDs found, trades cannot execute.

### Position Sizing Parameters
Configured via `.env` or defaults:
- `INITIAL_BANKROLL=100` - Starting capital in USD
- `MAX_BET_PERCENTAGE=0.05` - Max 5% of bankroll per trade
- `MIN_EDGE_PERCENTAGE=0.15` - Minimum 15% edge required to trade
- Kelly Criterion uses **quarter-Kelly** (`kelly_fraction=0.25`) for safety

### AI Analysis Logic
**Current (v1.0)**: Single-model analysis using `openai/gpt-5.2`
- Located in `src/analysis/ai_analyzer.py`
- Model returns: probability estimate, confidence (1-10), reasoning
- Trades when model identifies sufficient edge

**Planned (v2.0)**: Multi-model consensus
- Each model returns: probability estimate, confidence (1-10), reasoning
- Consensus determined by majority vote (2+ of 3 models)
- Average edge calculated across models
- Only trades if consensus is strong ("BULLISH" or "BEARISH", not "MIXED")
- Can incorporate whale/smart money data if available

## Environment Variables

### Required
- `SKALE_CHAIN_WALLET_KEY` or `BLOCKRUN_WALLET_KEY` - SKALE chain private key for AI payments via x402
- `POLYGON_WALLET_PRIVATE_KEY` - Polygon signer private key (can be same as SKALE key)
- `POLYMARKET_PROXY_WALLET` - Gnosis Safe proxy wallet address from Polymarket Settings → Wallet

### Optional but Recommended
- `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_PASSPHRASE` - Trading credentials (auto-derived if not set)
- `ADMIN_USER`, `ADMIN_PASS` - Dashboard authentication (defaults to no auth if not set)
- `INITIAL_BANKROLL` - Starting capital in USD (default: 100)
- `MAX_BET_PERCENTAGE` - Max bet as fraction of bankroll (default: 0.05 = 5%)
- `MIN_EDGE_PERCENTAGE` - Minimum edge required to trade (default: 0.15 = 15%)

## Common Issues & Solutions

### "invalid signature" (400) Error
**Cause**: Signer wallet not authorized for the Gnosis Safe proxy, or incorrect API credentials.
**Solution**: 
1. Verify `POLYGON_WALLET_PRIVATE_KEY` is the same wallet you used to create your Polymarket account
2. Verify `POLYMARKET_PROXY_WALLET` is the correct Gnosis Safe address from Polymarket Settings
3. Delete API credentials from `.env` and regenerate: `python3 regenerate_creds.py`
4. Ensure the signer wallet is an authorized owner of the Gnosis Safe

### "403 Forbidden" on Order Placement
**Cause**: Deployed to geoblocked region.
**Solution**: Deploy to Tokyo using `./deploy-tokyo.sh`

### No Token IDs Found
**Cause**: Market data format changed or field missing.
**Solution**: Check `_parse_token_ids()` in `src/market/polymarket.py` and update parsing logic

### "insufficient balance" on Trades
**Cause**: USDC not in proxy wallet or insufficient POL for gas.
**Solution**: 
- Deposit USDC to the **proxy wallet address** (not signer), visible in Polymarket settings
- Ensure signer wallet has POL for gas fees on Polygon

### Markets Filtered Out
**Cause**: Markets have extreme odds (>85% or <15%) or low liquidity (<$5K).
**Solution**: This is intentional filtering in `fetch_active_markets()`. Adjust `min_odds`, `max_odds`, or `min_liquidity` parameters if needed.

## Code Style & Patterns

- **Error Handling**: Functions return `None` or empty lists on failure, with logging via `logger.error()`
- **Logging**: Use Python's `logging` module. Dashboard captures logs in `LogBuffer` for UI display
- **Configuration**: All configuration via environment variables loaded with `python-dotenv`
- **Type Hints**: Used throughout for clarity (e.g., `Optional[str]`, `List[Dict[str, Any]]`)
- **Wallet Initialization**: Lazy initialization pattern - wallets/clients created on first use via `get_*()` factory functions

## Security Notes

- Private keys are only used locally for signing - never sent to external services
- x402 protocol uses EIP-3009 `transferWithAuthorization` for atomic USDC payments
- Dashboard uses basic auth - suitable for single-user deployments
- API credentials should be stored in `.env`, never committed to version control
- When sharing logs or errors, always redact private keys and API credentials

## External APIs Used

- **Polymarket Gamma API**: `https://gamma-api.polymarket.com/markets` - Market data (free, no auth)
- **Polymarket CLOB API**: `https://clob.polymarket.com` - Order placement (requires API creds, geoblocked)
- **BlockRun API**: Accessed via `blockrun-llm` SDK - AI inference (pay-per-use with USDC on SKALE)
  - Current model: `openai/gpt-5.2`
  - Planned: Multiple models with configurable selection and parameters

## Future Multi-Agent Architecture

The codebase is designed for expansion to a **swarm architecture**:
- Market Analysis Agent (current implementation)
- News Agent (planned) - Real-time sentiment analysis
- Edge Detection Agent (planned) - Arbitrage detection
- Whale Tracker Agent (partial implementation in `src/signals/trades.py`)

Vision: Agents that can **call other agents via x402**, creating an autonomous economy of specialized services.
