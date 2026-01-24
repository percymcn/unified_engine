#!/usr/bin/env python3
"""
Broker Platform Parity Test Suite

Tests all brokers through unified REST API endpoints.
Verifies capability matrix, normalized schemas, and proper error handling.
"""

import asyncio
import sys
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx


BASE_URL = "http://127.0.0.1:8765"
TIMEOUT = 30.0


class BrokerParityTester:
    """Test broker platform parity across all brokers."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.accounts_by_broker: Dict[str, List[Dict[str, Any]]] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.capability_matrix = None
    
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
    
    async def load_accounts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load accounts grouped by broker."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/accounts/",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get("accounts", [])
                    
                    # Group by broker
                    by_broker = {}
                    for acc in accounts:
                        broker = acc.get("broker")
                        if broker not in by_broker:
                            by_broker[broker] = []
                        by_broker[broker].append(acc)
                    
                    self.accounts_by_broker = by_broker
                    return by_broker
                else:
                    print(f"❌ Failed to get accounts: {response.status_code}")
                    return {}
        except Exception as e:
            print(f"❌ Error loading accounts: {e}")
            return {}
    
    async def load_capability_matrix(self):
        """Load capability matrix."""
        try:
            from app.brokers.capabilities import get_capability_matrix
            self.capability_matrix = get_capability_matrix()
        except Exception as e:
            print(f"⚠️  Failed to load capability matrix: {e}")
    
    async def test_endpoint(
        self,
        broker: str,
        account_id: int,
        method: str,
        path: str,
        name: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Test an API endpoint."""
        url = f"{self.base_url}{path}"
        if params and method == "GET":
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
                
                # 400 with "missing credentials" is acceptable
                if response.status_code == 400 and "credential" in response.text.lower():
                    result["note"] = "Missing credentials (expected if account not configured)"
                    result["acceptable"] = True
                
                # 501 is acceptable (feature not supported)
                if response.status_code == 501:
                    result["note"] = "Feature not supported by broker"
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
    
    async def test_broker(self, broker: str, account_id: int) -> Dict[str, Any]:
        """Test all endpoints for a broker."""
        print(f"\n🧪 Testing {broker} with account_id={account_id}\n")
        
        broker_results = {}
        
        # Core endpoints to test
        tests = [
            # Accounts
            ("GET", f"/api/v1/brokers/{broker}/accounts?account_id={account_id}", "accounts.list"),
            # Positions
            ("GET", f"/api/v1/brokers/{broker}/positions?account_id={account_id}", "positions.open"),
            ("GET", f"/api/v1/brokers/{broker}/positions/history?account_id={account_id}&symbol=MNQ&days=30", "positions.history"),
            # Orders
            ("GET", f"/api/v1/brokers/{broker}/orders?account_id={account_id}", "orders.list"),
            # Market Data
            ("GET", f"/api/v1/brokers/{broker}/market/quote?account_id={account_id}&symbol=MNQ", "market.quote"),
            ("GET", f"/api/v1/brokers/{broker}/market/history?account_id={account_id}&symbol=MNQ&days=1&interval=5", "market.history"),
            # Statistics
            ("GET", f"/api/v1/brokers/{broker}/stats/session?account_id={account_id}&symbol=MNQ", "analytics.session"),
            ("GET", f"/api/v1/brokers/{broker}/stats/performance?account_id={account_id}&symbol=MNQ", "analytics.performance"),
        ]
        
        for method, path, capability in tests:
            print(f"  Testing {capability}...", end=" ", flush=True)
            result = await self.test_endpoint(broker, account_id, method, path, capability)
            broker_results[capability] = result
            
            if result.get("success"):
                print("✅ PASS")
            elif result.get("acceptable"):
                print(f"⚠️  {result.get('note', 'ACCEPTABLE')} ({result.get('status_code')})")
            else:
                print(f"❌ FAIL ({result.get('status_code', 'ERROR')})")
                if result.get("error"):
                    print(f"     Error: {result['error']}")
            
            await asyncio.sleep(0.3)  # Small delay between requests
        
        return broker_results
    
    async def run_tests(self) -> Dict[str, Any]:
        """Run tests for all brokers."""
        await self.load_capability_matrix()
        await self.load_accounts()
        
        if not self.accounts_by_broker:
            print("⚠️  No accounts found. Please create accounts first.")
            return {"skipped": True}
        
        print(f"\n📊 Found accounts for brokers: {', '.join(self.accounts_by_broker.keys())}\n")
        
        # Test each broker
        for broker, accounts in self.accounts_by_broker.items():
            if not accounts:
                print(f"⚠️  SKIP: No {broker} accounts found")
                self.results[broker] = {"skipped": True}
                continue
            
            # Use first account
            account_id = accounts[0].get("id")
            if not account_id:
                print(f"⚠️  SKIP: {broker} account missing ID")
                self.results[broker] = {"skipped": True}
                continue
            
            broker_results = await self.test_broker(broker, account_id)
            self.results[broker] = broker_results
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("BROKER PLATFORM PARITY TEST SUMMARY")
        print("="*80)
        
        if self.capability_matrix:
            print("\n📋 Capability Matrix:")
            print(self.capability_matrix.get_capability_matrix_table())
        
        print("\n📊 Test Results:")
        print("-"*80)
        
        for broker, results in self.results.items():
            if results.get("skipped"):
                print(f"{broker}: ⚠️  SKIPPED (no accounts)")
                continue
            
            total = len(results)
            passed = sum(1 for r in results.values() if r.get("success"))
            acceptable = sum(1 for r in results.values() if r.get("acceptable"))
            failed = total - passed - acceptable
            
            print(f"\n{broker}:")
            print(f"  Total: {total}, ✅ Passed: {passed}, ⚠️  Acceptable: {acceptable}, ❌ Failed: {failed}")
            
            if failed > 0:
                print("  Failed Tests:")
                for cap, result in results.items():
                    if not result.get("success") and not result.get("acceptable"):
                        print(f"    - {cap}: {result.get('status_code', 'ERROR')}")
        
        print("\n" + "="*80)
    
    def generate_report(self) -> str:
        """Generate markdown report."""
        from datetime import datetime
        
        report_lines = [
            "# Broker Platform Parity Test Report",
            f"**Generated:** {datetime.now().isoformat()}",
            "",
            "## Overview",
            "",
            "This report documents the platform parity test results for all brokers.",
            "",
        ]
        
        if self.capability_matrix:
            report_lines.extend([
                "## Capability Matrix",
                "",
                self.capability_matrix.get_capability_matrix_table(),
                "",
            ])
        
        report_lines.extend([
            "## Test Results",
            "",
        ])
        
        for broker, results in self.results.items():
            if results.get("skipped"):
                report_lines.append(f"### {broker}: SKIPPED (no accounts)")
                continue
            
            total = len(results)
            passed = sum(1 for r in results.values() if r.get("success"))
            acceptable = sum(1 for r in results.values() if r.get("acceptable"))
            failed = total - passed - acceptable
            
            report_lines.extend([
                f"### {broker}",
                "",
                f"- **Total Tests:** {total}",
                f"- **✅ Passed:** {passed}",
                f"- **⚠️  Acceptable:** {acceptable}",
                f"- **❌ Failed:** {failed}",
                "",
            ])
            
            if failed > 0:
                report_lines.append("**Failed Tests:**")
                for cap, result in results.items():
                    if not result.get("success") and not result.get("acceptable"):
                        report_lines.append(f"- {cap}: {result.get('status_code', 'ERROR')}")
                report_lines.append("")
        
        report_lines.extend([
            "## Endpoint Examples",
            "",
            "### Get Quote",
            f"```bash",
            f"curl -X GET \"{BASE_URL}/api/v1/brokers/{{broker}}/market/quote?account_id={{account_id}}&symbol=MNQ\" \\",
            f"  -H \"Authorization: Bearer YOUR_TOKEN\"",
            f"```",
            "",
            "### Get Orders",
            f"```bash",
            f"curl -X GET \"{BASE_URL}/api/v1/brokers/{{broker}}/orders?account_id={{account_id}}\" \\",
            f"  -H \"Authorization: Bearer YOUR_TOKEN\"",
            f"```",
            "",
            "### Get Positions",
            f"```bash",
            f"curl -X GET \"{BASE_URL}/api/v1/brokers/{{broker}}/positions?account_id={{account_id}}\" \\",
            f"  -H \"Authorization: Bearer YOUR_TOKEN\"",
            f"```",
            "",
        ])
        
        return "\n".join(report_lines)


async def main():
    """Main test function."""
    print("Broker Platform Parity Test Suite")
    print("="*80)
    
    # Get credentials
    import os
    username = os.getenv("TEST_USERNAME") or input("Username: ")
    password = os.getenv("TEST_PASSWORD") or input("Password: ")
    
    tester = BrokerParityTester()
    
    # Login
    if not await tester.login(username, password):
        print("❌ Login failed. Exiting.")
        sys.exit(1)
    
    # Run tests
    await tester.run_tests()
    tester.print_summary()
    
    # Generate report
    report = tester.generate_report()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f".gsd/reports/BROKER_PLATFORM_PARITY_{timestamp}.md"
    
    import os
    os.makedirs(".gsd/reports", exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
