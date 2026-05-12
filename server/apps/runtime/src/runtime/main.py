import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from runtime.lifespan import lifespan
from runtime.models.errors import (
    AuthError,
    ConflictError,
    ExternalError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ZenveError,
)
from runtime.routes import core_router, run_router, skill_router, snapshot_router, template_router, workspace_router
from zenve_engine.github.client import GitHubError

app = FastAPI(lifespan=lifespan)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> None:
    raise HTTPException(status_code=404, detail=exc.message)


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> None:
    raise HTTPException(status_code=409, detail=exc.message)


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> None:
    raise HTTPException(status_code=422, detail=exc.message)


@app.exception_handler(ExternalError)
async def external_handler(request: Request, exc: ExternalError) -> None:
    raise HTTPException(status_code=502, detail=exc.message)


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> None:
    raise HTTPException(status_code=429, detail=exc.message)


@app.exception_handler(AuthError)
async def auth_handler(request: Request, exc: AuthError) -> None:
    raise HTTPException(status_code=403, detail=exc.message)


@app.exception_handler(ZenveError)
async def zenve_handler(request: Request, exc: ZenveError) -> None:
    raise HTTPException(status_code=500, detail=exc.message)


@app.exception_handler(GitHubError)
async def github_error_handler(request: Request, exc: GitHubError) -> None:
    raise HTTPException(status_code=502, detail=f"GitHub API error ({exc.status_code}): {exc.body}")


origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:7878",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Disposition"],
)

app.include_router(core_router)
app.include_router(workspace_router)
app.include_router(run_router)
app.include_router(snapshot_router)
app.include_router(template_router)
app.include_router(skill_router)

log_file = Path.home() / ".zenve" / "runtime.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file),
    ],
)

logger = logging.getLogger(__name__)


def main():
    reload = os.getenv("RUNTIME_RELOAD", "false").lower() == "true"
    if reload:
        uvicorn.run("runtime.main:app", host="0.0.0.0", port=8001, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
