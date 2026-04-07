/**
 * debug.js — Enhanced debug overlay.
 *
 * Toggle:  backtick (`) to enable/disable
 *
 * Keys (while active):
 *   Z          — toggle goal collision zones
 *   G          — freeze/unfreeze goal scoring
 *   B          — add a regular ball
 *   N          — remove a regular ball (allows 0)
 *   M          — toggle mouse ball (real server ball at cursor position)
 *   1-7        — select powerup type
 *   Left-click — spawn selected powerup at cursor
 *   Right-click— teleport first regular ball to cursor
 */
import {
  FIELD_MARGIN, BALL_R,
  GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V,
} from './config.js';
import { state } from './state.js';
import { send } from './network.js';

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

let active      = false;
let mouseBallOn = false;
let nx = 0.5, ny = 0.5;
let showZones = true;

// ── Powerup data ──────────────────────────────────────────────────────────────

const POWERUP_TYPES = ['double', 'speed', 'movinggoal', 'snitch', 'portal', 'hurricane', 'ghostgoal'];
const POWERUP_COLORS = {
  double:     '#ff6b6b',
  speed:      '#ffd93d',
  movinggoal: '#6bcb77',
  snitch:     '#c77dff',
  portal:     '#4d96ff',
  hurricane:  '#ff9f43',
  ghostgoal:  '#a8dadc',
};
const POWERUP_LABELS = {
  double:     'Double',
  speed:      'Speed',
  movinggoal: 'MovingGoal',
  snitch:     'Snitch',
  portal:     'Portal',
  hurricane:  'Hurricane',
  ghostgoal:  'GhostGoal',
};

let selectedPowerup = 'speed';

// ── DOM references ────────────────────────────────────────────────────────────

let _sidebar    = null;
let _puItems    = [];   // [{ el, type }]
let _statRows   = [];   // [{ label el, val el }]

const STATUS_FIELDS = ['cursor', 'bolas', 'timer', 'efeitos', 'zona', 'gols', 'mouse'];

function _buildSidebar() {
  _sidebar = document.getElementById('debug-sidebar');

  // Power-up list
  const list = document.getElementById('dbg-pu-list');
  list.innerHTML = '';
  _puItems = [];
  POWERUP_TYPES.forEach((type, i) => {
    const item = document.createElement('div');
    item.className = 'dbg-pu-item' + (type === selectedPowerup ? ' selected' : '');
    item.innerHTML =
      `<span class="dbg-pu-dot" style="background:${POWERUP_COLORS[type]}"></span>` +
      `<span class="dbg-pu-key">${i + 1}</span>` +
      `<span class="dbg-pu-label">${POWERUP_LABELS[type]}</span>`;
    item.addEventListener('click', () => _selectPowerup(type));
    list.appendChild(item);
    _puItems.push({ el: item, type });
  });

  // Status rows
  const statusEl = document.getElementById('dbg-status');
  statusEl.innerHTML = '';
  _statRows = [];
  STATUS_FIELDS.forEach(field => {
    const row = document.createElement('div');
    row.className = 'dbg-stat-row';
    const lbl = document.createElement('span');
    lbl.className = 'dbg-s-label';
    lbl.textContent = field;
    const val = document.createElement('span');
    val.className = 'dbg-s-val';
    row.appendChild(lbl);
    row.appendChild(val);
    statusEl.appendChild(row);
    _statRows.push(val);
  });
}

function _selectPowerup(type) {
  selectedPowerup = type;
  _puItems.forEach(({ el, type: t }) => el.classList.toggle('selected', t === type));
}

