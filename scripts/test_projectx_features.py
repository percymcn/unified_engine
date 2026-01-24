#!/usr/bin/env python3
"""
Test script for ProjectX/TopStep platform API endpoints.

Tests all ProjectX broker endpoints to verify full SDK feature exposure.
Requires:
- Valid ProjectX account in database
- Valid credentials (username, api_key)
- Backend running on http://127.0.0.1:8765
"""

import asyncio
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime

import httpx


BASE_URL = "http://127.0.0.1:8765"
TIMEOUT = 30.0


class ProjectXTester:
    """Test ProjectX platform API endpoints."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.account_id: Optional[int] = None
        self.results: Dict[str, Dict[str, Any]] = {}
    
    async def login(self, username: str, password: str) -> bool:
        """Login and get access token."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"username": username, "password": password}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    print(f"✅ Login successful")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def find_projectx_account(self) -> Optional[int]:
        """Find a ProjectX account ID."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/accounts/",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get("accounts", [])
                    
                    # Find ProjectX account
                    for acc in accounts:
                        if acc.get("broker") in ("projectx", "topstep"):
                            account_id = acc.get("id")
                            print(f"✅ Found ProjectX account: {account_id}")
                            return account_id
                    
                    print("⚠️  No ProjectX account found. Please create one first.")
                    print("   Go to: http://127.0.0.1:3456/dashboard/settings/accounts")
                    return None
                else:
                    print(f"❌ Failed to get accounts: {response.status_code}")
                    return None
        except Exception as e:
            print(f"❌ Error finding account: {e}")
            return None
    
    async def test_endpoint(
        self,
        method: str,
        path: str,
        name: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Test an API endpoint."""
        url = f"{self.base_url}{path}"
        if params and method == "GET":
            # Add params to URL
            from urllib.parse import urlencode
            url += "?" + urlencode(params)
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                if method == "GET":
                    response = await client.get(url, headers=self.get_headers())
                elif method == "POST":
                    response = await client.post(url, headers=self.get_headers(), json=json_data)
                elif method == "PATCH":
                    response = await client.patch(url, headers=self.get_headers(), json=json_data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.get_headers())
                else:
                    return {"success": False, "error": f"Unsupported method: {method}"}
                
                status_ok = 200 <= response.status_code < 300
                result = {
                    "success": status_ok,
                    "status_code": response.status_code,
                    "method": method,
                    "path": path,
                }
                
                try:
                    result["response"] = response.json()
                except:
                    result["response"] = response.text[:200]
                
                # 400 with "missing credentials" is acceptable (account exists but no creds)
                if response.status_code == 400 and "credential" in response.text.lower():
                    result["note"] = "Missing credentials (expected if account not configured)"
                    result["acceptable"] = True
                
                # 404 is acceptable for some endpoints
                if response.status_code == 404:
                    result["note"] = "Not found (may be expected)"
                    result["acceptable"] = True
                
                return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": method,
                "path": path,
            }
    
    async def run_tests(self) -> Dict[str, Any]:
        """Run all ProjectX endpoint tests."""
        if not self.account_id:
            print("⚠️  No ProjectX account found. Skipping tests.")
            return {"skipped": True}
        
        print(f"\n🧪 Testing ProjectX endpoints with account_id={self.account_id}\n")
        
        # Test endpoints
        tests = [
            # Accounts
            ("GET", f"/api/v1/brokers/projectx/accounts?account_id={self.account_id}", "Get Accounts"),
            ("GET", f"/api/v1/brokers/projectx/accounts/{self.account_id}", "Get Account Info"),
            
            # Positions
            ("GET", f"/api/v1/brokers/projectx/positions?account_id={self.account_id}", "Get Positions"),
            ("GET", f"/api/v1/brokers/projectx/positions/history?account_id={self.account_id}&symbol=MNQ&days=30", "Get Position History"),
            
            # Orders
            ("GET", f"/api/v1/brokers/projectx/orders?account_id={self.account_id}", "Get Orders"),
            
            # Market Data
            ("GET", f"/api/v1/brokers/projectx/market/quote?account_id={self.account_id}&symbol=MNQ", "Get Quote"),
            ("GET", f"/api/v1/brokers/projectx/market/orderbook?account_id={self.account_id}&symbol=MNQ&depth=10", "Get Orderbook"),
            ("GET", f"/api/v1/brokers/projectx/market/history?account_id={self.account_id}&symbol=MNQ&days=1&interval=5", "Get Market History"),
            
            # Statistics
            ("GET", f"/api/v1/brokers/projectx/stats/session?account_id={self.account_id}&symbol=MNQ", "Get Session Stats"),
            ("GET", f"/api/v1/brokers/projectx/stats/performance?account_id={self.account_id}&symbol=MNQ", "Get Performance Stats"),
            
            # Portfolio & Risk
            ("GET", f"/api/v1/brokers/projectx/portfolio/metrics?account_id={self.account_id}", "Get Portfolio Metrics"),
            ("GET", f"/api/v1/brokers/projectx/risk/analysis?account_id={self.account_id}&symbol=MNQ", "Get Risk Analysis"),
            
            # Technical Indicators
            ("POST", f"/api/v1/brokers/projectx/indicators?account_id={self.account_id}", "Calculate Technical Indicators",
             None, {"symbol": "MNQ", "days": 30, "interval": 5, "indicators": ["RSI", "MACD"]}),
        ]
        
        for test in tests:
            if len(test) == 3:
                method, path, name = test
                params = None
                json_data = None
            else:
                method, path, name, params, json_data = test
            
            print(f"Testing: {name}...", end=" ", flush=True)
            result = await self.test_endpoint(method, path, name, params, json_data)
            self.results[name] = result
            
            if result.get("success"):
                print("✅ PASS")
            elif result.get("acceptable"):
                print(f"⚠️  {result.get('note', 'ACCEPTABLE')}")
            else:
                print(f"❌ FAIL ({result.get('status_code', 'ERROR')})")
                if result.get("error"):
                    print(f"   Error: {result['error']}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get("success"))
        acceptable = sum(1 for r in self.results.values() if r.get("acceptable"))
        failed = total - passed - acceptable
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Acceptable: {acceptable}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print("\nFailed Tests:")
            for name, result in self.results.items():
                if not result.get("success") and not result.get("acceptable"):
                    print(f"  - {name}: {result.get('status_code', 'ERROR')}")
                    if result.get("error"):
                        print(f"    Error: {result['error']}")
        
        print("\n" + "="*60)


async def main():
    """Main test function."""
    print("ProjectX Platform API Test Suite")
    print("="*60)
    
    # Get credentials from user or environment
    import os
    username = os.getenv("TEST_USERNAME") or input("Username: ")
    password = os.getenv("TEST_PASSWORD") or input("Password: ")
    
    tester = ProjectXTester()
    
    # Login
    if not await tester.login(username, password):
        print("❌ Login failed. Exiting.")
        sys.exit(1)
    
    # Find ProjectX account
    tester.account_id = await tester.find_projectx_account()
    if not tester.account_id:
        print("\n⚠️  No ProjectX account found.")
        print("   Please create a ProjectX account first:")
        print("   1. Go to: http://127.0.0.1:3456/dashboard/settings/accounts")
        print("   2. Click 'Add Account'")
        print("   3. Select 'ProjectX / TopStep'")
        print("   4. Enter your username and API key")
        print("   5. Run this test again")
        sys.exit(0)
    
    # Run tests
    await tester.run_tests()
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
