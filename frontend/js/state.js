/**
 * Shared mutable game state.
 * All modules import this object and mutate its properties directly —
 * no getters/setters needed for a game of this scale.
 */
export const state = {
  mySlot:      -1,
  myRoom:      '',
  gameState:   'connect',   // connect | waiting | countdown | playing | goal | gameover
  localPadPos: 0.5,

  /** Last authoritative snapshot received from server */
  server: {
    balls:         [],
    paddles:       [0.5, 0.5, 0.5, 0.5],
    lives:         [3, 3, 3, 3],
    eliminated:    [false, false, false, false],
    names:         ['', '', '', ''],
    goals_scored:  [0, 0, 0, 0],
    powerups:      [],
    powerup_queue: [],
    goal_offsets:  [0, 0, 0, 0],
    goal_moving:   false,
  },

  /** Interpolated display positions (updated each frame in renderer) */
  displayBallMap: new Map(),   // id → { x, y }
  displayPads:    [0.5, 0.5, 0.5, 0.5],
};
