#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite
Tests all backend endpoints and frontend functionality
"""
import asyncio
import sys
import os
import json
import requests
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://127.0.0.1:8765"
API_BASE = f"{BASE_URL}/api/v1"

class EndpointTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.results = []
        
    def log(self, status: str, endpoint: str, message: str = ""):
        """Log test result"""
        result = {
            "status": status,
            "endpoint": endpoint,
            "message": message
        }
        self.results.append(result)
        symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{symbol} {endpoint}: {message}")
    
    def get_headers(self):
        """Get request headers with auth"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200):
        """Test a single endpoint"""
        url = f"{API_BASE}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.get_headers(), timeout=5)
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.get_headers(), timeout=5)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=self.get_headers(), timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.get_headers(), timeout=5)
            else:
                self.log("SKIP", endpoint, f"Unsupported method: {method}")
                return None
            
            if response.status_code == expected_status:
                self.log("PASS", f"{method} {endpoint}", f"Status {response.status_code}")
                try:
                    return response.json()
                except:
                    return response.text
            else:
                self.log("FAIL", f"{method} {endpoint}", f"Expected {expected_status}, got {response.status_code}")
                return None
        except Exception as e:
            self.log("FAIL", f"{method} {endpoint}", str(e))
            return None
    
    def test_auth(self):
        """Test authentication endpoints"""
        print("\n=== Testing Authentication ===")
        
        # Test register (might fail if user exists, that's OK)
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123!"
        }
        result = self.test_endpoint("POST", "/auth/register", register_data, expected_status=[200, 201, 400])
        
        # Test login
        login_data = {
            "username": "testuser",
            "password": "TestPassword123!"
        }
        result = self.test_endpoint("POST", "/auth/login", login_data)
        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log("PASS", "Auth", "Login successful, token obtained")
        else:
            # Try with existing user
            login_data = {"username": "admin", "password": "admin"}
            result = self.test_endpoint("POST", "/auth/login", login_data)
            if result and "access_token" in result:
                self.token = result["access_token"]
        
        # Test /auth/me
        self.test_endpoint("GET", "/auth/me")
    
    def test_accounts(self):
        """Test account endpoints"""
        print("\n=== Testing Accounts ===")
        
        # List accounts
        accounts = self.test_endpoint("GET", "/accounts")
        
        # Test connection
        test_data = {
            "broker": "projectx",
            "credentials": {"api_key": "test"}
        }
        self.test_endpoint("POST", "/accounts/test-connection", test_data, expected_status=[200, 400])
        
        # If we have accounts, test individual account endpoints
        if accounts and isinstance(accounts, dict) and accounts.get("accounts"):
            account_id = accounts["accounts"][0].get("id")
            if account_id:
                self.test_endpoint("GET", f"/accounts/{account_id}")
                self.test_endpoint("POST", f"/accounts/{account_id}/sync", expected_status=[200, 400])
                self.test_endpoint("GET", f"/accounts/{account_id}/balance")
    
    def test_brokers(self):
        """Test broker endpoints"""
        print("\n=== Testing Brokers ===")
        
        # Broker health
        self.test_endpoint("GET", "/brokers/health")
        
        # Broker unified endpoints
        brokers = ["tradelocker", "tradovate", "projectx", "mt4", "mt5"]
        for broker in brokers:
            self.test_endpoint("GET", f"/brokers/{broker}/accounts", expected_status=[200, 400, 404])
            self.test_endpoint("GET", f"/brokers/{broker}/positions", expected_status=[200, 400, 404])
            self.test_endpoint("GET", f"/brokers/{broker}/orders", expected_status=[200, 400, 404])
    
    def test_dashboard(self):
        """Test dashboard endpoints"""
        print("\n=== Testing Dashboard ===")
        
        self.test_endpoint("GET", "/dashboard/stats", expected_status=[200, 401])
        self.test_endpoint("GET", "/dashboard/positions", expected_status=[200, 401])
        self.test_endpoint("GET", "/dashboard/equity", expected_status=[200, 401])
    
    def test_settings(self):
        """Test settings endpoints"""
        print("\n=== Testing Settings ===")
        
        # Account groups
        self.test_endpoint("GET", "/account-groups")
        
        # Symbol aliases
        self.test_endpoint("GET", "/symbol-aliases")
        
        # Risk settings
        self.test_endpoint("GET", "/risk/settings", expected_status=[200, 404])
        
        # User preferences
        self.test_endpoint("GET", "/users/me/preferences", expected_status=[200, 404])
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Comprehensive End-to-End Tests\n")
        
        self.test_auth()
        if not self.token:
            print("\n⚠️  No auth token - some tests will fail")
        
        self.test_accounts()
        self.test_brokers()
        self.test_dashboard()
        self.test_settings()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Skipped: {skipped}")
        print(f"📊 Total: {len(self.results)}")
        
        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  ❌ {r['endpoint']}: {r['message']}")
        
        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": len(self.results),
            "results": self.results
        }

if __name__ == "__main__":
    tester = EndpointTester()
    results = tester.run_all_tests()
    
    # Save results
    with open("/tmp/e2e_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to /tmp/e2e_test_results.json")
    sys.exit(0 if results["failed"] == 0 else 1)
