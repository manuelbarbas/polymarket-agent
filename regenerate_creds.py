#!/usr/bin/env python3
"""
Regenerate Polymarket API credentials
"""
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

load_dotenv()

private_key = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
proxy_wallet = os.getenv("POLYMARKET_PROXY_WALLET")

if not private_key or not proxy_wallet:
    print("❌ Missing POLYGON_WALLET_PRIVATE_KEY or POLYMARKET_PROXY_WALLET in .env")
    exit(1)

print(f"Signer: {private_key[:10]}...")
print(f"Proxy: {proxy_wallet}")
print("\nGenerating credentials...\n")

# Determine signature type
sig_type = 2 if proxy_wallet.lower() != private_key else 0

client = ClobClient(
    "https://clob.polymarket.com",
    key=private_key,
    chain_id=137,
    signature_type=sig_type,
    funder=proxy_wallet if sig_type == 2 else None
)

try:
    creds = client.create_or_derive_api_creds()
    print("✅ API Credentials generated successfully!\n")
    print("Add these to your .env file:")
    print(f"POLYMARKET_API_KEY={creds.api_key}")
    print(f"POLYMARKET_API_SECRET={creds.api_secret}")
    print(f"POLYMARKET_PASSPHRASE={creds.api_passphrase}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
