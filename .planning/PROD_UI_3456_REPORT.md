# PROD UI 3456 REPORT

**Date:** 2026-01-23
**Phase:** PHASE 1 - UI Hard Recovery (Port 3456, LAN-Visible)

---

## Summary

UI-Next successfully builds and runs on port 3456, bound to `0.0.0.0` for LAN accessibility.

---

## Build Verification

### Commands Executed

```bash
cd /home/pharma5/unified_engine/ui-next
npm ci
npm run build
```

### Build Results

**Status:** ✅ PASSED
- Dependencies installed successfully
- Build completed without errors
- All routes generated successfully

**Build Output Summary:**
- Total routes: 65+
- Static pages: 15
- Dynamic routes: 50+ (API + SSR)
- First Load JS shared: 87.5 kB

**Key Pages:**
- `/` - 15.8 kB (183 kB first load)
- `/dashboard` - 118 kB (261 kB first load)
- `/login` - 3.38 kB (138 kB first load)
- `/register` - 3.56 kB (138 kB first load)

---

## Server Verification

### Start Command

```bash
cd /home/pharma5/unified_engine/ui-next
PORT=3456 HOSTNAME=0.0.0.0 npm run start
```

### Port Binding

**Configuration:**
- Port: `3456`
- Host: `0.0.0.0` (binds to all interfaces)
- Process: Next.js production server

### Network Access Tests

**Localhost:**
```bash
curl -I http://127.0.0.1:3456
```
**Result:** ✅ HTTP/1.1 200 OK

**LAN IP:**
```bash
curl -I http://192.168.1.254:3456
```
**Result:** ✅ HTTP/1.1 200 OK

**LAN IP Detection:**
- Detected: `192.168.1.254`
- Method: `hostname -I` fallback to `ip addr`

---

## Script Verification

### Location

`ui-next/scripts/run_3456.sh`

### Script Features

1. **Dependency Installation**
   - Uses `npm ci` if `package-lock.json` exists
   - Falls back to `npm install` if lock missing

2. **Build Process**
   - Runs `npm run build`
   - Fails fast on build errors

3. **Port Management**
   - Kills existing process on port 3456 using `fuser -k`
   - Waits 1 second for cleanup

4. **Server Start**
   - Binds to `0.0.0.0:3456` (LAN-visible)
   - Runs in background with `nohup`
   - Logs to `/tmp/ui-next_3456.log`

5. **Verification**
   - Checks localhost (127.0.0.1:3456)
   - Checks LAN IP (if available)
   - Reports HTTP status codes

### Script Usage

```bash
cd /home/pharma5/unified_engine/ui-next
./scripts/run_3456.sh
```

**Expected Output:**
```
=== UI-NEXT BUILD & START ===
[1/5] Installing dependencies...
[2/5] Building Next.js app...
[3/5] Killing any existing process on port 3456...
[4/5] Starting server on port 3456...
Started with PID: <pid>
[5/5] Verifying server is running...

=== SUCCESS ===
UI running on http://localhost:3456
UI also accessible on http://192.168.1.254:3456
LAN access verified: HTTP 200
HTTP status: 200
Logs: tail -f /tmp/ui-next_3456.log
```

---

## Network Configuration

### Binding

**Host:** `0.0.0.0` (all interfaces)
- ✅ Accessible from localhost
- ✅ Accessible from LAN
- ✅ Accessible from WAN (if firewall allows)

### Port

**Port:** `3456`
- Standard HTTP port
- No conflicts detected
- Firewall rules may need adjustment for external access

### LAN IP

**Detected IP:** `192.168.1.254`
- Method: `hostname -I` command
- Fallback: `ip addr` parsing

---

## Verification Commands

### Check if Running

```bash
# Check process
ps aux | grep "next-server" | grep 3456

# Check port binding
ss -lntp | grep 3456
# or
netstat -lntp | grep 3456

# Check logs
tail -f /tmp/ui-next_3456.log
```

### Test Access

```bash
# Localhost
curl -I http://127.0.0.1:3456

# LAN IP (replace with your IP)
curl -I http://192.168.1.254:3456

# Full page test
curl http://127.0.0.1:3456 | head -20
```

---

## Troubleshooting

### Port Already in Use

**Error:** Port 3456 already bound

**Solution:**
```bash
# Kill existing process
fuser -k 3456/tcp

# Or find and kill manually
lsof -ti:3456 | xargs kill -9
```

### Build Fails

**Error:** Build errors or type errors

**Solution:**
- Fix only lint/type blockers that prevent build
- Do not fix warnings that don't block production
- Check `ui-next/.next` for build artifacts

### LAN Access Denied

**Error:** Cannot access from LAN

**Solution:**
- Verify `HOSTNAME=0.0.0.0` is set
- Check firewall rules: `sudo ufw status`
- Verify network interface: `ip addr show`

---

## Production Deployment

### Using Script

```bash
cd /home/pharma5/unified_engine/ui-next
./scripts/run_3456.sh
```

### Manual Start

```bash
cd /home/pharma5/unified_engine/ui-next
npm ci
npm run build
PORT=3456 HOSTNAME=0.0.0.0 npm run start
```

### Systemd Service (Optional)

Create `/etc/systemd/system/ui-next.service`:
```ini
[Unit]
Description=UI-Next on Port 3456
After=network.target

[Service]
Type=simple
User=pharma5
WorkingDirectory=/home/pharma5/unified_engine/ui-next
ExecStart=/usr/bin/npm run start
Environment="PORT=3456"
Environment="HOSTNAME=0.0.0.0"
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Conclusion

- ✅ Build passes
- ✅ Server starts on port 3456
- ✅ Binds to 0.0.0.0 (LAN-visible)
- ✅ Accessible from localhost
- ✅ Accessible from LAN IP
- ✅ Script created and verified
- ✅ Logs to `/tmp/ui-next_3456.log`

**Status:** ✅ PRODUCTION READY

---

*Generated: 2026-01-23*
