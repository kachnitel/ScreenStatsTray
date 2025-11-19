"""Base platform abstraction."""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class PlatformBase(ABC):
    """Abstract base for platform-specific operations."""

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
        """
        Get active window info for app tracking.
        
        Returns:
            (app_name, window_title) or None if unavailable
        """
        pass

    @abstractmethod
    def suspend(self) -> bool:
        """
        Suspend system.
        
        Returns:
            True if command available, False otherwise
        """
        pass

    @abstractmethod
    def screen_off(self) -> bool:
        """
        Turn off screen.
        
        Returns:
            True if command available, False otherwise
        """
        pass

    @abstractmethod
    def lock_screen(self) -> bool:
        """
        Lock screen.
        
        Returns:
            True if command available, False otherwise
        """
        pass

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

