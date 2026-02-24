#!/bin/bash
# Control script for Unified Monitor Service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/monitor_and_heal.py"
PID_FILE="/tmp/unified-monitor.pid"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Monitor is already running (PID: $PID)"
                exit 1
            fi
        fi

        echo "Starting Unified Monitor..."
        nohup python3 "$MONITOR_SCRIPT" > "$SCRIPT_DIR/../logs/monitor/monitor_stdout.log" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Monitor started (PID: $(cat $PID_FILE))"
        echo "View logs: tail -f ~/unified_engine/logs/monitor/monitor.log"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "Monitor is not running"
            exit 1
        fi

        PID=$(cat "$PID_FILE")
        echo "Stopping monitor (PID: $PID)..."
        kill "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "Monitor stopped"
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Monitor is running (PID: $PID)"
                echo ""
                echo "Last 10 log entries:"
                tail -10 ~/unified_engine/logs/monitor/monitor.log
                exit 0
            else
                echo "Monitor is not running (stale PID file)"
                rm -f "$PID_FILE"
                exit 1
            fi
        else
            echo "Monitor is not running"
            exit 1
        fi
        ;;

    logs)
        tail -f ~/unified_engine/logs/monitor/monitor.log
        ;;

    install-systemd)
        if [ "$EUID" -ne 0 ]; then
            echo "Please run with sudo to install systemd service"
            exit 1
        fi
        bash "$SCRIPT_DIR/install_monitor.sh"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs|install-systemd}"
        echo ""
        echo "Commands:"
        echo "  start            - Start the monitor in background"
        echo "  stop             - Stop the monitor"
        echo "  restart          - Restart the monitor"
        echo "  status           - Check monitor status"
        echo "  logs             - View monitor logs (live)"
        echo "  install-systemd  - Install as systemd service (requires sudo)"
        exit 1
        ;;
esac
