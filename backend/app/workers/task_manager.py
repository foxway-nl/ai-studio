"""Asynchrone achtergrondtaak manager met SSE voortgang.

Singleton die asyncio taken beheert en voortgang streamt
via Server-Sent Events naar het frontend.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Coroutine, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Houdt de status bij van één achtergrondtaak."""

    id: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    current_step: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _asyncio_task: Optional[asyncio.Task] = field(default=None, repr=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def to_dict(self) -> dict:
        status_val = self.status.value
        if self.status == TaskStatus.COMPLETE:
            status_val = "completed"
        elif self.status in (TaskStatus.ERROR, TaskStatus.CANCELLED):
            status_val = "failed"
        elif self.status == TaskStatus.RUNNING:
            status_val = "running"

        return {
            "task_id": self.id,
            "status": status_val,
            "progress": round(self.progress, 4),
            "current_step": self.current_step,
            "step": self.current_step,
            "message": self.current_step or (self.error if self.error else ""),
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TaskManager:
    """Singleton achtergrondtaak manager.

    Beheert asyncio taken, houdt voortgang bij en biedt SSE streaming.
    """

    _instance: Optional["TaskManager"] = None

    def __new__(cls) -> "TaskManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: dict[str, TaskInfo] = {}
        return cls._instance

    @property
    def tasks(self) -> dict[str, TaskInfo]:
        return self._tasks

    def start_task(self, task_id: str, coroutine: Coroutine) -> TaskInfo:
        """Start een achtergrondtaak en volg de voortgang.

        Args:
            task_id: Unieke identificatie voor de taak.
            coroutine: De async functie die uitgevoerd moet worden.

        Returns:
            TaskInfo met de huidige status.
        """
        if task_id in self._tasks:
            existing = self._tasks[task_id]
            if existing.status in (TaskStatus.RUNNING, TaskStatus.QUEUED):
                logger.warning("Taak %s is al actief, wordt overgeslagen.", task_id)
                return existing

        info = TaskInfo(id=task_id)
        self._tasks[task_id] = info

        async def _wrapper() -> None:
            info.status = TaskStatus.RUNNING
            info.started_at = datetime.now(timezone.utc)
            info._event.set()
            info._event.clear()
            try:
                result = await coroutine
                info.result = result
                info.status = TaskStatus.COMPLETE
                info.progress = 1.0
                info.current_step = "Klaar"
            except asyncio.CancelledError:
                info.status = TaskStatus.CANCELLED
                info.error = "Taak geannuleerd"
                logger.info("Taak %s is geannuleerd.", task_id)
            except Exception as exc:
                info.status = TaskStatus.ERROR
                info.error = str(exc)
                logger.exception("Taak %s mislukt: %s", task_id, exc)
            finally:
                info.completed_at = datetime.now(timezone.utc)
                info._event.set()

        info._asyncio_task = asyncio.create_task(_wrapper(), name=f"task-{task_id}")
        return info

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Haal de huidige status op van een taak."""
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Annuleer een lopende taak.

        Returns:
            True als de taak succesvol is geannuleerd, anders False.
        """
        info = self._tasks.get(task_id)
        if info is None:
            return False
        if info._asyncio_task and not info._asyncio_task.done():
            info._asyncio_task.cancel()
            return True
        return False

    def update_progress(self, task_id: str, progress: float, step: str = "") -> None:
        """Update de voortgang van een taak (thread-safe via event loop).

        Args:
            task_id: ID van de taak.
            progress: Voortgang als float 0.0 – 1.0.
            step: Beschrijving van de huidige stap.
        """
        info = self._tasks.get(task_id)
        if info is None:
            return
        info.progress = max(0.0, min(1.0, progress))
        if step:
            info.current_step = step
        # Signal wachtende SSE clients
        info._event.set()
        info._event.clear()

    async def event_generator(self, task_id: str) -> AsyncGenerator[str, None]:
        """Async generator die SSE events yieldt voor een taak.

        Yields:
            SSE-geformatteerde strings met taakstatus updates.
        """
        info = self._tasks.get(task_id)
        if info is None:
            yield f"data: {json.dumps({'error': 'Taak niet gevonden', 'task_id': task_id})}\n\n"
            return

        # Stuur de initiële status
        yield f"data: {json.dumps(info.to_dict())}\n\n"

        while info.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
            try:
                await asyncio.wait_for(info._event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass  # Heartbeat – stuur opnieuw de huidige status
            yield f"data: {json.dumps(info.to_dict())}\n\n"

        # Stuur de eindstatus
        yield f"data: {json.dumps(info.to_dict())}\n\n"

    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Verwijder voltooide taken ouder dan max_age_seconds.

        Returns:
            Aantal verwijderde taken.
        """
        now = datetime.now(timezone.utc)
        to_remove = []
        for task_id, info in self._tasks.items():
            if info.status in (TaskStatus.COMPLETE, TaskStatus.ERROR, TaskStatus.CANCELLED):
                if info.completed_at and (now - info.completed_at).total_seconds() > max_age_seconds:
                    to_remove.append(task_id)
        for task_id in to_remove:
            del self._tasks[task_id]
        return len(to_remove)


# Globale singleton instantie
task_manager = TaskManager()
