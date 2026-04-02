/**
 * debug.js — Mouse-controlled debug ball for testing goal collisions.
 *
 * Toggle: press backtick (`) to enable/disable.
 * Shows collision zones and ball status in real time.
 */
import {
  FIELD_MARGIN, BALL_R,
  GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V,
} from './config.js';
import { state } from './state.js';

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

let active = false;
let nx = 0.5, ny = 0.5;   // normalized mouse position (0..1)
let showZones = true;

export function initDebug() {
  canvas.addEventListener('mousemove', e => {
    const r = canvas.getBoundingClientRect();
    nx = (e.clientX - r.left) / canvas.width;
    ny = (e.clientY - r.top)  / canvas.height;
  });

  window.addEventListener('keydown', e => {
    if (e.code === 'Backquote') { active = !active; e.preventDefault(); }
    if (e.code === 'KeyZ' && active) { showZones = !showZones; }
  });
}

export function debugTick() {
  if (!active) return;

  const S  = canvas.width;
  const st = state.server;
  const go = st.goal_offsets || [0, 0, 0, 0];

  const bx = nx * S;
  const by = ny * S;
  const br = BALL_R * S;

  const fm = FIELD_MARGIN;
  const gd = GOAL_DEPTH;
  const gH = GOAL_HALF_H;
  const gV = GOAL_HALF_V;
  const r  = BALL_R;

  // Physics check for each side (mirrors backend physics.py _check_side logic)
  //   ball_edge = pos - inward*r   (leading edge toward the wall)
  //   inGoal:  ball_edge has crossed wall AND perp within goal_half + BALL_R
  //   scored:  inGoal AND has gone past GOAL_DEPTH

  // Scoring threshold mirrors backend: ball_edge must go 2*BALL_R past wall
  // (i.e. the entire ball has crossed the goal line)
  // Lateral check uses goal_half only (no BALL_R expansion) to match visual posts
  const sides = [
    {
      label: 'TOPO',
      elim:  st.eliminated?.[0] ?? false,
      // TOP: inward=+1, wall=fm, ball_edge = ny - r
      inGoal:  (ny - r) < fm          && Math.abs(nx - 0.5 - go[0]) <= gH,
      scored:  (ny - r) < fm - 2*r    && Math.abs(nx - 0.5 - go[0]) <= gH,
    },
    {
      label: 'BAIXO',
      elim:  st.eliminated?.[1] ?? false,
      // BOTTOM: inward=-1, wall=1-fm, ball_edge = ny + r
      inGoal:  (ny + r) > (1 - fm)          && Math.abs(nx - 0.5 - go[1]) <= gH,
      scored:  (ny + r) > (1 - fm) + 2*r    && Math.abs(nx - 0.5 - go[1]) <= gH,
    },
    {
      label: 'ESQUERDA',
      elim:  st.eliminated?.[2] ?? false,
      // LEFT: inward=+1, wall=fm, ball_edge = nx - r
      inGoal:  (nx - r) < fm          && Math.abs(ny - 0.5 - go[2]) <= gV,
      scored:  (nx - r) < fm - 2*r    && Math.abs(ny - 0.5 - go[2]) <= gV,
    },
    {
      label: 'DIREITA',
      elim:  st.eliminated?.[3] ?? false,
      // RIGHT: inward=-1, wall=1-fm, ball_edge = nx + r
      inGoal:  (nx + r) > (1 - fm)          && Math.abs(ny - 0.5 - go[3]) <= gV,
      scored:  (nx + r) > (1 - fm) + 2*r    && Math.abs(ny - 0.5 - go[3]) <= gV,
    },
  ];

  const activeGoal   = sides.find(s => !s.elim && s.scored);
  const activeInGoal = sides.find(s => !s.elim && s.inGoal);

  // ── Draw zones overlay ───────────────────────────────────────────────────────
  if (showZones) {
    _drawZones(S, fm, gd, gH, gV, go, st.eliminated ?? [false,false,false,false]);
  }

  // ── Draw debug ball ──────────────────────────────────────────────────────────
  const ballColor = activeGoal   ? '#ff3333'
                  : activeInGoal ? '#ffbb00'
                  :                '#00ffaa';

  ctx.save();
  // Glow
  const glow = ctx.createRadialGradient(bx, by, 0, bx, by, br * 2.5);
  glow.addColorStop(0,   ballColor + '55');
  glow.addColorStop(1,   ballColor + '00');
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(bx, by, br * 2.5, 0, Math.PI * 2); ctx.fill();

  // Ball body
  const grad = ctx.createRadialGradient(bx - br*0.3, by - br*0.3, br*0.05, bx, by, br);
  grad.addColorStop(0, '#ffffff');
  grad.addColorStop(1, ballColor);
  ctx.fillStyle = grad;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();

  // Border
  ctx.strokeStyle = ballColor;
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.stroke();

  // Ball radius ring (shows collision boundary)
  ctx.setLineDash([3, 3]);
  ctx.strokeStyle = 'rgba(255,255,255,0.4)';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.stroke();
  ctx.setLineDash([]);

  ctx.restore();

  // ── HUD ──────────────────────────────────────────────────────────────────────
  ctx.save();
  ctx.font = 'bold 11px monospace';

  const hudLines = [
    `[ DEBUG ] backtick=off  Z=zonas(${showZones?'on':'off'})`,
    `pos: (${nx.toFixed(3)}, ${ny.toFixed(3)})`,
    activeGoal   ? `\u25cf GOL: ${activeGoal.label}` :
    activeInGoal ? `\u25cf Na rede: ${activeInGoal.label}` :
                   `\u25cb Livre`,
  ];

  hudLines.forEach((line, i) => {
    const isStatus = i === 2;
    ctx.fillStyle = isStatus
      ? (activeGoal ? '#ff4444' : activeInGoal ? '#ffbb00' : '#aaffcc')
      : '#00ffaa';
    ctx.fillText(line, 8, 14 + i * 15);
  });

  ctx.restore();
}

