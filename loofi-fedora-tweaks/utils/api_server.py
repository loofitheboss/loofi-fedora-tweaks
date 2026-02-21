"""Loofi Web API server (FastAPI + Uvicorn)."""

import threading
from pathlib import Path
from typing import Optional

import uvicorn
from api.routes import executor as executor_routes
from api.routes import profiles as profiles_routes
from api.routes import system as system_routes
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from utils.auth import AuthManager


class APIServer:
    """FastAPI server wrapper to run in a background thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.app = self._create_app()
        self._thread: Optional[threading.Thread] = None

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Loofi Web API", version="20.0.0")
        # v29.0: CORS restricted to localhost (was wildcard)
        allowed_origins = [
            f"http://{self.host}:{self.port}",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

        # API routes
        app.include_router(system_routes.router, prefix="/api")
        app.include_router(executor_routes.router, prefix="/api")
        app.include_router(profiles_routes.router, prefix="/api")

        @app.post("/api/token")
        def issue_token(api_key: str = Form(...)):
            """Issue JWT token for valid API key (form-urlencoded)."""
            try:
                token = AuthManager.issue_token(api_key)
                return {"access_token": token, "token_type": "bearer"}
            except (RuntimeError, ValueError, OSError) as e:
                raise HTTPException(status_code=401, detail=str(e))

        @app.post("/api/key")
        def generate_key():
            api_key = AuthManager.generate_api_key()
            return {"api_key": api_key}

        # Static file serving
        web_dir = Path(__file__).parent.parent / "web"
        if web_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(web_dir / "assets")), name="assets")

            @app.get("/")
            def serve_index():
                return FileResponse(str(web_dir / "index.html"))

        return app

    def start(self) -> None:
        """Start the API server in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
