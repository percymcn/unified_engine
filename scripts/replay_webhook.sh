#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: BROKER=projectx USER_ID=1 WEBHOOK_KEY=... BASE=http://localhost:18765 bash scripts/replay_webhook.sh path/to/payload.json"
  exit 1
fi

payload_file="$1"
BASE="${BASE:-http://localhost:18765}"
BROKER="${BROKER:-projectx}"
USER_ID="${USER_ID:-1}"
WEBHOOK_KEY="${WEBHOOK_KEY:-}"

if [[ -z "$WEBHOOK_KEY" ]]; then
  echo "WEBHOOK_KEY is required"
  exit 1
fi

auth_header=()
if [[ -n "${AUTH_HEADER:-}" ]]; then
  auth_header=(-H "${AUTH_HEADER}")
elif [[ -n "${TOKEN:-}" ]]; then
  auth_header=(-H "Authorization: Bearer ${TOKEN}")
fi

redact_json() {
  python - "$1" <<'PY'
import json
import sys

path = sys.argv[1]
raw = open(path, "r", encoding="utf-8").read().strip()
if not raw:
    print("<empty>")
    raise SystemExit(0)
try:
    data = json.loads(raw)
except Exception:
    print(raw)
    raise SystemExit(0)

redact_keys = {
    "access_token",
    "refresh_token",
    "api_key",
    "api_secret",
    "secret",
    "token",
    "webhook_key",
    "authorization",
    "auth",
}

def scrub(obj):
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            if key.lower() in redact_keys:
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = scrub(value)
        return cleaned
    if isinstance(obj, list):
        return [scrub(value) for value in obj]
    return obj

print(json.dumps(scrub(data), indent=2, sort_keys=True))
PY
}

post_url="${BASE}/api/v1/webhooks/incoming?broker=${BROKER}&user=${USER_ID}&key=${WEBHOOK_KEY}"
resp_file=$(mktemp)
status=$(curl -s -o "$resp_file" -w "%{http_code}" -H "Content-Type: application/json" "${auth_header[@]}" --data "@${payload_file}" "$post_url")

echo "Webhook POST: ${post_url}"
echo "HTTP ${status}"
redact_json "$resp_file"

positions_url="${BASE}/api/v1/dashboard/positions"
pos_file=$(mktemp)
pos_status=$(curl -s -o "$pos_file" -w "%{http_code}" "${auth_header[@]}" "$positions_url")

echo "Positions GET: ${positions_url}"
echo "HTTP ${pos_status}"
redact_json "$pos_file"

rm -f "$resp_file" "$pos_file"
