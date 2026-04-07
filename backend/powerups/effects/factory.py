"""PowerUpEffectFactory — Factory pattern for creating PowerUpEffect instances.

To add a new power-up type, call ``PowerUpEffectFactory.register()``
without modifying any existing code (Open/Closed principle).
"""
from __future__ import annotations

from powerups.effects.base       import PowerUpEffect
from powerups.effects.double     import DoubleEffect
from powerups.effects.speed      import SpeedEffect
from powerups.effects.snitch     import SnitchEffect
from powerups.effects.moving_goal import MovingGoalEffect
from powerups.effects.portal     import PortalEffect
from powerups.effects.hurricane  import HurricaneEffect
from powerups.effects.ghost_goal import GhostGoalEffect


class PowerUpEffectFactory:
    _registry: dict[str, type[PowerUpEffect]] = {
        "double":     DoubleEffect,
        "speed":      SpeedEffect,
        "snitch":     SnitchEffect,
        "movinggoal": MovingGoalEffect,
        "portal":     PortalEffect,
        "hurricane":  HurricaneEffect,
        "ghostgoal":  GhostGoalEffect,
    }

    @classmethod
    def create(cls, ptype: str) -> PowerUpEffect:
        klass = cls._registry.get(ptype)
        if klass is None:
            raise ValueError(f"Unknown powerup type: {ptype!r}")
        return klass()

    @classmethod
    def register(cls, ptype: str, klass: type[PowerUpEffect]) -> None:
        """Extension point: register new power-up types at runtime."""
        cls._registry[ptype] = klass
