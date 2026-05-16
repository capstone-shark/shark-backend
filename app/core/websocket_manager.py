import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """포즈 데이터 실시간 스트리밍용 in-memory WebSocket 매니저
    """

    def __init__(self) -> None:
        # device_id -> set of WebSocket. None 키는 "모든 디바이스 구독"
        self._subscribers: dict[Optional[str], set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, device_id: Optional[str] = None) -> None:
        await ws.accept()
        async with self._lock:
            self._subscribers.setdefault(device_id, set()).add(ws)
        logger.info("WS connected (device_id=%s, total=%d)", device_id, self._count())

    async def disconnect(self, ws: WebSocket, device_id: Optional[str] = None) -> None:
        async with self._lock:
            bucket = self._subscribers.get(device_id)
            if bucket:
                bucket.discard(ws)
                if not bucket:
                    self._subscribers.pop(device_id, None)
        logger.info("WS disconnected (device_id=%s, total=%d)", device_id, self._count())

    async def broadcast(self, payload: dict, device_id: str) -> None:
        """해당 device_id 구독자 + 전체 구독자(None)에게 JSON 전송"""
        async with self._lock:
            targets = list(self._subscribers.get(device_id, set()) | self._subscribers.get(None, set()))

        if not targets:
            return

        dead: list[tuple[WebSocket, Optional[str]]] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                logger.warning("WS send failed — marking dead", exc_info=True)
                dead.append((ws, device_id))

        for ws, did in dead:
            await self.disconnect(ws, did)

    def _count(self) -> int:
        return sum(len(s) for s in self._subscribers.values())


manager = ConnectionManager()
