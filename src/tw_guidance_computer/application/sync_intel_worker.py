"""Background sync worker for shared intel."""

from __future__ import annotations

import time
from typing import final

from tw_guidance_computer.application.pull_intel import PullIntel
from tw_guidance_computer.application.push_intel import PushIntel
from tw_guidance_computer.domain.exceptions import (
    IntelConnectError,
    IntelDataError,
    IntelKeyError,
    IntelTransferError,
)
from tw_guidance_computer.domain.models import IntelConfig, SyncStatus

_SLEEP_TICK = 1.0


@final
class SyncIntelWorker:
    """Encapsulates the background sync algorithm for the HUD thread."""

    def __init__(self, push: PushIntel, pull: PullIntel, config: IntelConfig) -> None:
        """Initialize with push/pull use cases and sync configuration.

        Args:
            push: Use case for pushing local intel to the server.
            pull: Use case for pulling remote intel from the server.
            config: Intel sync configuration (interval, budget).
        """
        self._push = push
        self._pull = pull
        self._config = config
        self._status: SyncStatus = SyncStatus()
        self._sync_counter: int = 0
        self._stop_requested: bool = False
        self._shutdown_requested: bool = False

    def get_status(self) -> SyncStatus:
        """Return current sync status (thread-safe read)."""
        return self._status

    def request_shutdown(self) -> None:
        """Request graceful shutdown with a final push."""
        self._shutdown_requested = True

    def request_stop(self) -> None:
        """Force stop immediately (second ctrl+c)."""
        self._stop_requested = True

    def run(self) -> None:
        """Main sync loop: pull on startup, then push+pull on interval until stopped."""
        # Startup pull
        if self._should_exit():
            self._do_shutdown()
            return
        self._do_pull()

        while not self._should_exit():
            self._interruptible_sleep(self._config.sync_interval)
            if self._should_exit():
                break
            self._do_push()
            if self._should_exit():
                break
            self._do_pull()
            self._sync_counter += 1

        if self._shutdown_requested and not self._stop_requested:
            self._do_shutdown()

    def _should_exit(self) -> bool:
        """Check if stop or shutdown has been requested."""
        return self._stop_requested or self._shutdown_requested

    def _interruptible_sleep(self, seconds: int) -> None:
        """Sleep in short ticks so shutdown/stop requests are responsive."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._should_exit():
                return
            remaining = deadline - time.monotonic()
            time.sleep(min(_SLEEP_TICK, max(0.0, remaining)))

    def _do_push(self) -> None:
        """Execute a push cycle, mapping errors to status codes."""
        try:
            self._push.execute()
            self._status = SyncStatus(last_error=None, shutdown_status=self._status.shutdown_status)
        except IntelKeyError:
            self._status = SyncStatus(last_error="E66", shutdown_status=self._status.shutdown_status)
        except IntelConnectError as e:
            code = "E31" if _is_auth_error(e) else "E24"
            self._status = SyncStatus(last_error=code, shutdown_status=self._status.shutdown_status)
        except IntelDataError:
            self._status = SyncStatus(last_error="E17", shutdown_status=self._status.shutdown_status)
        except IntelTransferError:
            self._status = SyncStatus(last_error="E38", shutdown_status=self._status.shutdown_status)

    def _do_pull(self) -> None:
        """Execute a pull cycle, mapping errors to status codes."""
        try:
            self._pull.execute(
                budget_seconds=float(self._config.sync_budget),
                offset=self._sync_counter,
            )
            self._status = SyncStatus(last_error=None, shutdown_status=self._status.shutdown_status)
        except IntelKeyError:
            self._status = SyncStatus(last_error="E66", shutdown_status=self._status.shutdown_status)
        except IntelConnectError as e:
            code = "E31" if _is_auth_error(e) else "E24"
            self._status = SyncStatus(last_error=code, shutdown_status=self._status.shutdown_status)
        except IntelDataError:
            self._status = SyncStatus(last_error="E52", shutdown_status=self._status.shutdown_status)
        except IntelTransferError:
            self._status = SyncStatus(last_error="E45", shutdown_status=self._status.shutdown_status)

    def _do_shutdown(self) -> None:
        """Execute the shutdown sequence: final push with status updates."""
        self._status = SyncStatus(last_error=self._status.last_error, shutdown_status="Exporting sectors...")
        try:
            self._push.execute()
            self._status = SyncStatus(last_error=None, shutdown_status="Done.")
        except (IntelConnectError, IntelTransferError, IntelDataError, IntelKeyError) as e:
            self._status = SyncStatus(
                last_error=self._status.last_error,
                shutdown_status=f"Push failed: {e}",
            )


def _is_auth_error(e: IntelConnectError) -> bool:
    """Detect auth errors by message content."""
    msg = str(e).lower()
    return "auth" in msg or "denied" in msg
