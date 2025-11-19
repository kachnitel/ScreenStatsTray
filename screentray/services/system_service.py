"""System command service with platform abstraction."""
from ..platform import get_platform


class SystemService:
    """Handles system-level commands via platform layer."""

    def __init__(self) -> None:
        self.platform = get_platform()

    def suspend(self) -> bool:
        return self.platform.suspend()

    def screen_off(self) -> bool:
        return self.platform.screen_off()

    def lock_screen(self) -> bool:
        return self.platform.lock_screen()
