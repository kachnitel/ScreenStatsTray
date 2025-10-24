"""
Data models for the application.
"""
from dataclasses import dataclass

@dataclass
class Event:
    """Represents a single event in the database."""
    id: int
    timestamp: str
    type: str
    detail: str = ""
