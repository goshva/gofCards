"""Entry point for hosting platforms that start the app by running a script.

The application package lives in `backend/`, so that directory is put on the
import path before the app is imported. Running this file is equivalent to:

    uvicorn app.main:app --host 0.0.0.0 --port 80 --app-dir backend
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    import uvicorn

    # Amvera exposes the container port as PORT; 80 matches containerPort in
    # amvera.yaml and is the default when the variable is absent
    port = int(os.getenv("PORT", "80"))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        app_dir=str(BACKEND_DIR),
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
