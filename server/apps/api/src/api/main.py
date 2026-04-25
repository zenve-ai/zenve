import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from api.lifespan import lifespan
from api.routes import (
    agent_router,
    api_key_router,
    auth_router,
    core_router,
    github_router,
    project_router,
    template_router,
    ws_router,
)
from zenve_models.errors import (
    AuthError,
    ConflictError,
    ExternalError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ZenveError,
)

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


origins = [
    "http://localhost:5173",
    "http://localhost:5174",
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
app.include_router(auth_router)
app.include_router(github_router)
app.include_router(project_router)
app.include_router(api_key_router)
app.include_router(agent_router)
app.include_router(template_router)
app.include_router(ws_router)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    if reload:
        uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
