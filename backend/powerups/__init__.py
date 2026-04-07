"""
powerups — spawn management and effect strategy for all power-up types.

Re-exports the public API so that existing imports like
  ``from powerups import PowerUpManager``
  ``from powerups import PowerUpEffect, PowerUpEffectFactory``
continue to work without change.
"""
from powerups.manager          import PowerUpManager
from powerups.effects.base     import PowerUpEffect
from powerups.effects.factory  import PowerUpEffectFactory

__all__ = [
    "PowerUpManager",
    "PowerUpEffect",
    "PowerUpEffectFactory",
]
