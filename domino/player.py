"""Who is sitting at the table."""
from dataclasses import dataclass, field


@dataclass
class Player:
    id: str                   # whatever the platform uses to identify the user
    name: str
    is_bot: bool = False
    hand: list = field(default_factory=list)
