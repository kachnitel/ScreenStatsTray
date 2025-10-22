from dataclasses import dataclass

@dataclass
class Event:
    id: int
    timestamp: str
    type: str
    detail: str = ""
