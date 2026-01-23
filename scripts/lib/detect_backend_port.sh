#!/bin/bash
# detect_backend_port.sh - Auto-detect running backend port
# Used by verification scripts to find the correct backend URL

detect_backend_port() {
    # If API_URL is explicitly set, use it
    if [ -n "$API_URL" ]; then
        echo "$API_URL"
        return 0
    fi

    # Common ports to check
    PORTS=(8765 8000 8080 3000 5000)
    
    for port in "${PORTS[@]}"; do
        # Try /health endpoint first (faster)
        if curl -s -f --max-time 2 "http://localhost:$port/health" > /dev/null 2>&1; then
            echo "http://localhost:$port"
            return 0
        fi
        # Fallback to /docs endpoint
        if curl -s -f --max-time 2 "http://localhost:$port/docs" > /dev/null 2>&1; then
            echo "http://localhost:$port"
            return 0
        fi
    done
    
    # Default fallback
    echo "http://localhost:8765"
    return 1
}

# If script is executed directly, output the detected URL
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    detect_backend_port
fi
