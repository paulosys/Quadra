"""
managers — room-level effect subsystems extracted from the Room god object.

Each manager implements:
  tick(dt, ...)  — advance one physics step
  reset()        — clear state for a new round

Import from here for convenience:
  from managers import HurricaneManager, MovingGoalManager, PortalManager, \
                       CornerManager, UpgradeManager
"""
from managers.hurricane_manager   import HurricaneManager
from managers.moving_goal_manager import MovingGoalManager
from managers.portal_manager      import PortalManager
from managers.corner_manager      import CornerManager
from managers.upgrade_manager     import UpgradeManager

__all__ = [
    "HurricaneManager",
    "MovingGoalManager",
    "PortalManager",
    "CornerManager",
    "UpgradeManager",
]
