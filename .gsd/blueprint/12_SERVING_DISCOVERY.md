# UI Serving Discovery - Port 3456

**Date:** 2026-01-22  
**Investigation:** How Next.js UI is served on port 3456

---

## Phase 1: Discovery Results

### 1. Port 3456 Listener

**Command:** `ss -ltnp | grep :3456`

**Result:**
```
LISTEN 0      511                *:3456             *:*    users:(("next-server (v1",pid=134400,fd=21))
```

**Finding:** Next.js server process (PID 134400) is listening on port 3456.

---

### 2. Process Details

**Command:** `ps -fp 134400`

**Result:**
```
UID          PID    PPID  C STIME TTY          TIME CMD
pharma5   134400  134399  0 12:13 ?        00:00:06 next-server (v14.2.35)
```

**Command:** `tr '\0' ' ' < /proc/134400/cmdline`

**Result:**
```
next-server (v14.2.35)
```

**Command:** `readlink -f /proc/134400/cwd`

**Result:**
```
/home/pharma5/unified_engine/ui-next
```

**Command:** `readlink -f /proc/134400/exe`

**Result:**
```
/usr/bin/node
```

**Finding:** 
- Process is running as user `pharma5`
- Working directory: `/home/pharma5/unified_engine/ui-next`
- Executable: `/usr/bin/node`
- Command: `next-server (v14.2.35)` (Next.js v14.2.35 in production mode)

---

### 3. Parent Process

**Command:** `ps -fp 134399`

**Result:**
```
UID          PID    PPID  C STIME TTY          TIME CMD
pharma5   134399  134385  0 12:13 ?        00:00:00 sh -c next start
```

**Finding:** Parent process is a shell running `next start` command.

---

### 4. Docker Check

**Command:** `docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}" | grep -E "3456|3000"`

**Result:**
```
fluxio-ai-landing-fluxio-landing-1        fluxio-ai-landing-fluxio-landing   0.0.0.0:3003->3000/tcp, [::]:3003->3000/tcp
```

**Finding:** No Docker containers are serving port 3456. The only container found is on port 3003 (unrelated).

**Command:** `docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep -i ui`

**Result:**
```
No docker swarm services found
```

**Finding:** Not running in Docker Swarm.

---

### 5. Systemd Check

**Command:** `systemctl list-units --type=service | grep -Ei "tradeflow|unified|next|ui"`

**Result:**
```
No matching systemd units found
```

**Finding:** Not managed by systemd.

---

### 6. PM2 Check

**Command:** `pm2 list`

**Result:**
```
pm2 not installed or no processes
```

**Finding:** Not managed by PM2.

---

### 7. HTTP Verification

**Command:** `curl -I http://127.0.0.1:3456/`

**Result:**
```
HTTP/1.1 200 OK
Vary: RSC, Next-Router-State-Tree, Next-Router-Prefetch, Accept-Encoding
x-nextjs-cache: HIT
X-Powered-By: Next.js
Cache-Control: s-maxage=31536000, stale-while-revalidate
ETag: "4z31pa9b8c32e3"
Content-Type: text/html; charset=utf-8
Content-Length: 143373
Date: Thu, 22 Jan 2026 19:08:09 GMT
Connection: keep-alive
Keep-Alive: timeout=5
```

**Finding:** Port 3456 is serving Next.js application successfully (HTTP 200).

---

### 8. Build Status

**Command:** `ls -la ui-next/.next`

**Result:**
```
drwxrwxr-x 6 pharma5 pharma5   4096 Jan 22 12:12 .
-rw-rw-r-- 1 pharma5 pharma5     21 Jan 22 12:12 BUILD_ID
```

**Finding:** Build directory exists, last built on Jan 22 12:12.

**Command:** `cat ui-next/package.json | grep -A 5 '"scripts"'`

**Result:**
```
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
```

**Finding:** Standard Next.js scripts available.

---

## Summary

### Serving Method Identified

**Type:** Next.js production server running directly on host (not containerized)

**Details:**
- **Process:** `next-server (v14.2.35)` (PID 134400)
- **Command:** `next start` (production mode)
- **Working Directory:** `/home/pharma5/unified_engine/ui-next`
- **Port:** 3456
- **User:** pharma5
- **Management:** Not systemd, not PM2, not Docker - likely started manually or via script

### Deployment Method

The UI is served by:
1. Running `next start` from `/home/pharma5/unified_engine/ui-next`
2. Process is NOT managed by systemd, PM2, or Docker
3. To update: rebuild with `npm run build` and restart the process

### Restart Method

Since the process is not managed by a service manager, restart requires:
1. Kill the current process (PID 134400)
2. Rebuild: `cd ui-next && npm run build`
3. Restart: `cd ui-next && next start` (or via script if one exists)

**Note:** Check for `start.sh` or similar scripts that may handle the startup.

---

## Next Steps for Deployment

1. **Commit changes** (Phase 3)
2. **Rebuild UI:** `cd ui-next && npm ci && npm run build`
3. **Restart process:** Kill PID 134400, then restart `next start` from `ui-next` directory
4. **Verify:** Check port 3456 returns 200 and UI shows updated broker fields
