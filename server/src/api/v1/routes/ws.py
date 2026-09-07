from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.services.websocket_manager import connection_manager

router = APIRouter(prefix="/ws", tags=["WebSockets"])

@router.websocket("/ws/{facility_id}")
async def facility_ws(websocket: WebSocket, facility_id: str):
    await connection_manager.connect(websocket, facility_id)
    try:
        while True:
            await websocket.receive_text()  # keepalive/pings from client
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, facility_id)
