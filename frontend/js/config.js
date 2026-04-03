// Game constants — must match backend/config.py
export const WS_URL = `ws://${window.location.hostname}:8765`;

export const FIELD_MARGIN    = 0.08;
export const PADDLE_THICK    = 0.03;
export const PADDLE_LEN_H    = 0.16;
export const PADDLE_LEN_V    = 0.16;
export const BALL_R          = 0.022;
export const GOAL_DEPTH      = 0.07;
export const GOAL_HALF_H     = 0.168;
export const GOAL_HALF_V     = 0.168;
export const POWERUP_RADIUS  = 0.038;
export const PORTAL_RADIUS   = 0.045;
export const HURRICANE_RADIUS = 0.30;
export const PADDLE_SPEED    = 0.012;

export const SIDE_LABELS = ['Topo', 'Baixo', 'Esquerda', 'Direita'];

export const SIDE_KEYS = [
  { neg: 'KeyA',      pos: 'KeyD'       },
  { neg: 'ArrowLeft', pos: 'ArrowRight' },
  { neg: 'KeyW',      pos: 'KeyS'       },
  { neg: 'ArrowUp',   pos: 'ArrowDown'  },
];
