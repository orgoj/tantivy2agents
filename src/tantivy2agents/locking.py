"""Cross-process locking for index rebuilds and searches.

Several agents share one installed CLI and run ``tantivy2agents search``
concurrently against the same project. Without coordination every process that
finds a stale or unopenable index starts its own forced rebuild, and those
rebuilds delete the index directory from under each other.

The lock lives next to the index directory (never inside it), so a rebuild that
replaces ``idx/`` cannot remove the lock file itself.
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Optional

from .exceptions import CLIError

try:  # pragma: no cover - exercised only on POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows and friends
    fcntl = None

logger = logging.getLogger(__name__)

LOCK_FILENAME = "index.lock"
DEFAULT_LOCK_TIMEOUT = 120.0
LOCK_POLL_INTERVAL = 0.02

EXCLUSIVE = "exclusive"
SHARED = "shared"


class IndexLockTimeoutError(CLIError):
    """Waiting for the index lock exceeded the configured timeout."""

    def __init__(self, lock_path: str, timeout: float, mode: str):
        super().__init__(
            message=f"Timed out after {timeout:g}s waiting for the index lock",
            hint=(
                "Another tantivy2agents process is rebuilding or reading the "
                "index. Retry shortly, or raise TANTIVY2AGENTS_LOCK_TIMEOUT."
            ),
            context={"lock_path": lock_path, "mode": mode},
        )


def default_lock_timeout() -> float:
    """Return the lock timeout, overridable via environment variable."""
    raw = os.getenv("TANTIVY2AGENTS_LOCK_TIMEOUT")
    if not raw:
        return DEFAULT_LOCK_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Ignoring invalid TANTIVY2AGENTS_LOCK_TIMEOUT=%r", raw)
        return DEFAULT_LOCK_TIMEOUT
    if value <= 0:
        logger.warning("Ignoring non-positive TANTIVY2AGENTS_LOCK_TIMEOUT=%r", raw)
        return DEFAULT_LOCK_TIMEOUT
    return value


class IndexLock:
    """Reentrant shared/exclusive lock shared by all processes on one index.

    Readers take :meth:`shared`, writers take :meth:`exclusive`. Reentrant
    acquisition inside the same process is a no-op, which lets a search that
    already holds the write lock call ``index_command`` without deadlocking.
    """

    def __init__(self, lock_path: str) -> None:
        self.lock_path = lock_path
        self._fd: Optional[int] = None
        self._mode: Optional[str] = None
        self._depth = 0

    @property
    def mode(self) -> Optional[str]:
        """Currently held mode, or None when this process holds nothing."""
        return self._mode

    def exclusive(self, timeout: Optional[float] = None):
        """Context manager holding the write lock."""
        return self._acquire(EXCLUSIVE, timeout)

    def shared(self, timeout: Optional[float] = None):
        """Context manager holding the read lock."""
        return self._acquire(SHARED, timeout)

    @contextmanager
    def _acquire(self, mode: str, timeout: Optional[float]):
        if self._depth:
            if mode == EXCLUSIVE and self._mode == SHARED:
                raise RuntimeError(
                    "Cannot upgrade a shared index lock to an exclusive one"
                )
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return

        if fcntl is None:  # pragma: no cover - non-POSIX fallback
            logger.debug("fcntl unavailable; index locking is disabled")
            self._mode = mode
            self._depth = 1
            try:
                yield
            finally:
                self._depth = 0
                self._mode = None
            return

        wait = default_lock_timeout() if timeout is None else timeout
        fd = self._open_lock_file()
        try:
            self._flock(fd, mode, wait)
        except BaseException:
            os.close(fd)
            raise

        self._fd = fd
        self._mode = mode
        self._depth = 1
        try:
            yield
        finally:
            self._depth = 0
            self._mode = None
            self._fd = None
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _open_lock_file(self) -> int:
        parent = os.path.dirname(self.lock_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o644)

    def _flock(self, fd: int, mode: str, timeout: float) -> None:
        flag = fcntl.LOCK_EX if mode == EXCLUSIVE else fcntl.LOCK_SH
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, flag | fcntl.LOCK_NB)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise IndexLockTimeoutError(self.lock_path, timeout, mode) from None
                time.sleep(LOCK_POLL_INTERVAL)
