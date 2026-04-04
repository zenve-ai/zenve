import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zenve.api.lifespan import lifespan
from zenve.api.routes import auth_router, core_router

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
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


def main():
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    if reload:
        uvicorn.run("zenve.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
