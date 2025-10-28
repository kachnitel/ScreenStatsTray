"""
screentray/plugins/__init__.py

Plugin system for ScreenTray.
"""
from .base import PluginBase
from .manager import PluginManager

__all__ = ['PluginBase', 'PluginManager']
