"""
Global configuration — all tunable values loaded from environment variables.
"""
import os

# ── Tick ───────────────────────────────────────────────────────────────────────
TICK_RATE: int   = int(os.getenv("TICK_RATE", 60))
TICK_DT:   float = 1.0 / TICK_RATE

# ── Arena ──────────────────────────────────────────────────────────────────────
FIELD_MARGIN: float = float(os.getenv("FIELD_MARGIN", 0.08))
PADDLE_THICK: float = float(os.getenv("PADDLE_THICK", 0.03))
PADDLE_LEN_H: float = float(os.getenv("PADDLE_LEN_H", 0.16))
PADDLE_LEN_V: float = float(os.getenv("PADDLE_LEN_V", 0.16))
PADDLE_SPEED: float = float(os.getenv("PADDLE_SPEED", 0.012))

# ── Ball ───────────────────────────────────────────────────────────────────────
BALL_R:          float = float(os.getenv("BALL_R",          0.022))
BALL_SPEED_INIT: float = float(os.getenv("BALL_SPEED_INIT", 0.008))
BALL_SPEED_MAX:  float = float(os.getenv("BALL_SPEED_MAX",  0.022))
BALL_SPEED_INC:  float = float(os.getenv("BALL_SPEED_INC",  0.00015))

# ── Goals ──────────────────────────────────────────────────────────────────────
GOAL_DEPTH:  float = float(os.getenv("GOAL_DEPTH",  0.07))
GOAL_HALF_H: float = float(os.getenv("GOAL_HALF_H", 0.168))
GOAL_HALF_V: float = float(os.getenv("GOAL_HALF_V", 0.168))

# ── Game ───────────────────────────────────────────────────────────────────────
LIVES_START:    int   = int(os.getenv("LIVES_START",    3))
GOAL_PAUSE:     float = float(os.getenv("GOAL_PAUSE",   2.0))
COUNTDOWN_SECS: int   = int(os.getenv("COUNTDOWN_SECS", 3))

# ── Power-ups ──────────────────────────────────────────────────────────────────
POWERUP_RADIUS:        float     = float(os.getenv("POWERUP_RADIUS",        0.038))
POWERUP_SPAWN_MIN:     float     = float(os.getenv("POWERUP_SPAWN_MIN",     8.0))
POWERUP_SPAWN_MAX:     float     = float(os.getenv("POWERUP_SPAWN_MAX",     14.0))
POWERUP_TYPES:         list[str] = ["double", "speed", "movinggoal", "snitch", "portal", "hurricane", "ghostgoal"]
POWERUP_WEIGHTS:       list[int] = [4, 3, 1, 2, 2, 2, 4]
POWERUP_QUEUE_SIZE:    int       = int(os.getenv("POWERUP_QUEUE_SIZE",      4))
MAX_POWERUPS_ON_FIELD: int       = int(os.getenv("MAX_POWERUPS_ON_FIELD",   2))
MAX_BALLS:             int       = int(os.getenv("MAX_BALLS",                4))

SPEED_BOOST_FACTOR:   float = float(os.getenv("SPEED_BOOST_FACTOR",   1.65))
SPEED_BOOST_DURATION: float = float(os.getenv("SPEED_BOOST_DURATION", 5.0))

MOVING_GOAL_SPEED:    float = float(os.getenv("MOVING_GOAL_SPEED",    1.1))
MOVING_GOAL_AMP:      float = float(os.getenv("MOVING_GOAL_AMP",      0.17))
MOVING_GOAL_DURATION: float = float(os.getenv("MOVING_GOAL_DURATION", 9.0))

SNITCH_DURATION:    float = float(os.getenv("SNITCH_DURATION",    8.0))
SNITCH_TURN_CHANCE: float = float(os.getenv("SNITCH_TURN_CHANCE", 0.025))  # sharp-turn probability per tick

PORTAL_DURATION:    float = float(os.getenv("PORTAL_DURATION",    10.0))
PORTAL_RADIUS:      float = float(os.getenv("PORTAL_RADIUS",      0.045))
PORTAL_MIN_DIST:    float = float(os.getenv("PORTAL_MIN_DIST",    0.35))
PORTAL_COOLDOWN:    float = float(os.getenv("PORTAL_COOLDOWN",    0.4))
PORTAL_ROT_SPEED:   float = float(os.getenv("PORTAL_ROT_SPEED",   1.5))   # rad/s (~4s per full spin)
PORTAL_ENTRY_DELAY: float = float(os.getenv("PORTAL_ENTRY_DELAY", 0.25))  # seconds before teleport fires

HURRICANE_DURATION: float = float(os.getenv("HURRICANE_DURATION", 6.0))
HURRICANE_RADIUS:   float = float(os.getenv("HURRICANE_RADIUS",   0.30))
HURRICANE_STRENGTH: float = float(os.getenv("HURRICANE_STRENGTH", 0.05))   # rad/tick rotation — high = strong spin
HURRICANE_PULL:     float = float(os.getenv("HURRICANE_PULL",     0.004))  # centripetal accel toward center

# ── Corner power-ups (4-player only) ───────────────────────────────────────────
CORNER_POWERUP_SPAWN_MIN: float = float(os.getenv("CORNER_POWERUP_SPAWN_MIN", 15.0))
CORNER_POWERUP_SPAWN_MAX: float = float(os.getenv("CORNER_POWERUP_SPAWN_MAX", 25.0))
CORNER_CHARGE_TIME:       float = float(os.getenv("CORNER_CHARGE_TIME",       1.0))
CORNER_PROXIMITY:         float = float(os.getenv("CORNER_PROXIMITY",         0.10))
CORNER_GOAL_DURATION:     float = float(os.getenv("CORNER_GOAL_DURATION",     9.0))

# ── Pulse ──────────────────────────────────────────────────────────────────────
PULSE_FORCE_NORMAL:  float = float(os.getenv("PULSE_FORCE_NORMAL",  0.010))
PULSE_FORCE_PERFECT: float = float(os.getenv("PULSE_FORCE_PERFECT", 0.020))
PULSE_RADIUS_NORMAL: float = float(os.getenv("PULSE_RADIUS_NORMAL", 0.18))
PULSE_RADIUS_PERFECT: float = float(os.getenv("PULSE_RADIUS_PERFECT", 0.055))
PULSE_COOLDOWN:      float = float(os.getenv("PULSE_COOLDOWN",      0.5))

# ── Network ────────────────────────────────────────────────────────────────────
WS_HOST:          str   = os.getenv("WS_HOST",          "0.0.0.0")
WS_PORT:          int   = int(os.getenv("WS_PORT",       8765))
HTTP_HOST:        str   = os.getenv("HTTP_HOST",         "0.0.0.0")
HTTP_PORT:        int   = int(os.getenv("HTTP_PORT",      8080))
WS_PING_INTERVAL: int   = int(os.getenv("WS_PING_INTERVAL", 20))
WS_PING_TIMEOUT:  int   = int(os.getenv("WS_PING_TIMEOUT",  30))
