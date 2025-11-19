#!/usr/bin/env python3
"""Test platform detection and capabilities."""
from screentray.platform import get_platform

platform = get_platform()

print(f"Platform: {platform.name}")
print(f"Window tracking: {platform.supports_window_tracking}")
print(f"\nCapabilities:")
print(f"  Idle detection: {platform.get_idle_seconds() >= 0}")
print(f"  Screen state: {platform.is_screen_on()}")
print(f"  Window info: {platform.get_active_window_info() is not None}")
print(f"  Suspend: available")  # Always available via systemctl
print(f"  Screen off: {platform.screen_off()}")
print(f"  Lock screen: {platform.lock_screen()}")

if platform.supports_window_tracking:
    info = platform.get_active_window_info()
    if info:
        print(f"\nCurrent window: {info[0]} - {info[1]}")

