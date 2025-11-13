"""System command service."""
import subprocess

class SystemService:
    """Handles system-level commands."""

    @staticmethod
    def suspend() -> None:
        """Suspend the system."""
        subprocess.run(["systemctl", "suspend", "--check-inhibitors=no"], check=False)

    @staticmethod
    def screen_off() -> None:
        """Turn off the screen."""
        subprocess.run(["xset", "dpms", "force", "off"], check=False)

    @staticmethod
    def lock_screen() -> None:
        """Lock the screen."""
        subprocess.run(["loginctl", "lock-session"], check=False)
