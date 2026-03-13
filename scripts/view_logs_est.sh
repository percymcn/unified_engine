#!/bin/bash
# View Docker logs with timestamps converted to EST
# Usage: ./view_logs_est.sh [service_name] [options]

SERVICE=${1:-unified_api}
TAIL_LINES=${2:-50}

echo "==================================="
echo "Docker Logs - $SERVICE (EST Times)"
echo "==================================="
echo ""

# Get logs with timestamps
docker service logs $SERVICE --tail $TAIL_LINES --timestamps 2>&1 | while IFS= read -r line; do
    # Extract timestamp (format: 2026-03-13T04:52:07.946378Z)
    if [[ $line =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}) ]]; then
        UTC_TIME="${BASH_REMATCH[1]}"

        # Convert to EST using date command
        # Remove 'T' and add UTC indicator
        UTC_FORMAT="${UTC_TIME/T/ }Z"

        # Convert to EST (macOS and Linux compatible)
        if command -v gdate &> /dev/null; then
            # macOS with GNU date
            EST_TIME=$(gdate -d "$UTC_FORMAT" '+%m/%d %I:%M:%S %p %Z' 2>/dev/null || echo "$UTC_TIME")
        else
            # Linux date
            EST_TIME=$(TZ="America/New_York" date -d "$UTC_FORMAT" '+%m/%d %I:%M:%S %p %Z' 2>/dev/null || echo "$UTC_TIME")
        fi

        # Replace timestamp in line
        echo "$line" | sed "s/$UTC_TIME/$EST_TIME/"
    else
        # No timestamp, print as-is
        echo "$line"
    fi
done

echo ""
echo "Usage: $0 [service_name] [tail_lines]"
echo "Example: $0 unified_api 100"
echo ""
echo "Available services:"
docker service ls --format "  - {{.Name}}"
