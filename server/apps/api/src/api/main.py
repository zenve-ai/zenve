import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.lifespan import lifespan
from api.routes import (
    agent_router,
    api_key_router,
    auth_router,
    core_router,
    github_router,
    preset_router,
    project_router,
    template_router,
    ws_router,
)

app = FastAPI(lifespan=lifespan)


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
app.include_router(preset_router)
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
