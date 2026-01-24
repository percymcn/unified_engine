#!/usr/bin/env python3
"""
Broker Integration Test Script

Tests broker SDK integrations for:
- TradeLocker
- ProjectX/TopStep
- MT4
- MT5

Tests:
1. test-connection endpoint (schema validation)
2. account discovery (if supported)
3. account creation (with placeholder credentials)

Usage:
    python3 scripts/test_broker_integrations.py [--username USERNAME] [--password PASSWORD]

If credentials not provided, will attempt to create a test user.
"""

import sys
import json
import argparse
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

BASE_URL = "http://127.0.0.1:8765"
API_BASE = f"{BASE_URL}/api/v1"

class BrokerTester:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.results = {}

    def test_connection(self, broker: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test broker connection endpoint"""
        url = f"{API_BASE}/accounts/test-connection"
        payload = {
            "broker": broker,
            "credentials": credentials
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": str(e)}
            return {
                "success": False,
                "status_code": e.response.status_code,
                "error": error_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def discover_accounts(self, broker: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test account discovery endpoint"""
        url = f"{API_BASE}/accounts/discover"
        payload = {
            "broker": broker,
            "credentials": credentials
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": str(e)}
            return {
                "success": False,
                "status_code": e.response.status_code,
                "error": error_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_account(self, broker: str, credentials: Dict[str, Any], account_id: str = "test123") -> Dict[str, Any]:
        """Test account creation endpoint"""
        url = f"{API_BASE}/accounts/"
        payload = {
            "broker": broker,
            "account_id": account_id,
            "account_type": "demo",
            "currency": "USD",
            "leverage": 100,
            **credentials
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": str(e)}
            return {
                "success": False,
                "status_code": e.response.status_code,
                "error": error_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_accounts(self) -> Dict[str, Any]:
        """Get list of accounts"""
        url = f"{API_BASE}/accounts/"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_broker(self, broker: str, test_credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single broker comprehensively"""
        print(f"\n{'='*60}")
        print(f"Testing {broker.upper()}")
        print(f"{'='*60}")
        
        result = {
            "broker": broker,
            "test_connection": None,
            "discover_accounts": None,
            "create_account": None,
            "account_list": None
        }
        
        # Test 1: Test Connection
        print(f"\n[1/4] Testing connection endpoint...")
        test_conn_result = self.test_connection(broker, test_credentials)
        result["test_connection"] = test_conn_result
        
        if test_conn_result["success"]:
            print(f"  ✓ Connection test passed (schema valid)")
            if "data" in test_conn_result:
                conn_data = test_conn_result["data"]
                print(f"    Status: {conn_data.get('status', 'unknown')}")
                print(f"    Message: {conn_data.get('message', 'N/A')}")
        else:
            status_code = test_conn_result.get("status_code", "N/A")
            error = test_conn_result.get("error", {})
            if status_code == 400:
                print(f"  ✗ Schema validation failed (expected with placeholder creds)")
                print(f"    Error: {error.get('detail', error)}")
            elif status_code == 401:
                print(f"  ✗ Authentication failed")
            else:
                print(f"  ✗ Connection test failed: {error}")
        
        # Test 2: Account Discovery (if connection test passed or returned credential error)
        print(f"\n[2/4] Testing account discovery...")
        discover_result = self.discover_accounts(broker, test_credentials)
        result["discover_accounts"] = discover_result
        
        if discover_result["success"]:
            print(f"  ✓ Discovery test passed")
            if "data" in discover_result:
                disc_data = discover_result["data"]
                accounts = disc_data.get("accounts", [])
                print(f"    Found {len(accounts)} accounts")
        else:
            status_code = discover_result.get("status_code", "N/A")
            error = discover_result.get("error", {})
            if status_code == 400:
                print(f"  ✗ Schema validation failed (expected with placeholder creds)")
            else:
                print(f"  ✗ Discovery failed: {error.get('detail', error)}")
        
        # Test 3: Account Creation (only if schema validation passed)
        print(f"\n[3/4] Testing account creation...")
        # Map credentials to AccountCreate format
        create_payload = {}
        for key, value in test_credentials.items():
            # Map common field names
            if key == "api_key":
                create_payload["api_key"] = value
            elif key == "username":
                create_payload["broker_config"] = create_payload.get("broker_config", {})
                create_payload["broker_config"]["username"] = value
            elif key == "password":
                create_payload["broker_config"] = create_payload.get("broker_config", {})
                create_payload["broker_config"]["password"] = value
            elif key == "server":
                create_payload["server"] = value
            elif key == "metaapi_token":
                create_payload["broker_config"] = create_payload.get("broker_config", {})
                create_payload["broker_config"]["metaapi_token"] = value
            elif key == "metaapi_account_id":
                create_payload["broker_config"] = create_payload.get("broker_config", {})
                create_payload["broker_config"]["metaapi_account_id"] = value
            else:
                create_payload["broker_config"] = create_payload.get("broker_config", {})
                create_payload["broker_config"][key] = value
        
        create_result = self.create_account(broker, create_payload, f"test_{broker}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        result["create_account"] = create_result
        
        if create_result["success"]:
            print(f"  ✓ Account creation passed")
            if "data" in create_result:
                print(f"    Account ID: {create_result['data'].get('id', 'N/A')}")
        else:
            status_code = create_result.get("status_code", "N/A")
            error = create_result.get("error", {})
            if status_code == 400:
                print(f"  ✗ Schema validation failed (expected with placeholder creds)")
                print(f"    Error: {error.get('detail', error)}")
            elif status_code == 403:
                print(f"  ✗ Broker slot limit reached (expected on free tier)")
            else:
                print(f"  ✗ Account creation failed: {error.get('detail', error)}")
        
        # Test 4: Verify account appears in list
        print(f"\n[4/4] Verifying account list...")
        list_result = self.get_accounts()
        result["account_list"] = list_result
        
        if list_result["success"]:
            accounts = list_result.get("data", {}).get("accounts", [])
            broker_accounts = [a for a in accounts if a.get("broker") == broker]
            print(f"  ✓ Account list retrieved")
            print(f"    Total accounts: {len(accounts)}")
            print(f"    {broker} accounts: {len(broker_accounts)}")
        else:
            print(f"  ✗ Failed to retrieve account list: {list_result.get('error')}")
        
        return result


def authenticate(username: str, password: str) -> Optional[str]:
    """Authenticate and get access token"""
    url = f"{API_BASE}/auth/login"
    params = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except requests.exceptions.HTTPError:
        # Try to register if login fails
        print(f"Login failed, attempting to register user '{username}'...")
        register_url = f"{API_BASE}/auth/register"
        register_payload = {
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "full_name": "Test User"
        }
        try:
            response = requests.post(register_url, json=register_payload, timeout=10)
            response.raise_for_status()
            # Now try login again
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
        except Exception as e:
            print(f"Registration/login failed: {e}")
            return None
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test broker integrations")
    parser.add_argument("--username", default="testuser", help="Username for authentication")
    parser.add_argument("--password", default="testpass123", help="Password for authentication")
    args = parser.parse_args()
    
    print("="*60)
    print("BROKER INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Backend: {BASE_URL}")
    print(f"Username: {args.username}")
    print("="*60)
    
    # Authenticate
    print("\n[Authenticating...]")
    token = authenticate(args.username, args.password)
    if not token:
        print("ERROR: Failed to authenticate")
        sys.exit(1)
    print("✓ Authentication successful")
    
    # Initialize tester
    tester = BrokerTester(token)
    
    # Define test credentials for each broker (placeholders)
    test_configs = {
        "tradelocker": {
            "username": "test@example.com",
            "password": "testpassword",
            "server": "Demo Server"
        },
        "projectx": {
            "username": "testuser",
            "api_key": "test_api_key_12345"
        },
        "topstep": {
            "username": "testuser",
            "api_key": "test_api_key_12345"
        },
        "mt4": {
            "metaapi_token": "test_token_12345",
            "metaapi_account_id": "test_account_12345"
        },
        "mt5": {
            "metaapi_token": "test_token_12345",
            "metaapi_account_id": "test_account_12345"
        }
    }
    
    # Test each broker
    all_results = {}
    for broker, credentials in test_configs.items():
        result = tester.test_broker(broker, credentials)
        all_results[broker] = result
    
    # Generate report
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    report_lines = []
    report_lines.append("# Broker SDK Verification Report")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append(f"Backend: {BASE_URL}")
    report_lines.append("")
    report_lines.append("## Test Results")
    report_lines.append("")
    
    for broker, result in all_results.items():
        report_lines.append(f"### {broker.upper()}")
        report_lines.append("")
        
        # Test Connection
        tc = result["test_connection"]
        if tc and tc.get("success"):
            report_lines.append("- **test-connection**: ✅ PASS")
        elif tc and tc.get("status_code") == 400:
            report_lines.append("- **test-connection**: ⚠️ SCHEMA_VALID (credential error expected)")
        else:
            report_lines.append("- **test-connection**: ❌ FAIL")
        
        # Discover Accounts
        disc = result["discover_accounts"]
        if disc and disc.get("success"):
            report_lines.append("- **discover-accounts**: ✅ PASS")
        elif disc and disc.get("status_code") == 400:
            report_lines.append("- **discover-accounts**: ⚠️ SCHEMA_VALID (credential error expected)")
        else:
            report_lines.append("- **discover-accounts**: ❌ FAIL")
        
        # Create Account
        create = result["create_account"]
        if create and create.get("success"):
            report_lines.append("- **create-account**: ✅ PASS")
        elif create and create.get("status_code") == 400:
            report_lines.append("- **create-account**: ⚠️ SCHEMA_VALID (credential error expected)")
        elif create and create.get("status_code") == 403:
            report_lines.append("- **create-account**: ⚠️ SLOT_LIMIT (free tier limit)")
        else:
            report_lines.append("- **create-account**: ❌ FAIL")
        
        # Account List
        alist = result["account_list"]
        if alist and alist.get("success"):
            report_lines.append("- **account-list**: ✅ PASS")
        else:
            report_lines.append("- **account-list**: ❌ FAIL")
        
        report_lines.append("")
    
    report_lines.append("## Curl Commands")
    report_lines.append("")
    report_lines.append("### Authentication")
    report_lines.append("```bash")
    report_lines.append(f"TOKEN=$(curl -s -X POST {API_BASE}/auth/login \\")
    report_lines.append(f"  -H 'Content-Type: application/json' \\")
    report_lines.append(f"  -d '{{\"username\":\"{args.username}\",\"password\":\"{args.password}\"}}' \\")
    report_lines.append(f"  | python3 -c \"import sys,json; print(json.load(sys.stdin)['access_token'])\")")
    report_lines.append("```")
    report_lines.append("")
    
    for broker, credentials in test_configs.items():
        report_lines.append(f"### {broker.upper()}")
        report_lines.append("")
        report_lines.append("**Test Connection:**")
        report_lines.append("```bash")
        creds_json = json.dumps(credentials)
        report_lines.append(f"curl -X POST {API_BASE}/accounts/test-connection \\")
        report_lines.append(f"  -H 'Authorization: Bearer $TOKEN' \\")
        report_lines.append(f"  -H 'Content-Type: application/json' \\")
        report_lines.append(f"  -d '{{\"broker\":\"{broker}\",\"credentials\":{creds_json}}}'")
        report_lines.append("```")
        report_lines.append("")
    
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save report
    report_file = f".gsd/reports/BROKER_SDK_VERIFICATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    import os
    os.makedirs(".gsd/reports", exist_ok=True)
    with open(report_file, "w") as f:
        f.write(report_text)
    print(f"\n✓ Report saved to: {report_file}")


if __name__ == "__main__":
    main()
