"""
game_loop — async coroutine that drives one Room through its full lifecycle:
  countdown → playing → goal pause → upgrade pick → countdown → … → gameover
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from config import COUNTDOWN_SECS, TICK_DT

if TYPE_CHECKING:
    from room import Room

log = logging.getLogger("quadra")

# Upgrade cards available after each goal
_UPGRADE_CARDS = [
    {"id": "life",   "cost_goals": 3, "label": "+1 Vida",    "desc": "Troca 3 gols por 1 vida extra"},
    {"id": "paddle", "cost_goals": 2, "label": "+10% Barra", "desc": "Aumenta 10% a barra do goleiro"},
    {"id": "speed",  "cost_goals": 2, "label": "+15% Veloc.", "desc": "Aumenta 15% a velocidade"},
]
_UPGRADE_TIMEOUT  = 7.0   # seconds each player has to pick
_GOAL_FLASH_PAUSE = 1.5   # brief pause for the goal flash before upgrade screen
_KICKOFF_TIMEOUT  = 5.0   # seconds scorer has to aim and kick
_KICKOFF_ROT_SPEED = 1.8  # rad/s — must match frontend js/network.js rotSpeed


async def game_loop(room: Room) -> None:
    log.info(f"[{room.id}] game loop started")

    room.set_n_sides(max(4, room.num_players))
    await _run_countdown(room)

    room.launch_ball()
    room.state = "playing"
    await room.broadcast({"type": "start"})

    while True:
        tick_start = time.monotonic()

        async with room.lock:
            if room.num_players == 0:
                log.info(f"[{room.id}] all players left, stopping loop")
                room.state = "waiting"
                return

            if room.state == "playing":
                scored, scorer, collected = room.tick()

                if scored is not None:
                    p = room.players.get(scored)
                    if p is not None and not p.eliminated:
                        done = await _handle_goal(room, scored, scorer)
                        if done:
                            return
                        continue  # timing reset handled inside _handle_goal

                await room.broadcast(room.state_snapshot(collected))

        elapsed = time.monotonic() - tick_start
        sleep   = TICK_DT - elapsed
        if sleep > 0:
            await asyncio.sleep(sleep)


async def _run_countdown(room: Room) -> None:
    room.state = "countdown"
    ordered = [room.players.get(i) for i in range(room.n_sides)]
    paddles = [p.paddle_pos if p else 0.5 for p in ordered]
    for n in range(COUNTDOWN_SECS, 0, -1):
        await room.broadcast({"type": "countdown", "value": n, "paddles": paddles})
        await asyncio.sleep(1.0)


async def _handle_goal(room: Room, scored: int, scorer: int | None) -> bool:
    """
    Process a goal event. Returns True if the game ended (gameover).
    Must be called while holding room.lock.
    scorer is the player slot who last touched the ball (may be None).
    """
    scored_player = room.players.get(scored)
    if scored_player is None:
        return False

    scored_player.lives -= 1
    eliminated_now  = scored_player.lives <= 0
    can_buy_life    = eliminated_now and scored_player.goals_scored >= 3

    if eliminated_now and not can_buy_life:
        scored_player.eliminated = True
    elif can_buy_life:
        scored_player.pending_elimination = True  # offer pending; not yet eliminated

    # Award goal to scorer — no own goals
    if scorer is not None and scorer != scored and scorer in room.players:
        room.players[scorer].goals_scored += 1

    alive     = room.alive_slots()
    # game_over only if no pending offer can save anyone
    game_over = len(alive) <= 1 and not can_buy_life

    room.state = "goal"
    await room.broadcast({
        "type":                    "goal",
        "player":                  scored,
        "scorer":                  scorer,
        "lives":                   room.lives,
        "eliminated":              room.eliminated,
        "eliminated_now":          eliminated_now,
        "can_buy_life":            can_buy_life,
        "pending_elimination_slots": [s for s, p in room.players.items()
                                       if p.pending_elimination],
        "game_over":               game_over,
        "winner":                  alive[0] if game_over and alive else -1,
        "names":                   [room.names.get(i, "") for i in range(room.n_sides)],
        "goals_scored":            room.goals_scored,
        "life_gained":             False,
    })

    if game_over:
        room.state = "gameover"
        return True

    # Release lock so ws_handler can receive pick_upgrade messages during the pause
    room.lock.release()
    try:
        await asyncio.sleep(_GOAL_FLASH_PAUSE)
        if room.num_players == 0:
            return True

        await _run_upgrade_phase(room)
        if room.num_players == 0:
            return True

        # After upgrade phase, a pending-elimination player who didn't buy a life
        # is now fully eliminated — check if that ends the game.
        alive_after = room.alive_slots()
        if len(alive_after) <= 1:
            room.state = "gameover"
            winner = alive_after[0] if alive_after else -1
            await room.broadcast({
                "type":      "gameover",
                "winner":    winner,
                "names":     [room.names.get(i, "") for i in range(room.n_sides)],
                "eliminated": room.eliminated,
            })
            return True

        kickoff_scorer = scorer if (scorer is not None and scorer != scored) else None
        room.clear_round_state()
        await room.broadcast(room.state_snapshot())
        if kickoff_scorer is None:
            await _run_countdown(room)

        kick_angle = await _run_kickoff_phase(room, kickoff_scorer)
        if room.num_players == 0:
            return True

        room.launch_ball(kick_angle=kick_angle)
        room.state = "playing"
        await room.broadcast({"type": "start"})
        return False
    finally:
        await room.lock.acquire()


async def _run_kickoff_phase(room: Room, scorer: int | None) -> float | None:
    """
    Let the scorer aim and kick the ball. Returns the chosen angle (radians) or
    None when there is no scorer (random launch will be used).
    Called while room.lock is NOT held.
    """
    if scorer is None or scorer not in room.players:
        return None

    room.kickoff_event  = asyncio.Event()
    room.kickoff_angle  = None
    room.kickoff_scorer = scorer
    room.state = "kickoff"

    await room.broadcast({
        "type":    "kickoff",
        "scorer":  scorer,
        "timeout": _KICKOFF_TIMEOUT,
    })

    kickoff_start = time.monotonic()
    try:
        await asyncio.wait_for(room.kickoff_event.wait(), timeout=_KICKOFF_TIMEOUT)
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - kickoff_start
        room.kickoff_angle = elapsed * _KICKOFF_ROT_SPEED

    room.kickoff_event  = None
    room.kickoff_scorer = None
    return room.kickoff_angle


async def _run_upgrade_phase(room: Room) -> None:
    """Show upgrade cards to all players and wait for picks (or timeout)."""
    pending_slots = [s for s, p in room.players.items() if p.pending_elimination]
    all_done = room.begin_upgrade_phase()
    room.state = "upgrade"

    await room.broadcast({
        "type":                      "upgrade_pick",
        "cards":                     _UPGRADE_CARDS,
        "goals_scored":              room.goals_scored,
        "timeout":                   int(_UPGRADE_TIMEOUT),
        "pending_elimination_slots": pending_slots,
    })

    try:
        await asyncio.wait_for(all_done.wait(), timeout=_UPGRADE_TIMEOUT)
    except asyncio.TimeoutError:
        pass

    # Resolve any pending eliminations (player didn't buy a life in time)
    for p in room.players.values():
        if p.pending_elimination:
            p.eliminated          = True
            p.pending_elimination = False

    # Notify clients of applied upgrades and final elimination state
    await room.broadcast({
        "type":            "upgrade_result",
        "goals_scored":    room.goals_scored,
        "lives":           room.lives,
        "eliminated":      room.eliminated,
        "paddle_len_mult": room.paddle_len_mult,
        "speed_mult":      room.speed_mult,
    })
