import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from api.config import get_settings
from api.db.database import get_db
from api.db.models import UserRecord
from api.services.membership import MembershipService
from api.services.workspace import WorkspaceService
from api.services.ws_manager import WebSocketManager
from api.utils.auth import ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/api/v1/workspaces/{workspace_id}/ws")
async def workspace_websocket(
    workspace_id: str,
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

    # Authorize workspace membership
    workspace_db_id: str | None = None
    db = next(get_db())
    try:
        user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
        if not user:
            await websocket.close(code=4001)
            return
        workspace = WorkspaceService(db).get_by_id_or_slug(workspace_id)
        MembershipService(db).require_membership(user.id, workspace.id)
        workspace_db_id = workspace.id
    except Exception:
        await websocket.close(code=4003)
        return
    finally:
        db.close()

    await ws_manager.connect(workspace_db_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error for workspace=%s user=%s", workspace_db_id, user_id)
    finally:
        ws_manager.disconnect(workspace_db_id, websocket)