function _updateStatus(activeGoal, activeInGoal, mouseBall) {
  const st  = state.server;
  const frozen = st.debug_freeze_goals || false;
  const balls  = st.balls || [];
  const regular = balls.filter(b => b.id !== st.debug_mouse_ball_id);

  const effects = [];
  if (mouseBall?.boosted)                           effects.push('boost');
  if (mouseBall?.snitched)                          effects.push('snitch');
  if (st.hurricane_active)                          effects.push('hurri.');
  if (st.goal_moving)                               effects.push('mvgoal');
  if ((st.portals || []).length > 0)                effects.push('portal');
  if ((st.corner_goals_active || []).some(Boolean)) effects.push('corner');

  const spawnTimer = st.powerup_spawn_timer ?? 0;

  const rows = [
    { val: `${nx.toFixed(3)}, ${ny.toFixed(3)}`,             color: 'rgba(255,255,255,.6)' },
    { val: `${regular.length}${mouseBallOn ? ' +M' : ''}`,   color: 'rgba(255,255,255,.6)' },
    { val: `${spawnTimer.toFixed(1)}s`,                       color: 'rgba(255,255,255,.6)' },
    { val: effects.length ? effects.join(' ') : 'nenhum',     color: effects.length ? '#ffd93d' : 'rgba(255,255,255,.25)' },
    { val: activeGoal   ? `GOL: ${activeGoal.label}`
         : activeInGoal ? `Rede: ${activeInGoal.label}`
         :                'Livre',
      color: activeGoal ? '#ff4444' : activeInGoal ? '#ffbb00' : '#00ffaa' },
    { val: frozen ? 'FROZEN' : 'live',                        color: frozen ? '#ff8800' : 'rgba(255,255,255,.3)' },
    { val: mouseBallOn ? 'ON' : 'off',                        color: mouseBallOn ? '#00ffaa' : 'rgba(255,255,255,.3)' },
  ];

  _statRows.forEach((el, i) => {
    if (rows[i]) { el.textContent = rows[i].val; el.style.color = rows[i].color; }
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────

export function initDebug() {
  _buildSidebar();

  canvas.addEventListener('mousemove', e => {
    const r = canvas.getBoundingClientRect();
    nx = (e.clientX - r.left) / canvas.width;
    ny = (e.clientY - r.top)  / canvas.height;
  });

  canvas.addEventListener('click', e => {
    if (!active) return;
    send({ type: 'debug_spawn_powerup', powerup_type: selectedPowerup, x: nx, y: ny });
  });

  canvas.addEventListener('contextmenu', e => {
    if (!active) return;
    e.preventDefault();
    send({ type: 'debug_teleport_ball', x: nx, y: ny });
  });

  window.addEventListener('keydown', e => {
    if (e.code === 'Backquote') {
      active = !active;
      e.preventDefault();
      _sidebar.classList.toggle('active', active);
      if (!active && mouseBallOn) {
        mouseBallOn = false;
        send({ type: 'debug_mouse_active', active: false });
      }
      return;
    }
    if (!active) return;

    if (e.code === 'KeyZ') { showZones = !showZones; }
    if (e.code === 'KeyG') { send({ type: 'debug_toggle_freeze' }); }
    if (e.code === 'KeyB') { send({ type: 'debug_add_ball' }); }
    if (e.code === 'KeyN') { send({ type: 'debug_remove_ball' }); }
    if (e.code === 'KeyM') {
      mouseBallOn = !mouseBallOn;
      send({ type: 'debug_mouse_active', active: mouseBallOn });
    }
    for (let i = 0; i < POWERUP_TYPES.length; i++) {
      if (e.code === `Digit${i + 1}`) { _selectPowerup(POWERUP_TYPES[i]); }
    }
  });
}

// ── Main tick ─────────────────────────────────────────────────────────────────

export function debugTick() {
  if (!active) return;

  if (mouseBallOn) {
    send({ type: 'debug_mouse_move', x: nx, y: ny });
  }

  const S  = canvas.width;
  const st = state.server;
  const go = st.goal_offsets || [0, 0, 0, 0];

  const fm = FIELD_MARGIN;
  const gH = GOAL_HALF_H;
  const gV = GOAL_HALF_V;
  const r  = BALL_R;

  const sides = [
    { label: 'TOPO',     elim: st.eliminated?.[0] ?? false,
      inGoal: (ny - r) < fm          && Math.abs(nx - 0.5 - go[0]) <= gH,
      scored: (ny - r) < fm - 2*r    && Math.abs(nx - 0.5 - go[0]) <= gH },
    { label: 'BAIXO',    elim: st.eliminated?.[1] ?? false,
      inGoal: (ny + r) > (1 - fm)        && Math.abs(nx - 0.5 - go[1]) <= gH,
      scored: (ny + r) > (1 - fm) + 2*r  && Math.abs(nx - 0.5 - go[1]) <= gH },
    { label: 'ESQUERDA', elim: st.eliminated?.[2] ?? false,
      inGoal: (nx - r) < fm          && Math.abs(ny - 0.5 - go[2]) <= gV,
      scored: (nx - r) < fm - 2*r    && Math.abs(ny - 0.5 - go[2]) <= gV },
    { label: 'DIREITA',  elim: st.eliminated?.[3] ?? false,
      inGoal: (nx + r) > (1 - fm)        && Math.abs(ny - 0.5 - go[3]) <= gV,
      scored: (nx + r) > (1 - fm) + 2*r  && Math.abs(ny - 0.5 - go[3]) <= gV },
  ];

  const activeGoal   = sides.find(s => !s.elim && s.scored);
  const activeInGoal = sides.find(s => !s.elim && s.inGoal);

  const mouseBallId = st.debug_mouse_ball_id;
  const mouseBall   = mouseBallId != null
    ? (st.balls || []).find(b => b.id === mouseBallId) ?? null
    : null;

  if (showZones) {
    _drawZones(S, fm, gH, gV, go, st.eliminated ?? [false, false, false, false]);
  }

  _drawCursor(S, activeGoal, activeInGoal, mouseBall);
  _updateStatus(activeGoal, activeInGoal, mouseBall);
}

// ── Canvas drawing ────────────────────────────────────────────────────────────

function _drawCursor(S, activeGoal, activeInGoal, mouseBall) {
  const bx = nx * S;
  const by = ny * S;
  const br = BALL_R * S;

  let ballColor = '#00ffaa';
  if (mouseBall) {
    if (mouseBall.boosted)  ballColor = '#ffd93d';
    if (mouseBall.snitched) ballColor = '#c77dff';
  }
  if (activeGoal)                   ballColor = '#ff3333';
  if (activeInGoal && !activeGoal)  ballColor = '#ffbb00';

  ctx.save();

  const glowR = mouseBall?.boosted ? br * 3.5 : br * 2.5;
  const glow  = ctx.createRadialGradient(bx, by, 0, bx, by, glowR);
  glow.addColorStop(0, ballColor + '66');
  glow.addColorStop(1, ballColor + '00');
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(bx, by, glowR, 0, Math.PI * 2); ctx.fill();

  if (mouseBall?.snitched) {
    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(performance.now() / 300);
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = '#c77dff';
    ctx.lineWidth   = 2;
    ctx.globalAlpha = 0.8;
    ctx.beginPath(); ctx.arc(0, 0, br * 1.8, 0, Math.PI * 2); ctx.stroke();
    ctx.restore();
  }

  const grad = ctx.createRadialGradient(bx - br*0.3, by - br*0.3, br*0.05, bx, by, br);
  grad.addColorStop(0, '#ffffff');
  grad.addColorStop(1, ballColor);
  ctx.fillStyle = grad;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();

  ctx.strokeStyle = ballColor;
  ctx.lineWidth   = 1.5;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.stroke();

  ctx.setLineDash([3, 3]);
  ctx.strokeStyle = 'rgba(255,255,255,0.35)';
  ctx.lineWidth   = 1;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.stroke();
  ctx.setLineDash([]);

  if (mouseBallOn) {
    ctx.fillStyle    = '#ffffff';
    ctx.font         = 'bold 9px monospace';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', bx, by);
    ctx.textBaseline = 'alphabetic';
  }

  ctx.restore();

  // Powerup spawn radius preview
  if (!mouseBallOn) {
    const puColor = POWERUP_COLORS[selectedPowerup] || '#ffffff';
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.strokeStyle = puColor;
    ctx.lineWidth   = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(bx, by, 0.038 * S, 0, Math.PI * 2); ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }
}

function _drawZones(S, fm, gH, gV, go, elim) {
  const r = BALL_R;
  ctx.save();

  ctx.fillStyle = 'rgba(255,180,0,0.22)';
  if (!elim[0]) ctx.fillRect((0.5+go[0]-gH)*S, (fm-2*r)*S,   gH*2*S, 2*r*S);
  if (!elim[1]) ctx.fillRect((0.5+go[1]-gH)*S, (1-fm)*S,     gH*2*S, 2*r*S);
  if (!elim[2]) ctx.fillRect((fm-2*r)*S, (0.5+go[2]-gV)*S,   2*r*S,  gV*2*S);
  if (!elim[3]) ctx.fillRect((1-fm)*S,   (0.5+go[3]-gV)*S,   2*r*S,  gV*2*S);

  ctx.fillStyle = 'rgba(255,0,0,0.28)';
  if (!elim[0]) ctx.fillRect((0.5+go[0]-gH)*S, 0,            gH*2*S, (fm-2*r)*S);
  if (!elim[1]) ctx.fillRect((0.5+go[1]-gH)*S, (1-fm+2*r)*S, gH*2*S, S);
  if (!elim[2]) ctx.fillRect(0,                (0.5+go[2]-gV)*S, (fm-2*r)*S, gV*2*S);
  if (!elim[3]) ctx.fillRect((1-fm+2*r)*S,     (0.5+go[3]-gV)*S, S,          gV*2*S);

  ctx.restore();
}
