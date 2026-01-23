# PROD BUILD REPORT - January 2026

**Date:** 2026-01-23
**Phase:** Frontend Build Verification

---

## Summary

UI-Next builds cleanly and runs on port 3456.

---

## Build Results

### Commands Executed

```bash
cd /home/pharma5/unified_engine/ui-next
npm run build
```

### Build Output (Summary)

```
✓ Generating static pages (57/57)
○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand

Total routes: 65
Static pages: 15
Dynamic routes: 50 (API + SSR)
```

### Page Sizes (Key Pages)

| Route | Size | First Load JS |
|-------|------|--------------|
| `/` | 15.8 kB | 183 kB |
| `/dashboard` | 118 kB | 261 kB |
| `/login` | 4.11 kB | 139 kB |
| `/register` | 4.3 kB | 139 kB |

### Shared JS Bundle
```
First Load JS shared by all: 87.5 kB
```

---

## Server Verification

### Start Command
```bash
PORT=3456 HOSTNAME=0.0.0.0 npm run start
```

### Health Check
```bash
curl -I http://localhost:3456
```

### Result
```
HTTP/1.1 200 OK
X-Powered-By: Next.js
x-nextjs-cache: HIT
Content-Type: text/html; charset=utf-8
Content-Length: 143367
```

**Status:** ✅ PASSED

---

## Dynamic Server Warnings (Expected)

These are **informational** - not blocking:

| Route | Reason |
|-------|--------|
| `/api/users/me/profile` | Uses `cookies()` |
| `/api/billing/plans` | Uses `cookies()` |

**Note:** Routes using `cookies()` cannot be statically rendered. This is expected Next.js behavior.

---

## Script Created

**Location:** `ui-next/scripts/run_3456.sh`

**Usage:**
```bash
cd /home/pharma5/unified_engine/ui-next
./scripts/run_3456.sh
```

**Steps:**
1. Install dependencies (npm ci)
2. Build (npm run build)
3. Kill existing process on 3456
4. Start on port 3456
5. Verify with curl

**Logs:** `/tmp/ui-next_3456.log`

---

## Conclusion

- ✅ Build passes
- ✅ No lint errors blocking production
- ✅ Server starts on port 3456
- ✅ HTTP 200 response verified
- ✅ Script created for repeatable deployment

---

---

## Verification (2026-01-23 18:35 UTC)

**Build Status:** ✅ PASSED
```bash
cd /home/pharma5/unified_engine/ui-next
npm run build
# Result: Build successful, all routes generated
```

**Server Start:** ✅ VERIFIED
```bash
PORT=3456 HOSTNAME=0.0.0.0 npm run start
curl -I http://127.0.0.1:3456
# Result: HTTP/1.1 200 OK
```

**Script Status:** ✅ READY
- Location: `ui-next/scripts/run_3456.sh`
- Executable: Yes
- Tested: Yes

---

*Generated: 2026-01-23*
*Last Verified: 2026-01-23 18:35 UTC*
