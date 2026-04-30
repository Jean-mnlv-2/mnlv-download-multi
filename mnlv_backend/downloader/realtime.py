import hashlib
import json
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from .models import DownloadTask


class TaskRealtimeNotifier:
    """
    Source unique des événements temps réel (WebSocket).

    Objectifs :
    - schéma stable
    - throttle (2-4 updates/sec max)
    - déduplication (n'envoie que si changement significatif)
    """

    def __init__(self, max_updates_per_sec: float = 4.0):
        self.channel_layer = get_channel_layer()
        self.min_interval_s = 1.0 / max(1.0, max_updates_per_sec)
        self._last_sent_at: Dict[str, float] = {}
        self._last_payload_hash: Dict[str, str] = {}

    def _group_name(self, user_id: int) -> str:
        return f"user_{user_id}_tasks"

    def _result_file_url(self, task: DownloadTask) -> Optional[str]:
        if not task.result_file:
            return None
        try:
            return task.result_file.url
        except Exception:
            # peut échouer si storage non prêt
            return None

    def _track_payload(self, task: DownloadTask) -> Optional[dict]:
        if not task.track:
            return None
        return {
            "title": task.track.title,
            "artist": task.track.artist,
            "album": task.track.album,
            "cover_url": task.track.cover_url,
        }

    def _payload(self, task: DownloadTask, *, message: Optional[str], speed: Optional[str], eta: Optional[str]) -> dict:
        return {
            "task_id": str(task.id),
            "status": task.status,
            "progress": int(task.progress or 0),
            "message": message,
            "speed": speed,
            "eta": eta,
            "error_message": task.error_message,
            "error_code": task.error_code,
            "result_file_url": self._result_file_url(task),
            "track": self._track_payload(task),
        }

    def _hash_payload(self, payload: dict) -> str:
        # stable hash, ignore ordering
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def send(
        self,
        task: DownloadTask,
        *,
        message: Optional[str] = None,
        speed: Optional[str] = None,
        eta: Optional[str] = None,
        force: bool = False,
    ) -> None:
        if not task.user_id:
            return

        now = time.time()
        task_key = str(task.id)

        payload = self._payload(task, message=message, speed=speed, eta=eta)
        payload_hash = self._hash_payload(payload)

        last_hash = self._last_payload_hash.get(task_key)
        last_sent_at = self._last_sent_at.get(task_key, 0.0)

        throttled = (now - last_sent_at) < self.min_interval_s
        unchanged = last_hash == payload_hash

        if not force and (throttled or unchanged):
            return

        self._last_payload_hash[task_key] = payload_hash
        self._last_sent_at[task_key] = now

        async_to_sync(self.channel_layer.group_send)(
            self._group_name(task.user_id),
            {"type": "task_update", "data": payload},
        )


default_notifier = TaskRealtimeNotifier(
    max_updates_per_sec=float(getattr(settings, "TASK_WS_MAX_UPDATES_PER_SEC", 4.0))
)

