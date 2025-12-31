#!/usr/bin/env python3
"""
Backend Server Launcher with Dynamic Port Finding
Finds a free port starting from 8000 and launches uvicorn
"""
import socket
import sys
import os
import subprocess
from pathlib import Path

def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Find a free port starting from start_port
    
    Args:
        start_port: Port to start checking from
        max_attempts: Maximum number of ports to check
        
    Returns:
        First available port number
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")

def get_port_from_env() -> int:
    """Get port from environment variable or return None"""
    port_str = os.getenv('PORT')
    if port_str:
        try:
            return int(port_str)
        except ValueError:
            print(f"Warning: Invalid PORT environment variable: {port_str}")
    return None

def main():
    """Main entry point"""
    # Get port from environment or find free port
    port = get_port_from_env()
    
    if port is None:
        # Find free port starting from 8000
        port = find_free_port(8000)
        print(f"🔍 Found free port: {port}")
    else:
        # Check if specified port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', port))
                print(f"✅ Using port from environment: {port}")
        except OSError:
            print(f"⚠️  Port {port} from environment is not available, finding free port...")
            port = find_free_port(8000)
            print(f"🔍 Found free port: {port}")
    
    # Set environment variable for the app to use
    os.environ['PORT'] = str(port)
    
    # Get project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Build uvicorn command
    host = os.getenv('HOST', '0.0.0.0')
    reload = os.getenv('RELOAD', 'true').lower() == 'true'
    
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--host', host,
        '--port', str(port),
    ]
    
    if reload:
        cmd.append('--reload')
    
    # Print startup info
    print(f"\n🚀 Starting Unified Trading Engine Backend")
    print(f"📍 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"💚 Health: http://{host}:{port}/health")
    print(f"\n💡 Tip: Set PORT environment variable to use a specific port")
    print(f"💡 Tip: Set RELOAD=false to disable auto-reload in production\n")
    
    # Change to project root directory
    os.chdir(project_root)
    
    # Run uvicorn
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
