import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from zenve_config.settings import get_settings
from zenve_db.database import Session as DBSession
from zenve_db.models import UserRecord
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
from zenve_services.ws_manager import WebSocketManager
from zenve_utils.auth import ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/api/v1/projects/{org_id}/ws")
async def org_websocket(
    org_id: str,
    websocket: WebSocket,
    token: str = Query(...),
):
    ws_manager: WebSocketManager = websocket.app.state.ws_manager

    # Authenticate token
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    # Authorize org membership
    org_db_id: str | None = None
    db = DBSession()
    try:
        user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
        if not user:
            await websocket.close(code=4001)
            return
        org = ProjectService(db).get_by_id_or_slug(org_id)
        MembershipService(db).require_membership(user.id, org.id)
        org_db_id = org.id
    except Exception:
        await websocket.close(code=4003)
        return
    finally:
        db.close()

    await ws_manager.connect(org_db_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error for org=%s user=%s", org_db_id, user_id)
    finally:
        ws_manager.disconnect(org_db_id, websocket)
