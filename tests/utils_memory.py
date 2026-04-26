import os
import psutil
import threading
import time
import resource
from dataclasses import dataclass
from typing import Optional, Self, TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """Immutable result of a memory tracking session."""

    peak_rss_bytes: int

    @property
    def peak_rss_mb(self) -> float:
        """Peak Resident Set Size in Megabytes."""
        return self.peak_rss_bytes / (1024 * 1024)


class MemoryTracker:
    """
    Tracks peak RSS memory usage using a background polling thread and OS-level High Water Mark.

    This tracker captures both Python allocations and native allocations from Rust/C extensions.
    """

    def __init__(self, interval: float = 0.05) -> None:
        self.interval = interval
        self._peak_rss: int = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._process = psutil.Process(os.getpid())
        self._result: Optional[MemoryResult] = None

    def _track(self) -> None:
        """Polling loop executed in a background thread."""
        while not self._stop_event.is_set():
            try:
                current_rss = self._process.memory_info().rss
                with self._lock:
                    if current_rss > self._peak_rss:
                        self._peak_rss = current_rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(self.interval)

    def start(self) -> None:
        """Starts the background tracking thread."""
        self._peak_rss = self._process.memory_info().rss
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._track, daemon=True)
        self._thread.start()

    def stop(self) -> MemoryResult:
        """
        Stops the tracking thread and returns the peak RSS observed.

        Also incorporates resource.getrusage for the OS-level peak (High Water Mark).
        """
        self._stop_event.set()
        if self._thread:
            self._thread.join()

        # Cross-verify with OS-level maximum RSS (High Water Mark)
        # Note: on Linux, ru_maxrss is in kilobytes.
        os_peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        os_peak_bytes = os_peak_kb * 1024

        with self._lock:
            final_peak = max(self._peak_rss, os_peak_bytes)
            self._result = MemoryResult(peak_rss_bytes=final_peak)

        return self._result

    @property
    def result(self) -> MemoryResult:
        """Returns the result of the tracking session. Must be called after stop() or __exit__."""
        if self._result is None:
            raise RuntimeError(
                "MemoryTracker result is not available. Did you stop the tracker?"
            )
        return self._result

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional["TracebackType"],
    ) -> None:
        self.stop()
