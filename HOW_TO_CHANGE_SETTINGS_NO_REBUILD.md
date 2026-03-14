# How to Change Settings WITHOUT Rebuilding Docker

## Quick Config Changes (No Rebuild Needed)

### Option 1: Database Updates (FASTEST - 5 seconds)
For these settings, just update the database:

```sql
-- Change scan interval (5min, 15min, 30min, etc)
UPDATE smartflow_config 
SET ai_only_scan_interval = 900  -- seconds (900 = 15min)
WHERE enabled = true;

-- Change instruments being tracked
UPDATE smartflow_config 
SET ai_only_instruments = '["MES", "NQ", "XAUUSD"]'::jsonb
WHERE id = 1;

-- Enable/disable AI-only mode
UPDATE smartflow_config 
SET enable_ai_only_mode = true
WHERE enabled = true;

-- Change thresholds
UPDATE smartflow_config 
SET buy_threshold = 5.0,
    sell_threshold = -5.0
WHERE enabled = true;
```

**Apply changes**: Just restart the service
```bash
docker service update --force unified_api
```

---

### Option 2: Environment Variables (MEDIUM - 30 seconds)
For API keys and global settings:

```bash
# Edit docker-stack.yml
nano docker-stack.yml

# Find the unified_api service, update environment:
environment:
  - ANTHROPIC_API_KEY=your-new-key
  - DATABASE_URL=postgresql://...

# Redeploy JUST that service
docker stack deploy -c docker-stack.yml unified
```

---

### Option 3: Hot Code Updates (ADVANCED - 2 minutes)
For minor Python code changes without full rebuild:

```bash
# 1. Get running container ID
CONTAINER=$(docker ps | grep unified_api | awk '{print $1}' | head -1)

# 2. Copy changed file into container
docker cp app/services/ai_strategy_suite.py $CONTAINER:/app/app/services/

# 3. Restart the service
docker service update --force unified_api
```

---

## When You MUST Rebuild

Only rebuild Docker when:
- Adding NEW Python dependencies (requirements.txt)
- Changing Dockerfile
- Adding NEW files/folders
- Updating system packages (apt-get)

---

## Common Quick Changes

### Reduce Cost Further (No Rebuild)
```sql
-- Scan every 30min instead of 15min
UPDATE smartflow_config SET ai_only_scan_interval = 1800;

-- Reduce to 2 instruments per user
UPDATE smartflow_config SET ai_only_instruments = '["MES", "XAUUSD"]' WHERE id = 1;
UPDATE smartflow_config SET ai_only_instruments = '["US30", "XAUUSD"]' WHERE id = 2;

-- Turn off AI-only mode entirely
UPDATE smartflow_config SET enable_ai_only_mode = false;
```

### Make Day Trading More Aggressive (No Rebuild)
```sql
-- Lower thresholds for more signals
UPDATE smartflow_config SET buy_threshold = 4.0, sell_threshold = -4.0;

-- Faster scans
UPDATE smartflow_config SET ai_only_scan_interval = 600;  -- 10min

-- Add more instruments
UPDATE smartflow_config SET ai_only_instruments = '["MES", "NQ", "RTY", "XAUUSD", "BTCUSD"]';
```

### Test Different Settings (No Rebuild)
```sql
-- Try very conservative (fewer, higher quality signals)
UPDATE smartflow_config SET 
    buy_threshold = 8.0, 
    sell_threshold = -8.0,
    min_confidence_score = 85;

-- Try very aggressive (more signals, lower quality)
UPDATE smartflow_config SET 
    buy_threshold = 3.0, 
    sell_threshold = -3.0,
    min_confidence_score = 60;
```

---

## Apply Changes
After any database change:
```bash
docker service update --force unified_api
# Wait 30 seconds for service to restart
```

Check if it worked:
```bash
docker service logs unified_api --tail 50 | grep -i "smartflow\|initialized"
```

---

## Pro Tips

1. **Test in staging first**: Make changes on one user account (id=2) before applying to both
2. **Monitor costs**: Check Anthropic dashboard after each change
3. **Document changes**: Keep notes of what settings work best
4. **Rollback quickly**: Keep a backup of working settings

