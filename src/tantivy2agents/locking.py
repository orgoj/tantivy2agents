"""Cross-process locking for index rebuilds and searches.

Several agents share one installed CLI and run ``tantivy2agents search``
concurrently against the same project. Without coordination every process that
finds a stale or unopenable index starts its own forced rebuild, and those
rebuilds delete the index directory from under each other.

The lock is an operating-system lock on a lock file, taken through
``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows. Both are released
by the operating system when the process exits, even after a crash or a kill,
so a lock can never be left behind and block everyone else. That is the reason
this uses OS locks rather than a plain "create a lock file" scheme, which would
need stale-lock detection and lock stealing to survive a crashed rebuild.

The lock is exclusive only. Windows has no shared-mode equivalent, and one
behavior on every platform is worth more here than parallel searches: a search
holds the lock just long enough to open the index and run the query.

The lock file lives next to the index directory, never inside it, so a rebuild
that replaces ``idx/`` cannot remove the lock file itself.
"""

import logging
import os
import socket
import sys
import time
from contextlib import contextmanager
from typing import Optional

from .exceptions import CLIError

logger = logging.getLogger(__name__)

LOCK_FILENAME = "index.lock"
DEFAULT_LOCK_TIMEOUT = 120.0
LOCK_POLL_INTERVAL = 0.02

# Byte 0 of the lock file is the lock itself. Windows byte-range locks are
# mandatory, so the human-readable holder info starts at byte 1 where other
# processes may still read it.
_LOCK_BYTE = 0
_INFO_OFFSET = 1

if sys.platform == "win32":  # pragma: no cover - exercised on Windows only
    import msvcrt

    def _try_lock(fd: int) -> None:
        """Take the lock, or raise OSError when another process holds it."""
        os.lseek(fd, _LOCK_BYTE, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(fd: int) -> None:
        os.lseek(fd, _LOCK_BYTE, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> None:
        """Take the lock, or raise OSError when another process holds it."""
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class IndexLockTimeoutError(CLIError):
    """Waiting for the index lock exceeded the configured timeout."""

    def __init__(self, lock_path: str, timeout: float, holder: Optional[str] = None):
        context = {"lock_path": lock_path}
        if holder:
            context["held_by"] = holder

        super().__init__(
            message=f"Timed out after {timeout:g}s waiting for the index lock",
            hint=(
                "Another tantivy2agents process is rebuilding or reading the "
                "index. Retry shortly, or raise TANTIVY2AGENTS_LOCK_TIMEOUT."
            ),
            context=context,
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
    """Reentrant exclusive lock shared by all processes on one index.

    Reentrant acquisition inside the same process is a no-op, which lets a
    search that already holds the lock call ``index_command`` without
    deadlocking against itself.
    """

    def __init__(self, lock_path: str) -> None:
        self.lock_path = lock_path
        self._fd: Optional[int] = None
        self._depth = 0

    @property
    def held(self) -> bool:
        """True while this process holds the lock."""
        return self._depth > 0

    @contextmanager
    def acquire(self, timeout: Optional[float] = None):
        """Hold the lock for the duration of the ``with`` block."""
        if self._depth:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return

        wait = default_lock_timeout() if timeout is None else timeout
        fd = self._open_lock_file()
        try:
            self._wait_for_lock(fd, wait)
            self._write_holder_info(fd)
        except BaseException:
            os.close(fd)
            raise

        self._fd = fd
        self._depth = 1
        try:
            yield
        finally:
            self._depth = 0
            self._fd = None
            try:
                _unlock(fd)
            finally:
                os.close(fd)

    def _open_lock_file(self) -> int:
        parent = os.path.dirname(self.lock_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        return os.open(self.lock_path, flags, 0o644)

    def _wait_for_lock(self, fd: int, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                _try_lock(fd)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise IndexLockTimeoutError(
                        self.lock_path, timeout, self._read_holder_info()
                    ) from None
                time.sleep(LOCK_POLL_INTERVAL)

    def _write_holder_info(self, fd: int) -> None:
        """Record who holds the lock, for diagnostics only."""
        info = f"pid={os.getpid()} host={socket.gethostname()} since={time.time():.0f}"
        try:
            os.lseek(fd, _INFO_OFFSET, os.SEEK_SET)
            os.write(fd, info.encode("utf-8", "replace"))
            os.truncate(fd, _INFO_OFFSET + len(info))
        except OSError as e:
            logger.debug("Could not record index lock holder: %s", e)

    def _read_holder_info(self) -> Optional[str]:
        """Best-effort read of the current holder's diagnostics line."""
        try:
            with open(self.lock_path, "rb") as f:
                f.seek(_INFO_OFFSET)
                raw = f.read(256)
        except OSError:
            return None
        text = raw.decode("utf-8", "replace").strip("\x00").strip()
        return text or None
