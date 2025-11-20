"""Base platform abstraction."""
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List


class PlatformBase(ABC):
    """Abstract base for platform-specific operations."""

    # Subclasses override these
    IDLE_COMMANDS: List[List[str]] = []
    SCREEN_STATE_COMMAND: List[str] = []
    WINDOW_COMMANDS: Optional[Dict[str, List[str]]] = None
    SUSPEND_COMMAND: List[str] = ["systemctl", "suspend", "--check-inhibitors=no"]
    SCREEN_OFF_COMMAND: Optional[List[str]] = None
    LOCK_COMMAND: Optional[List[str]] = None

    @abstractmethod
    def get_idle_seconds(self) -> float:
        """Return current idle time in seconds."""
        pass

    @abstractmethod
    def is_screen_on(self) -> bool:
        """Return True if display is powered on."""
        pass

    @abstractmethod
    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Get active window info for app tracking."""
        pass

    def suspend(self) -> bool:
        """Suspend system."""
        return self._run_command(self.SUSPEND_COMMAND)

    def screen_off(self) -> bool:
        """Turn off screen."""
        if not self.SCREEN_OFF_COMMAND:
            return False
        return self._run_command(self.SCREEN_OFF_COMMAND)

    def lock_screen(self) -> bool:
        """Lock screen."""
        if not self.LOCK_COMMAND:
            return False
        return self._run_command(self.LOCK_COMMAND)

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name for logging."""
        pass

    @property
    @abstractmethod
    def supports_window_tracking(self) -> bool:
        """Whether platform supports window tracking."""
        pass

    # Shared helpers
    def _check_command(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _run_command(self, cmd: List[str], check: bool = False) -> bool:
        """
        Execute command, return success.
        Does NOT actually run if check=True (for capability testing).
        """
        if check:
            # Only verify first command exists
            return self._check_command(cmd[0])
        try:
            subprocess.run(cmd, check=False, capture_output=True)
            return True
        except FileNotFoundError:
            return False

    def _is_x11(self) -> bool:
        """Check if running on X11."""
        import os
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        return session_type == "x11" or os.environ.get("DISPLAY") is not None
