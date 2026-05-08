from fastapi import APIRouter

router = APIRouter(tags=["core"])


@router.get("/")
def root():
    return {"ok": True, "message": "zenve runtime is running", "version": "0.1.0"}


@router.get("/healthz")
def healthz():
    return {"ok": True, "service": "zenve-runtime", "version": "0.1.0"}
