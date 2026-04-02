"""
RoomRegistry — single source of truth for active game rooms.

Provides get-or-create and delete semantics. Exposes a module-level
singleton so handlers don't need to pass it around explicitly.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from room import Room

log = logging.getLogger("quadra")


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: Dict[str, Room] = {}

    def get_or_create(self, room_id: str) -> Room:
        if room_id not in self._rooms:
            self._rooms[room_id] = Room(room_id)
            log.info(f"Room '{room_id}' created (total: {len(self._rooms)})")
        return self._rooms[room_id]

    def delete(self, room_id: str) -> None:
        if self._rooms.pop(room_id, None) is not None:
            log.info(f"Room '{room_id}' deleted (total: {len(self._rooms)})")

    def get(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id)

    @property
    def count(self) -> int:
        return len(self._rooms)


# Module-level singleton shared across all handlers
registry = RoomRegistry()
