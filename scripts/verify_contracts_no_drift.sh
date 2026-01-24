#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8765}"

tmp="/tmp/contracts.json"
curl -fsS "$API_URL/api/v1/brokers/contracts" -o "$tmp"

python3 - <<'PY'
import json, sys, pathlib, re

contracts=json.load(open("/tmp/contracts.json"))
brokers=contracts["brokers"]

# UI schema file
ui_path=pathlib.Path("ui-next/src/lib/brokers/credentialSchemas.ts")
txt=ui_path.read_text(encoding="utf-8")

# crude but effective checks:
# 1) every contract field name should appear in UI schemas file
missing=[]
for bid,b in brokers.items():
    for f in b.get("fields",[]):
        name=f.get("name")
        if name and name not in txt:
            missing.append((bid,name))

# 2) known removed drift fields should NOT exist
for bad in ["environment_url"]:
    if bad in txt:
        print(f"❌ Drift: UI still contains removed field: {bad}")
        sys.exit(1)

if missing:
    print("❌ Drift: UI is missing contract field(s):")
    for bid,name in missing[:50]:
        print(f"  - {bid}: {name}")
    sys.exit(1)

print("✅ Contracts/UI drift check passed")
PY
