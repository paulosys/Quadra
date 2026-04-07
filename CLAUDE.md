# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start the application (build + run)
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down

# Restart without rebuild
docker compose restart
```

There is no test suite, linter, or build step outside of Docker.

## Architecture

QUADRA is a multiplayer browser ball game (2-8 players, Pong-style polygonal arena). The stack is a Python WebSocket server + vanilla JS/Canvas frontend, communicating via JSON over WebSocket.

```
frontend/           ← Browser client (ES Modules, no bundler)
  index.html        ← Markup only, loads css/style.css + js/main.js
  css/style.css
  js/
    config.js       ← Game constants (must match backend/config.py)
    state.js        ← Shared mutable state object (imported everywhere)
    audio.js        ← Web Audio API, self-contained
    particles.js    ← Fire particle system
    renderer.js     ← Canvas drawing (draw, resize)
    ui.js           ← DOM overlays, scoreboard, powerup queue
    input.js        ← Keyboard + mobile touch → server
    network.js      ← WebSocket: connect, send, message routing
    debug.js        ← Debug overlay: mouse-controlled ball + goal-collision zones (toggle: backtick)
    main.js         ← Entry point: loop, button bindings, init

backend/
  config.py               ← All constants loaded from env vars
  events.py               ← EventBus + GameEvent enum (Observer pattern)
  physics.py              ← PhysicsEngine (stateless) + WallDef + compute_walls
  room.py                 ← Room facade (game session state, orchestrates managers)
  game_loop.py            ← game_loop() coroutine (countdown→play→goal→upgrade→gameover)
  room_registry.py        ← RoomRegistry + module-level singleton
  ws_handler.py           ← WebSocket connection handler (join, move, start_game)
  entrypoint.py           ← Starts HTTP (aiohttp, port 8080) + WS (port 8765)
  server.py               ← Legacy monolithic server (kept for reference)
  docs/
    class_diagram.puml    ← PlantUML class diagram of the full backend

  models/                 ← Domain entities
    ball.py               ← Ball dataclass + behaviour methods (boost, snitch, timers)
    player.py             ← Player dataclass (consolidates all per-slot mutable state)
    arena.py              ← Side enum, SIDE_NAMES, PowerUp, Portal, CornerPowerUp

  powerups/               ← Power-up system
    manager.py            ← PowerUpManager (spawn queue, collision detection, dispatch)
    effects/              ← Strategy pattern — one file per power-up type
      base.py             ← PowerUpEffect ABC (apply_to_ball / apply_to_room)
      factory.py          ← PowerUpEffectFactory (Factory pattern, open for extension)
      double.py           ← DoubleEffect
      speed.py            ← SpeedEffect
      snitch.py           ← SnitchEffect
      moving_goal.py      ← MovingGoalEffect
      portal.py           ← PortalEffect
      hurricane.py        ← HurricaneEffect
      ghost_goal.py       ← GhostGoalEffect

  managers/               ← Room-level subsystems (each owns one responsibility)
    hurricane_manager.py  ← Vortex force applied to balls near center
    moving_goal_manager.py← Goal-zone oscillation (global power-up + corner variant)
    portal_manager.py     ← Portal spawning, rotation, ball teleportation
    corner_manager.py     ← Corner power-up charging (4-player square arena only)
    upgrade_manager.py    ← Upgrade card selection phase between rounds
```

## Backend design

**Dependency order** (no circular imports):
```
config
  → models  (ball, player, arena)
    → physics
    → events
    → powerups/effects  (base, concretes, factory)
      → powerups/manager
        → managers  (hurricane, moving_goal, portal, corner, upgrade)
          → room
            → game_loop / room_registry
              → ws_handler
                → entrypoint
```

**Design patterns applied:**
- **Facade** — `Room` is a thin coordinator (~300 lines) over 5 specialised managers; it owns no effect logic itself.
- **Strategy** — `PowerUpEffect` ABC with 7 concrete subclasses, one per power-up type. Each is isolated in its own file.
- **Factory** — `PowerUpEffectFactory` maps type strings to effect classes; new power-ups require only a new file + one `_registry` entry.
- **Observer** — `EventBus` + `GameEvent` decouple `PowerUpManager` from room-level managers. Effects publish events; `Room._on_powerup_collected` routes them.
- **Value Object** — `Player` dataclass consolidates 6 former parallel arrays (`lives`, `eliminated`, `goals_scored`, `paddles`, `paddle_len_mult`, `speed_mult`) into one object per slot.

**Physics**: `PhysicsEngine` is stateless — each `tick_ball()` call takes a `Ball` + arena parameters and returns the scored `Side | None`. For polygonal arenas (n > 4) it uses vector-based `WallDef` checks computed by `compute_walls(n)`.

**Power-ups**: `PowerUpManager` handles spawn timers and the pre-seeded queue. On collision it calls `PowerUpEffectFactory.create(type)`, then `effect.apply_to_ball()` and `effect.apply_to_room()`. Room-level effects are signalled via `EventBus`; the matching manager reacts through its subscriber.

**Rooms**: Created on-demand by `RoomRegistry`, destroyed when empty. All game state lives in `Room`. Multiple rooms run independently with no shared state.

## Frontend design

Uses **ES Modules** (`type="module"`) — no bundler, no globals.

**State flow**: `network.js` receives server messages and writes to `state.js`. `renderer.js` and `ui.js` read from `state.js` each frame/event. `input.js` writes `state.localPadPos` and calls `send()` (injected from `main.js`).

**No circular imports**: `send` is passed as a parameter to `inputTick(send)` and `setupInputListeners(send)` rather than imported from `network.js` in `input.js`.

## WebSocket protocol

- **Client → Server:** `{"type": "join"|"move"|"start_game", ...}`
- **Server → Client:** `{"type": "state"|"goal"|"countdown"|"start"|"joined"|"player_joined"|"player_left"|"gameover"|"error", ...}`
- State messages sent at 60 Hz during play.

## Configuration

All backend tunable parameters are in `.env` and loaded via `os.getenv()` in `backend/config.py`. Frontend constants in `js/config.js` must be kept in sync manually.

## Adding a new power-up type

1. Create `backend/powerups/effects/<name>.py` implementing `PowerUpEffect`.
2. Register it in `backend/powerups/effects/factory.py` → `_registry`.
3. Add the type string and weight to `POWERUP_TYPES` / `POWERUP_WEIGHTS` in `config.py`.
4. Add the corresponding visual/sound handling in the frontend if needed.
