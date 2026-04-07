"""
powerups.effects — Strategy hierarchy for all power-up types.

Re-exports the public API so that existing imports like
  ``from powerups.effects import PowerUpEffect, PowerUpEffectFactory``
continue to work without change.
"""
from powerups.effects.base       import PowerUpEffect
from powerups.effects.factory    import PowerUpEffectFactory
from powerups.effects.double     import DoubleEffect
from powerups.effects.speed      import SpeedEffect
from powerups.effects.snitch     import SnitchEffect
from powerups.effects.moving_goal import MovingGoalEffect
from powerups.effects.portal     import PortalEffect
from powerups.effects.hurricane  import HurricaneEffect
from powerups.effects.ghost_goal import GhostGoalEffect

__all__ = [
    "PowerUpEffect",
    "PowerUpEffectFactory",
    "DoubleEffect",
    "SpeedEffect",
    "SnitchEffect",
    "MovingGoalEffect",
    "PortalEffect",
    "HurricaneEffect",
    "GhostGoalEffect",
]
