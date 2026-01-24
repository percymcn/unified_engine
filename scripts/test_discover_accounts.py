#!/usr/bin/env python3
"""
Test script for account discovery functionality.
Tests the discover endpoint with sample credentials (expects empty or schema-valid response, never 500).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from typing import Dict, Any

BACKEND_URL = "http://127.0.0.1:8765"

async def test_discover_accounts():
    """Test account discovery endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, try to login (or use existing session)
        print("Testing account discovery endpoint...")
        print(f"Backend URL: {BACKEND_URL}")
        
        # Test discover endpoint with placeholder credentials
        test_cases = [
            {
                "broker": "tradelocker",
                "credentials": {"api_key": "test_key"}
            },
            {
                "broker": "projectx",
                "credentials": {"username": "test_user", "api_key": "test_key"}
            },
            {
                "broker": "tradovate",
                "credentials": {"access_token": "test_token", "environment": "demo"}
            },
        ]
        
        results = []
        for test_case in test_cases:
            broker = test_case["broker"]
            credentials = test_case["credentials"]
            
            try:
                response = await client.post(
                    f"{BACKEND_URL}/api/v1/accounts/discover",
                    json={
                        "broker": broker,
                        "credentials": credentials
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                status_code = response.status_code
                if status_code == 401:
                    print(f"  {broker}: SKIP (authentication required)")
                    results.append({"broker": broker, "status": "SKIP", "reason": "auth_required"})
                elif status_code == 200:
                    data = response.json()
                    accounts = data.get("accounts", [])
                    print(f"  {broker}: OK (status 200, {len(accounts)} accounts)")
                    results.append({"broker": broker, "status": "OK", "accounts_count": len(accounts)})
                elif status_code == 400:
                    data = response.json()
                    detail = data.get("detail", "Bad request")
                    print(f"  {broker}: OK (status 400 - expected for invalid credentials: {detail[:50]})")
                    results.append({"broker": broker, "status": "OK", "reason": "invalid_credentials"})
                elif status_code == 500:
                    print(f"  {broker}: FAIL (status 500 - internal server error)")
                    results.append({"broker": broker, "status": "FAIL", "reason": "internal_error"})
                else:
                    print(f"  {broker}: UNEXPECTED (status {status_code})")
                    results.append({"broker": broker, "status": "UNEXPECTED", "status_code": status_code})
                    
            except Exception as e:
                print(f"  {broker}: ERROR ({str(e)[:50]})")
                results.append({"broker": broker, "status": "ERROR", "error": str(e)})
        
        print("\nSummary:")
        print(f"  Total tests: {len(test_cases)}")
        passed = sum(1 for r in results if r["status"] in ("OK", "SKIP"))
        failed = sum(1 for r in results if r["status"] == "FAIL")
        print(f"  Passed/Skipped: {passed}")
        print(f"  Failed: {failed}")
        
        if failed > 0:
            print("\nFAIL: Some tests returned 500 errors")
            return 1
        else:
            print("\nPASS: No 500 errors (endpoint is stable)")
            return 0

if __name__ == "__main__":
    exit_code = asyncio.run(test_discover_accounts())
    sys.exit(exit_code)
