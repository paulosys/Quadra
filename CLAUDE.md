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

QUADRA is a multiplayer browser ball game (2-4 players, Pong-style square arena). The stack is a Python WebSocket server + vanilla JS/Canvas frontend, communicating via JSON over WebSocket.

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
    main.js         ← Entry point: loop, button bindings, init

backend/            ← Python authoritative server
  config.py         ← All constants loaded from env vars
  models.py         ← Dataclasses: Ball, PowerUp; Side enum
  physics.py        ← PhysicsEngine (stateless, testable)
  powerups.py       ← PowerUpManager (spawn queue, ball-level effects)
  room.py           ← Room (game session state, orchestrates physics/powerups)
  game_loop.py      ← game_loop() coroutine (countdown→play→goal→gameover)
  room_registry.py  ← RoomRegistry + module-level singleton
  ws_handler.py     ← WebSocket connection handler (join, move, start_game)
  entrypoint.py     ← Starts HTTP (aiohttp, port 8080) + WS (port 8765)
```

## Backend design

**Dependency order** (no circular imports):
`config` → `models` → `physics` / `powerups` → `room` → `game_loop` / `room_registry` → `ws_handler` → `entrypoint`

**Physics**: `PhysicsEngine` is stateless — each `tick_ball()` call takes a `Ball` + arena parameters and returns the scored `Side | None`. The `Room` owns all mutable state.

**Power-ups**: `PowerUpManager` handles spawn timers, the pre-seeded queue, and ball-level effects (`double`, `speed`). Room-level effects (`movinggoal`) are signalled by returning the type in the `collected` list; `Room._apply_room_effects()` handles them.

**Rooms**: Created on-demand, destroyed when empty. All game state is in `Room`. Multiple rooms run independently with no shared state.

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
