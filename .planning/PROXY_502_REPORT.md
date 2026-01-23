# PROXY 502 REPORT

**Date:** 2026-01-23
**Phase:** PHASE 2 - Proxy/502 Recovery

---

## Summary

Proxy configurations found reference Docker services, not direct ports. No changes required for standalone UI on port 3456.

---

## Proxy Configuration Analysis

### Nginx Configurations Found

1. **`nginx.conf`**
   - Upstream: `trading_ui:80` (Docker service)
   - Used in Docker Compose/Swarm stack
   - Not applicable for standalone UI

2. **`nginx-reverse-proxy.conf`**
   - Upstream: `trading_ui:80` (Docker service)
   - Used in Docker Swarm stack
   - Not applicable for standalone UI

3. **`deploy/nginx/nginx.conf`**
   - Upstream: `ui:3000` (Docker service)
   - Used in deployment stack
   - Not applicable for standalone UI

### Docker Compose Configurations

**Files Checked:**
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker-compose.demo.yml`
- `deploy/docker-compose.yml`

**Findings:**
- All reference Docker services (`trading_ui`, `ui`)
- Port mappings: `3000:80`, `3001:3000`
- No direct port 3456 references

---

## Standalone UI Deployment

### Current Setup

**UI Running On:**
- Port: `3456`
- Host: `0.0.0.0` (LAN-visible)
- Access: `http://<LAN_IP>:3456` or `http://localhost:3456`

### Proxy Integration (If Needed)

If a standalone nginx proxy is running and needs to point to UI:

**Option 1: Direct Port Proxy**
```nginx
upstream ui_next {
    server 127.0.0.1:3456;
}

server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://ui_next;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Option 2: Update Existing Config**
If `nginx-reverse-proxy.conf` is used standalone:
```nginx
# Change line 124 from:
set $ui_upstream trading_ui:80;
# To:
set $ui_upstream 127.0.0.1:3456;
```

---

## Docker Stack Integration

### Current Docker Services

**Service Names:**
- `trading_ui` - Old UI service (port 80)
- `ui` - Alternative UI service (port 3000)

**Note:** These are Docker service names, not direct ports. They require Docker Swarm/Compose to resolve.

### If Updating Docker Stack

**docker-compose.yml example:**
```yaml
services:
  ui-next:
    image: node:18
    command: npm run start
    environment:
      - PORT=3456
      - HOSTNAME=0.0.0.0
    ports:
      - "3456:3456"
```

Then update nginx upstream:
```nginx
upstream ui {
    server ui-next:3456;
}
```

---

## 502 Error Troubleshooting

### Common Causes

1. **Upstream Not Running**
   - Check: `curl http://127.0.0.1:3456`
   - Fix: Start UI with `./ui-next/scripts/run_3456.sh`

2. **Wrong Upstream Port**
   - Check: nginx config upstream port
   - Fix: Update to `127.0.0.1:3456`

3. **Docker Service Not Resolved**
   - Check: Docker service name resolution
   - Fix: Ensure Docker stack is running

4. **Firewall Blocking**
   - Check: `sudo ufw status`
   - Fix: Allow port 3456 if needed

---

## Recommendations

### For Standalone Deployment

**No proxy changes needed** if:
- UI is accessed directly on port 3456
- No nginx proxy is running
- Docker stack is not in use

### For Docker Stack Deployment

**Update required** if:
- Docker stack is active
- Nginx proxy is running
- Need to route through proxy

**Action:** Update Docker service or nginx upstream to point to UI on port 3456.

---

## Verification

### Check if Nginx is Running

```bash
# Check nginx process
ps aux | grep nginx

# Check nginx config
sudo nginx -t

# Check listening ports
ss -lntp | grep :80
```

### Test Proxy (If Running)

```bash
# Test upstream
curl -I http://127.0.0.1:3456

# Test through proxy
curl -I http://localhost/
```

---

## Conclusion

- ✅ No standalone nginx configs found pointing to wrong port
- ✅ Docker configs reference services (not direct ports)
- ✅ Standalone UI on 3456 works independently
- ⚠️ If Docker stack is active, may need service update

**Status:** No changes required for standalone UI deployment.

**Note:** Docker stack integration would require separate update if stack is active.

---

*Generated: 2026-01-23*
