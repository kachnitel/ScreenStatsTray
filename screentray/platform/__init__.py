"""Platform detection and factory."""
import os
import subprocess
from typing import Optional
from .base import PlatformBase
from .kde import KDEPlatform
from .gnome import GNOMEPlatform
from .generic import GenericPlatform


_platform_instance: Optional[PlatformBase] = None


def detect_platform() -> PlatformBase:
    """
    Detect desktop environment and return appropriate platform instance.

    Detection order:
    1. Check XDG_CURRENT_DESKTOP environment variable
    2. Check for KDE-specific processes
    3. Check for GNOME-specific processes
    4. Fallback to generic implementation
    """
    global _platform_instance

    if _platform_instance is not None:
        return _platform_instance

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    # KDE detection
    if "kde" in desktop or "plasma" in desktop:
        _platform_instance = KDEPlatform()
        print(f"Detected platform: {_platform_instance.name}")
        return _platform_instance

    # GNOME detection
    if "gnome" in desktop or "ubuntu" in desktop:
        _platform_instance = GNOMEPlatform()
        print(f"Detected platform: {_platform_instance.name}")
        return _platform_instance

    # Process-based fallback detection
    try:
        processes = subprocess.check_output(["ps", "-e"]).decode().lower()

        if "plasmashell" in processes or "kwin" in processes:
            _platform_instance = KDEPlatform()
        elif "gnome-shell" in processes or "mutter" in processes:
            _platform_instance = GNOMEPlatform()
        else:
            _platform_instance = GenericPlatform()

    except (subprocess.CalledProcessError, FileNotFoundError):
        _platform_instance = GenericPlatform()

    print(f"Detected platform: {_platform_instance.name}")
    return _platform_instance


def get_platform() -> PlatformBase:
    """Get current platform instance (cached)."""
    return detect_platform()


__all__ = ["PlatformBase", "get_platform", "detect_platform"]

