import asyncio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import jwt
from app.core.django_bridge import run_django
from app.core.security import decode_jwt_token

router = APIRouter(tags=["Realtime WebSocket"])


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str = Query(default="")):
    try:
        payload = decode_jwt_token(token, expected_type="access")
        user_id = str(payload.get("user_id") or "")
        if not user_id:
            await websocket.close(code=4001)
            return
    except jwt.PyJWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            def _fetch():
                from apps.notifications.models import NotificationMessage

                qs = NotificationMessage.objects.filter(recipient_id=user_id, is_read=False)
                latest = qs.order_by("-created_at")[:5]
                return {
                    "unread_count": qs.count(),
                    "latest": [
                        {
                            "id": str(n.id),
                            "title": n.title,
                            "body": n.body,
                            "created_at": n.created_at.isoformat(),
                        }
                        for n in latest
                    ],
                }

            snap = await run_django(_fetch)
            await websocket.send_json({"event": "notification_snapshot", "data": snap})
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return
