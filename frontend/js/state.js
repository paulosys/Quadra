/**
 * Shared mutable game state.
 * All modules import this object and mutate its properties directly —
 * no getters/setters needed for a game of this scale.
 */
export const state = {
  mySlot:      -1,
  myRoom:      '',
  gameState:   'connect',   // connect | waiting | countdown | playing | goal | upgrade | kickoff | gameover
  localPadPos: 0.5,
  kickoff:     null,        // null | { scorer, startTime, rotSpeed, timeout }

  /** Last authoritative snapshot received from server */
  server: {
    numSides:      4,
    balls:         [],
    paddles:       new Array(8).fill(0.5),
    lives:         new Array(8).fill(3),
    eliminated:    new Array(8).fill(false),
    names:         new Array(8).fill(''),
    goals_scored:  new Array(8).fill(0),
    powerups:      [],
    powerup_queue: [],
    goal_offsets:  new Array(8).fill(0),
    goal_moving:   false,
    portals:             [],
    hurricane_active:    false,
    corner_powerups:     [null, null, null, null],
    corner_goals_active: [false, false, false, false],
    paddle_len_mult:     new Array(8).fill(1),
    speed_mult:          new Array(8).fill(1),
    powerup_spawn_timer: 0,
  },

  /** Interpolated display positions (updated each frame in renderer) */
  displayBallMap: new Map(),   // id → { x, y }
  displayPads:    new Array(8).fill(0.5),
};
