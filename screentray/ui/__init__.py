"""UI components - DEPRECATED, use screentray.tray instead."""
from ..tray.tray import TrayApp
from ..tray.popup import StatsPopup
from ..tray.activity_bar import ActivityBar
from ..tray.config_dialog import ConfigDialog

__all__ = ['TrayApp', 'StatsPopup', 'ActivityBar', 'ConfigDialog']
