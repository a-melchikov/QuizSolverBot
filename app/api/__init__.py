from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

STATIC_DIR = Path(__file__).parent.parent / "webapp" / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="QuizSolverBot Mini App", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
