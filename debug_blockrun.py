#!/usr/bin/env python3
"""
Debug script to test BlockRun API with detailed logging
"""
import os
import logging
from dotenv import load_dotenv

# Load env
load_dotenv()

# Enable detailed HTTP logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable httpx logging
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)

from blockrun_llm import LLMClient

print("=" * 70)
print("BLOCKRUN API DEBUG")
print("=" * 70)

# Initialize client
print("\nInitializing client...")
client = LLMClient()

print(f"Wallet: {client.get_wallet_address()}")
print(f"API URL: {client.api_url}")
print(f"Network ID: {os.getenv('NETWORK_ID')}")

# Simple test
print("\n" + "=" * 70)
print("TESTING SIMPLE REQUEST")
print("=" * 70)

try:
    print("\nSending: 'Hello' to model glm-4.7")
    response = client.chat('glm-4.7', 'Hello', max_tokens=10)
    print(f"\n✓ SUCCESS!")
    print(f"Response: {response}")
except Exception as e:
    print(f"\n✗ FAILED!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    
    # Print detailed error info
    if hasattr(e, 'status_code'):
        print(f"Status code: {e.status_code}")
    if hasattr(e, 'response'):
        print(f"Response body: {e.response}")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "=" * 70)