// ── Private ──────────────────────────────────────────────────────────────────

function _drawZones(S, fm, gd, gH, gV, go, elim) {
  const r = BALL_R;

  ctx.save();

  // "In-pocket" zone (amber): ball_edge has passed wall, center not yet 2r past it
  // Width uses goal_half only (matches visual posts)
  ctx.fillStyle = 'rgba(255,180,0,0.22)';
  if (!elim[0]) ctx.fillRect((0.5+go[0]-gH)*S, (fm-2*r)*S,   gH*2*S, 2*r*S);
  if (!elim[1]) ctx.fillRect((0.5+go[1]-gH)*S, (1-fm)*S,     gH*2*S, 2*r*S);
  if (!elim[2]) ctx.fillRect((fm-2*r)*S, (0.5+go[2]-gV)*S,   2*r*S,  gV*2*S);
  if (!elim[3]) ctx.fillRect((1-fm)*S,   (0.5+go[3]-gV)*S,   2*r*S,  gV*2*S);

  // "Scored" zone (red): ball_edge < wall - 2r  →  ball fully past goal line
  ctx.fillStyle = 'rgba(255,0,0,0.28)';
  if (!elim[0]) ctx.fillRect((0.5+go[0]-gH)*S, 0,              gH*2*S, (fm-2*r)*S);
  if (!elim[1]) ctx.fillRect((0.5+go[1]-gH)*S, (1-fm+2*r)*S,   gH*2*S, S);
  if (!elim[2]) ctx.fillRect(0,                (0.5+go[2]-gV)*S, (fm-2*r)*S, gV*2*S);
  if (!elim[3]) ctx.fillRect((1-fm+2*r)*S,     (0.5+go[3]-gV)*S, S,          gV*2*S);

  ctx.restore();
}
