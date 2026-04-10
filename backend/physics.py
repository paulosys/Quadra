"""
PhysicsEngine — stateless ball physics and collision detection.

Depends only on config and models; has no knowledge of rooms, powerups,
or network. Each method takes what it needs as explicit parameters so it
can be tested in isolation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from config import (
    BALL_R, BALL_SPEED_INC, BALL_SPEED_MAX,
    FIELD_MARGIN, GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V,
    PADDLE_LEN_H, PADDLE_LEN_V, PADDLE_THICK,
    SPEED_BOOST_FACTOR,
)
from models import Ball, Side


@dataclass
class WallDef:
    nx: float; ny: float   # outward unit normal
    tx: float; ty: float   # tangent along wall (rightward / clockwise)
    mx: float; my: float   # wall midpoint in normalised coords
    half_len: float        # half wall length


def compute_walls(n: int) -> list[WallDef]:
    """Return N WallDef objects, one per player slot.

    For n=4 the legacy TOP/BOTTOM/LEFT/RIGHT order is preserved and
    half_len=0.5 so that paddles[i] maps directly to world x/y coord.
    For n>4 a clockwise regular N-gon starting at the top is used.
    """
    inradius = 0.5 - FIELD_MARGIN
    if n == 4:
        return [
            WallDef( 0, -1,  1,  0,  0.5,         inradius,      0.5),  # TOP
            WallDef( 0,  1,  1,  0,  0.5,      1 - inradius,     0.5),  # BOTTOM
            WallDef(-1,  0,  0,  1,  inradius,      0.5,          0.5),  # LEFT
            WallDef( 1,  0,  0,  1,  1 - inradius,  0.5,          0.5),  # RIGHT
        ]
    # Para n>4: maximiza o polígono mantendo os vértices dentro do canvas
    inradius = (0.5 - 0.01) * math.cos(math.pi / n)
    half_len = inradius * math.tan(math.pi / n)
    walls: list[WallDef] = []
    for i in range(n):
        angle  = -math.pi / 2 + i * 2 * math.pi / n
        nx, ny = math.cos(angle), math.sin(angle)
        tx, ty = -ny, nx
        walls.append(WallDef(nx, ny, tx, ty,
                             0.5 + inradius * nx,
                             0.5 + inradius * ny,
                             half_len))
    return walls


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
        ball:             Ball,
        paddles:          list[float],
        eliminated:       list[bool],
        players:          set[int],
        goal_offsets:     list[float],
        paddle_len_mults: list[float],
        wall_defs:        Optional[list[WallDef]] = None,
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
        if wall_defs is not None:
            for i, wd in enumerate(wall_defs):
                result = self._check_wall(ball, i, wd, paddles, eliminated,
                                          players, goal_offsets, paddle_len_mults)
                if result is not None:
                    scored = result
                    break
        else:
            for _side in (Side.TOP, Side.BOTTOM, Side.LEFT, Side.RIGHT):
                result = self._check_side(ball, _side, paddles, eliminated, players, goal_offsets, paddle_len_mults)
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
        b:                Ball,
        side:             Side,
        paddles:          list[float],
        eliminated:       list[bool],
        players:          set[int],
        goal_offsets:     list[float],
        paddle_len_mults: list[float],
    ) -> Optional[Side]:
        attr, vattr, perp_attr, vperp_attr, wall, inward, paddle_half, goal_half = \
            self._SIDE_PARAMS[side]
        paddle_half = paddle_half * paddle_len_mults[side]

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

    def _check_wall(
        self,
        b:                Ball,
        wall_idx:         int,
        wd:               WallDef,
        paddles:          list[float],
        eliminated:       list[bool],
        players:          set[int],
        goal_offsets:     list[float],
        paddle_len_mults: list[float],
    ) -> Optional[int]:
        """Vector-based wall check for polygon arenas (N > 4)."""
        r           = BALL_R
        d_center    = (b.x - wd.mx) * wd.nx + (b.y - wd.my) * wd.ny
        tang        = (b.x - wd.mx) * wd.tx + (b.y - wd.my) * wd.ty
        vel_n       = b.vx * wd.nx + b.vy * wd.ny
        paddle_half = PADDLE_LEN_H / 2 * paddle_len_mults[wall_idx] * wd.half_len * 2
        paddle_tang = (paddles[wall_idx] - 0.5) * 2 * wd.half_len
        # goal_half proportional to wall length — same ratio as the 4-player square
        goal_half   = GOAL_HALF_H * wd.half_len * 2
        # goal_offsets[i] stores raw tangential offset (same units as tang)
        goal_tang   = goal_offsets[wall_idx]

        if not eliminated[wall_idx] and wall_idx in players:
            # Paddle bounce
            if vel_n > 0 and d_center >= -(PADDLE_THICK + r):
                if abs(tang - paddle_tang) <= paddle_half:
                    new_vel_n = -abs(vel_n)
                    dv = new_vel_n - vel_n
                    b.vx += dv * wd.nx
                    b.vy += dv * wd.ny
                    spin = (tang - paddle_tang) / paddle_half * 0.004
                    b.vx += spin * wd.tx
                    b.vy += spin * wd.ty
                    push = -PADDLE_THICK - r - 0.001 - d_center
                    b.x += push * wd.nx
                    b.y += push * wd.ny
                    b.bounce     = True
                    b.last_touch = wall_idx
                    d_center = -PADDLE_THICK - r - 0.001

            if d_center >= -r:
                in_goal = abs(tang - goal_tang) <= goal_half
                if in_goal:
                    if d_center >= r:
                        return wall_idx   # scored
                else:
                    # Solid wall bounce
                    new_vel_n = -abs(vel_n)
                    dv = new_vel_n - vel_n
                    b.vx += dv * wd.nx
                    b.vy += dv * wd.ny
                    push = -r - d_center
                    b.x += push * wd.nx
                    b.y += push * wd.ny
        else:
            # Eliminated or no player: solid wall
            if d_center >= -r:
                new_vel_n = -abs(vel_n)
                dv = new_vel_n - vel_n
                b.vx += dv * wd.nx
                b.vy += dv * wd.ny
                push = -r - d_center
                b.x += push * wd.nx
                b.y += push * wd.ny

        return None
