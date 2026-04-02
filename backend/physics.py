"""
PhysicsEngine — stateless ball physics and collision detection.

Depends only on config and models; has no knowledge of rooms, powerups,
or network. Each method takes what it needs as explicit parameters so it
can be tested in isolation.
"""
from __future__ import annotations

from typing import Optional

from config import (
    BALL_R, BALL_SPEED_INC, BALL_SPEED_MAX,
    FIELD_MARGIN, GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V,
    PADDLE_LEN_H, PADDLE_LEN_V, PADDLE_THICK,
    SPEED_BOOST_FACTOR,
)
from models import Ball, Side


class PhysicsEngine:
    """
    Advances one ball by one tick and returns the side that was scored,
    or None.  Mutates *ball* in-place; everything else is read-only.
    """

    # Pre-computed constants (all derived from config, fixed for the session)
    _speed_inc = 1.0 + BALL_SPEED_INC

    # Per-side layout:
    #   (main_attr, vel_attr, perp_attr, vperp_attr, wall, inward, paddle_half, goal_half)
    # inward = +1  →  wall is a minimum boundary (TOP / LEFT)
    # inward = -1  →  wall is a maximum boundary (BOTTOM / RIGHT)
    _SIDE_PARAMS: dict = {
        Side.TOP:    ('y', 'vy', 'x', 'vx', FIELD_MARGIN,       +1, PADDLE_LEN_H / 2, GOAL_HALF_H),
        Side.BOTTOM: ('y', 'vy', 'x', 'vx', 1.0 - FIELD_MARGIN, -1, PADDLE_LEN_H / 2, GOAL_HALF_H),
        Side.LEFT:   ('x', 'vx', 'y', 'vy', FIELD_MARGIN,       +1, PADDLE_LEN_V / 2, GOAL_HALF_V),
        Side.RIGHT:  ('x', 'vx', 'y', 'vy', 1.0 - FIELD_MARGIN, -1, PADDLE_LEN_V / 2, GOAL_HALF_V),
    }

    def tick_ball(
        self,
        ball:         Ball,
        paddles:      list[float],
        eliminated:   list[bool],
        players:      set[int],
        goal_offsets: list[float],
    ) -> Optional[Side]:
        ball.bounce = False
        ball.x += ball.vx
        ball.y += ball.vy

        speed_cap = BALL_SPEED_MAX * SPEED_BOOST_FACTOR if ball.boosted else BALL_SPEED_MAX
        if not ball.boosted:
            spd = ball.speed
            if spd < speed_cap:
                ball.vx *= self._speed_inc
                ball.vy *= self._speed_inc

        scored: Optional[Side] = None
        for _side in (Side.TOP, Side.BOTTOM, Side.LEFT, Side.RIGHT):
            result = self._check_side(ball, _side, paddles, eliminated, players, goal_offsets)
            if result is not None:
                scored = result
                break

        # Hard speed cap after all deflections
        spd = ball.speed
        if spd > speed_cap:
            ball.vx = ball.vx / spd * speed_cap
            ball.vy = ball.vy / spd * speed_cap

        return scored

    # ── Side checks ───────────────────────────────────────────────────────────

    @staticmethod
    def _in_goal(pos: float, half: float, offset: float = 0.0) -> bool:
        c = 0.5 + offset
        return c - half <= pos <= c + half

    def _check_side(
        self,
        b:            Ball,
        side:         Side,
        paddles:      list[float],
        eliminated:   list[bool],
        players:      set[int],
        goal_offsets: list[float],
    ) -> Optional[Side]:
        attr, vattr, perp_attr, vperp_attr, wall, inward, paddle_half, goal_half = \
            self._SIDE_PARAMS[side]

        r          = BALL_R
        pos        = getattr(b, attr)
        vel        = getattr(b, vattr)
        perp       = getattr(b, perp_attr)
        ball_edge  = pos - inward * r        # leading edge of ball toward this wall
        field_edge = wall + inward * PADDLE_THICK  # inner face of paddle

        if not eliminated[side] and side in players:
            paddle_pos = paddles[side]
            if inward * vel < 0 and inward * (ball_edge - field_edge) <= 0:
                if paddle_pos - paddle_half <= perp <= paddle_pos + paddle_half:
                    setattr(b, vattr, inward * abs(vel))
                    setattr(b, vperp_attr,
                            getattr(b, vperp_attr) + (perp - paddle_pos) / paddle_half * 0.004)
                    setattr(b, attr, field_edge + inward * (r + 0.001))
                    b.bounce     = True
                    b.last_touch = int(side)
                    ball_edge = field_edge + inward * 0.001  # keep in sync after reposition

            if inward * (ball_edge - wall) < 0:
                if self._in_goal(perp, goal_half, goal_offsets[side]):
                    if inward * (ball_edge - wall) < -2 * BALL_R:
                        return side
                else:
                    setattr(b, vattr, inward * abs(vel))
                    setattr(b, attr,  wall + inward * r)
        else:
            if inward * (ball_edge - wall) < 0:
                setattr(b, vattr, inward * abs(vel))
                setattr(b, attr,  wall + inward * r)

        return None
