#!/usr/bin/env python3
"""
Medicilon CRO Intelligence Platform — Launcher
Starts the FastAPI backend + serves the frontend.

Usage:
    python run.py              # Start server on port 8000
    python run.py --port 8080  # Custom port
    python run.py --reload     # Auto-reload on code changes
"""

import argparse
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medicilon CRO Intelligence Platform")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    args = parser.parse_args()

    import uvicorn
    import socket

    # Check if port is already in use
    def is_port_in_use(port, host="0.0.0.0"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host, port))
            s.close()
            return False
        except OSError:
            return True

    if is_port_in_use(args.port, args.host):
        print(f"\n[WARN] Port {args.port} is already in use!")
        print(f"  Try: python run.py --port {args.port + 1}")
        print(f"  Or kill the process: netstat -ano | findstr :{args.port}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Medicilon CRO Intelligence Platform")
    print(f"  http://localhost:{args.port}")
    print(f"  API docs: http://localhost:{args.port}/docs")
    print(f"{'='*60}\n")

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
