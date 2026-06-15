"""
Metabolomics Platform v0.3.0 — Launcher
=========================================
Usage:
    python run.py              Start web UI (http://localhost:8002)
    python run.py --gui        Start desktop GUI
    python run.py --port 9000  Start web UI on custom port
"""

import sys, os

def main():
    args = sys.argv[1:]
    if "--gui" in args or "-g" in args:
        print("Launching Desktop GUI...")
        from gui.main import main as gui_main
        gui_main()
    else:
        port = 8002
        for i, arg in enumerate(args):
            if arg in ("--port", "-p") and i + 1 < len(args):
                port = int(args[i + 1])
        os.environ["PORT"] = str(port)
        from backend.main import app
        import uvicorn
        print(f"\n  Metabolomics Platform v0.3.0")
        print(f"  Web UI: http://localhost:{port}")
        print(f"  API docs: http://localhost:{port}/docs\n")
        uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
