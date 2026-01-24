#!/usr/bin/env python3
"""
Auth Flow Smoke Test

Tests the complete auth flow:
1. Register a new user
2. Login with credentials
3. Access protected endpoint (GET /api/v1/accounts/)

Usage:
    python3 scripts/smoke_auth.sh
    # OR
    python3 scripts/test_auth_flows.py
"""

import sys
import json
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8765"
API_BASE = f"{BASE_URL}/api/v1"

def test_register(username: str, email: str, password: str) -> dict:
    """Test user registration"""
    print(f"\n[1/3] Testing registration...")
    url = f"{API_BASE}/auth/register"
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"  ✅ Registration successful")
        print(f"    User ID: {data.get('id')}")
        print(f"    Username: {data.get('username')}")
        print(f"    Email: {data.get('email')}")
        return {"success": True, "data": data}
    except requests.exceptions.HTTPError as e:
        try:
            error_data = e.response.json()
        except:
            error_data = {"error": str(e)}
        print(f"  ❌ Registration failed: {error_data.get('detail', error_data.get('error', str(e)))}")
        return {"success": False, "error": error_data}
    except Exception as e:
        print(f"  ❌ Registration failed: {e}")
        return {"success": False, "error": str(e)}

def test_login(username: str, password: str) -> dict:
    """Test user login"""
    print(f"\n[2/3] Testing login...")
    url = f"{API_BASE}/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if token:
            print(f"  ✅ Login successful")
            print(f"    Token: {token[:20]}...")
            print(f"    Token type: {data.get('token_type')}")
            print(f"    Expires in: {data.get('expires_in')} seconds")
            return {"success": True, "token": token, "data": data}
        else:
            print(f"  ❌ Login failed: No token in response")
            return {"success": False, "error": "No token in response"}
    except requests.exceptions.HTTPError as e:
        try:
            error_data = e.response.json()
        except:
            error_data = {"error": str(e)}
        print(f"  ❌ Login failed: {error_data.get('detail', error_data.get('error', str(e)))}")
        return {"success": False, "error": error_data}
    except Exception as e:
        print(f"  ❌ Login failed: {e}")
        return {"success": False, "error": str(e)}

def test_protected_endpoint(token: str) -> dict:
    """Test accessing protected endpoint"""
    print(f"\n[3/3] Testing protected endpoint (GET /api/v1/accounts/)...")
    url = f"{API_BASE}/accounts/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        accounts = data.get("accounts", [])
        print(f"  ✅ Protected endpoint accessible")
        print(f"    Status: {response.status_code}")
        print(f"    Accounts found: {len(accounts)}")
        return {"success": True, "data": data}
    except requests.exceptions.HTTPError as e:
        try:
            error_data = e.response.json()
        except:
            error_data = {"error": str(e)}
        print(f"  ❌ Protected endpoint failed: {error_data.get('detail', error_data.get('error', str(e)))}")
        return {"success": False, "error": error_data}
    except Exception as e:
        print(f"  ❌ Protected endpoint failed: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("="*60)
    print("AUTH FLOW SMOKE TEST")
    print("="*60)
    print(f"Backend: {BASE_URL}")
    
    # Generate unique username with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    username = f"smoke_test_{timestamp}"
    email = f"{username}@example.com"
    password = "testpass123"
    
    print(f"\nTest credentials:")
    print(f"  Username: {username}")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    
    # Test 1: Register
    register_result = test_register(username, email, password)
    if not register_result["success"]:
        print("\n❌ Registration failed - cannot continue")
        sys.exit(1)
    
    # Test 2: Login
    login_result = test_login(username, password)
    if not login_result["success"]:
        print("\n❌ Login failed - cannot continue")
        sys.exit(1)
    
    token = login_result["token"]
    
    # Test 3: Protected endpoint
    protected_result = test_protected_endpoint(token)
    if not protected_result["success"]:
        print("\n❌ Protected endpoint test failed")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    print("\nAuth flow is working correctly:")
    print("  ✅ Registration")
    print("  ✅ Login")
    print("  ✅ Protected endpoint access")
    
    print("\n" + "="*60)
    print("CURL COMMANDS FOR VERIFICATION")
    print("="*60)
    print(f"""
# 1. Register
curl -s -X POST {API_BASE}/auth/register \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps({"username": username, "email": email, "password": password, "full_name": "Test User"})}'

# 2. Login
curl -s -X POST {API_BASE}/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps({"username": username, "password": password})}'

# 3. Get accounts (replace TOKEN with actual token from login)
TOKEN=$(curl -s -X POST {API_BASE}/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps({"username": username, "password": password})}' \\
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X GET {API_BASE}/accounts/ \\
  -H "Authorization: Bearer $TOKEN" \\
  | python3 -m json.tool
""")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
