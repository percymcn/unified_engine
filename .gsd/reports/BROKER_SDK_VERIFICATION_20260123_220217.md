# Broker SDK Verification Report
Generated: 2026-01-23T22:02:17.801892
Backend: http://127.0.0.1:8765

## Test Results

### TRADELOCKER

- **test-connection**: ✅ PASS
- **discover-accounts**: ✅ PASS
- **create-account**: ❌ FAIL
- **account-list**: ❌ FAIL

### PROJECTX

- **test-connection**: ✅ PASS
- **discover-accounts**: ✅ PASS
- **create-account**: ❌ FAIL
- **account-list**: ❌ FAIL

### TOPSTEP

- **test-connection**: ✅ PASS
- **discover-accounts**: ✅ PASS
- **create-account**: ❌ FAIL
- **account-list**: ❌ FAIL

### MT4

- **test-connection**: ✅ PASS
- **discover-accounts**: ✅ PASS
- **create-account**: ❌ FAIL
- **account-list**: ❌ FAIL

### MT5

- **test-connection**: ✅ PASS
- **discover-accounts**: ✅ PASS
- **create-account**: ❌ FAIL
- **account-list**: ❌ FAIL

## Curl Commands

### Authentication
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8765/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser789","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### TRADELOCKER

**Test Connection:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"broker":"tradelocker","credentials":{"username": "test@example.com", "password": "testpassword", "server": "Demo Server"}}'
```

### PROJECTX

**Test Connection:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"broker":"projectx","credentials":{"username": "testuser", "api_key": "test_api_key_12345"}}'
```

### TOPSTEP

**Test Connection:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"broker":"topstep","credentials":{"username": "testuser", "api_key": "test_api_key_12345"}}'
```

### MT4

**Test Connection:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"broker":"mt4","credentials":{"metaapi_token": "test_token_12345", "metaapi_account_id": "test_account_12345"}}'
```

### MT5

**Test Connection:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/accounts/test-connection \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"broker":"mt5","credentials":{"metaapi_token": "test_token_12345", "metaapi_account_id": "test_account_12345"}}'
```
