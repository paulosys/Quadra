/**
 * Renderer — owns the canvas element and all drawing logic.
 * Reads state for game data; does not write to state.
 */
import {
  FIELD_MARGIN, PADDLE_THICK, PADDLE_LEN_H, PADDLE_LEN_V,
  BALL_R, GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V, POWERUP_RADIUS, PORTAL_RADIUS,
  HURRICANE_RADIUS, PULSE_RADIUS_NORMAL, PULSE_RADIUS_PERFECT, PULSE_COOLDOWN_SECS,
} from './config.js';
import { state } from './state.js';
import { spawnFire, updateAndDrawFire } from './particles.js';

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

export function resize() {
  const maxW = Math.min(window.innerWidth - 16, 700);
  const maxH = window.innerHeight - 320;
  const sz   = Math.min(maxW, maxH, 620);
  canvas.width  = sz;
  canvas.height = sz;
  document.getElementById('pq-bar').style.maxWidth = sz + 'px';
}

export function draw() {
  const S  = canvas.width;
  const st = state.server;

  _interpolatePaddles(st, S);
  _syncBallDisplayMap(st);

  ctx.clearRect(0, 0, S, S);
  ctx.fillStyle = '#080808';
  ctx.fillRect(0, 0, S, S);

  const fm  = FIELD_MARGIN;
  const fL  = fm * S,  fR = (1 - fm) * S;
  const fT  = fm * S,  fB = (1 - fm) * S;
  const fW  = fR - fL, fH = fB - fT;
  const gd  = GOAL_DEPTH  * S;
  const gwH = GOAL_HALF_H * S;
  const gwV = GOAL_HALF_V * S;
  const pt  = PADDLE_THICK * S;
  const go  = st.goal_offsets || [0, 0, 0, 0];

  _drawGoalPockets(st, S, fT, fB, fL, fR, gd, gwH, gwV, go);
  _drawField(fL, fT, fR, fB, fW, fH, S);
  _drawFieldBorder(fL, fT, fW, fH);
  _eraseGoalBorders(st, S, fT, fB, fL, fR, gwH, gwV, go);

  if (st.hurricane_active) _drawHurricane(S, Date.now());
  for (const pu of (st.powerups || [])) _drawPowerup(pu, S);
  _drawPortals(st.portals || [], S);
  _drawCornerPowerups(st, S, fm);

  _drawPaddles(st, pt, fT, fB, fL, fR, S);
  _drawPulseReadiness(st, fT, fB, fL, fR, S);
  _drawPulseEffects(fT, fB, fL, fR, S);
  updateAndDrawFire(ctx);
  if (state.kickoff) {
    _drawKickoff(S, st);
  } else {
    _drawBalls(st, S);
  }
}

// ── Private drawing helpers ────────────────────────────────────────────────────

function _interpolatePaddles(st, S) {
  for (let i = 0; i < 4; i++)
    if (st.names[i]) state.displayPads[i] = _lerp(state.displayPads[i], st.paddles[i], 0.45);
  if (state.mySlot >= 0)
    state.displayPads[state.mySlot] = state.localPadPos;
}

function _syncBallDisplayMap(st) {
  const activeIds = new Set((st.balls || []).map(b => b.id));
  for (const id of state.displayBallMap.keys()) {
    if (!activeIds.has(id)) state.displayBallMap.delete(id);
  }
  for (const b of (st.balls || [])) {
    if (!state.displayBallMap.has(b.id)) {
      state.displayBallMap.set(b.id, { x: b.x, y: b.y });
    } else {
      const d = state.displayBallMap.get(b.id);
      d.x = _lerp(d.x, b.x, 0.35);
      d.y = _lerp(d.y, b.y, 0.35);
    }
  }
}

function _goalBg(st, slot) {
  const cornerActive = st.corner_goals_active && st.corner_goals_active[slot];
  return (st.goal_moving || cornerActive) ? '#6a3080' : '#7a2030';
}

function _drawGoalPockets(st, S, fT, fB, fL, fR, gd, gwH, gwV, go) {
  if (st.names[0] && !st.eliminated[0]) { const x=S*(0.5+go[0])-gwH, y=fT-gd, w=gwH*2, h=gd+4; ctx.fillStyle=_goalBg(st,0); _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'top'); }
  if (st.names[1] && !st.eliminated[1]) { const x=S*(0.5+go[1])-gwH, y=fB-4,  w=gwH*2, h=gd+4; ctx.fillStyle=_goalBg(st,1); _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'bottom'); }
  if (st.names[2] && !st.eliminated[2]) { const x=fL-gd, y=S*(0.5+go[2])-gwV, w=gd+4, h=gwV*2; ctx.fillStyle=_goalBg(st,2); _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'left'); }
  if (st.names[3] && !st.eliminated[3]) { const x=fR-4,  y=S*(0.5+go[3])-gwV, w=gd+4, h=gwV*2; ctx.fillStyle=_goalBg(st,3); _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'right'); }
}

function _drawNetLines(x, y, w, h, side) {
  const sp = Math.max(6, Math.round(Math.min(w, h) * 0.17));
  ctx.save();
  _rrPath(x, y, w, h, 6);
  ctx.clip();

  // Horizontal lines
  for (let gy = y + sp; gy < y + h - 1; gy += sp) {
    let t = (side === 'top')    ? 1 - (gy - y) / h
          : (side === 'bottom') ? (gy - y) / h
          : 0.55;
    ctx.strokeStyle = `rgba(255,255,255,${(0.13 + t * 0.2).toFixed(2)})`;
    ctx.lineWidth = 0.9;
    ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x + w, gy); ctx.stroke();
  }

  // Vertical lines
  for (let gx = x + sp; gx < x + w - 1; gx += sp) {
    let t = (side === 'left')  ? 1 - (gx - x) / w
          : (side === 'right') ? (gx - x) / w
          : 0.55;
    ctx.strokeStyle = `rgba(255,255,255,${(0.13 + t * 0.2).toFixed(2)})`;
    ctx.lineWidth = 0.9;
    ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y + h); ctx.stroke();
  }

  // Back-wall bright line (deepest edge)
  ctx.strokeStyle = 'rgba(255,255,255,0.45)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (side === 'top')    { ctx.moveTo(x + 4, y + 2);     ctx.lineTo(x + w - 4, y + 2); }
  if (side === 'bottom') { ctx.moveTo(x + 4, y + h - 2); ctx.lineTo(x + w - 4, y + h - 2); }
  if (side === 'left')   { ctx.moveTo(x + 2, y + 4);     ctx.lineTo(x + 2, y + h - 4); }
  if (side === 'right')  { ctx.moveTo(x + w - 2, y + 4); ctx.lineTo(x + w - 2, y + h - 4); }
  ctx.stroke();

  ctx.restore();
}

function _drawField(fL, fT, fR, fB, fW, fH, S) {
  ctx.save();
  ctx.beginPath(); _rrPath(fL, fT, fW, fH, 10); ctx.clip();
  ctx.fillStyle = '#0d3d20'; ctx.fill();
  ctx.strokeStyle = 'rgba(0,80,30,.35)'; ctx.lineWidth = 0.5;
  for (let x = fL; x <= fR; x += 20) { ctx.beginPath(); ctx.moveTo(x, fT); ctx.lineTo(x, fB); ctx.stroke(); }
  for (let y = fT; y <= fB; y += 20) { ctx.beginPath(); ctx.moveTo(fL, y); ctx.lineTo(fR, y); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(255,255,255,.07)'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(S * 0.5, S * 0.5, fW * 0.14, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
}

function _drawFieldBorder(fL, fT, fW, fH) {
  ctx.strokeStyle = '#c0c0b8'; ctx.lineWidth = 2;
  ctx.beginPath(); _rrPath(fL, fT, fW, fH, 10); ctx.stroke();
}

function _eraseGoalBorders(st, S, fT, fB, fL, fR, gwH, gwV, go) {
  ctx.strokeStyle = '#0d3d20'; ctx.lineWidth = 3.5;
  if (st.names[0] && !st.eliminated[0]) { ctx.beginPath(); ctx.moveTo(S*(0.5+go[0])-gwH+1, fT); ctx.lineTo(S*(0.5+go[0])+gwH-1, fT); ctx.stroke(); }
  if (st.names[1] && !st.eliminated[1]) { ctx.beginPath(); ctx.moveTo(S*(0.5+go[1])-gwH+1, fB); ctx.lineTo(S*(0.5+go[1])+gwH-1, fB); ctx.stroke(); }
  if (st.names[2] && !st.eliminated[2]) { ctx.beginPath(); ctx.moveTo(fL, S*(0.5+go[2])-gwV+1); ctx.lineTo(fL, S*(0.5+go[2])+gwV-1); ctx.stroke(); }
  if (st.names[3] && !st.eliminated[3]) { ctx.beginPath(); ctx.moveTo(fR, S*(0.5+go[3])-gwV+1); ctx.lineTo(fR, S*(0.5+go[3])+gwV-1); ctx.stroke(); }
}

function _drawPaddles(st, pt, fT, fB, fL, fR, S) {
  const dp = state.displayPads;
  const lm = st.paddle_len_mult || [1, 1, 1, 1];
  if (st.names[0]) _drawPadH(dp[0]*S, fT+pt*0.5, PADDLE_LEN_H*lm[0]*S, pt, st.eliminated[0], state.mySlot === 0);
  if (st.names[1]) _drawPadH(dp[1]*S, fB-pt*0.5, PADDLE_LEN_H*lm[1]*S, pt, st.eliminated[1], state.mySlot === 1);
  if (st.names[2]) _drawPadV(fL+pt*0.5, dp[2]*S, pt, PADDLE_LEN_V*lm[2]*S, st.eliminated[2], state.mySlot === 2);
  if (st.names[3]) _drawPadV(fR-pt*0.5, dp[3]*S, pt, PADDLE_LEN_V*lm[3]*S, st.eliminated[3], state.mySlot === 3);
}

function _drawBalls(st, S) {
  for (const b of (st.balls || [])) {
    const disp = state.displayBallMap.get(b.id) || { x: b.x, y: b.y };
    const bx = disp.x * S, by = disp.y * S, br = BALL_R * S;

    if (b.snitched) {
      _drawSnitch(bx, by, br);
      continue;
    }

    if (b.boosted) spawnFire(bx, by, b.vx * S * 60, b.vy * S * 60);

    if (b.boosted) {
      const glow = ctx.createRadialGradient(bx, by, 0, bx, by, br * 3);
      glow.addColorStop(0, 'rgba(255,160,0,0.55)');
      glow.addColorStop(1, 'rgba(255,80,0,0)');
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(bx, by, br * 3, 0, Math.PI * 2); ctx.fill();
    }

    const bg = ctx.createRadialGradient(bx - br * 0.3, by - br * 0.3, br * 0.05, bx, by, br);
    bg.addColorStop(0,  '#ffffff');
    bg.addColorStop(0.6,'#e8e8e0');
    bg.addColorStop(1,  b.boosted ? '#ff8800' : '#aaaaaa');
    ctx.fillStyle = bg;
    ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();
  }
}

function _drawSnitch(bx, by, br) {
  const t    = Date.now();
  const flap = Math.sin(t / 70);   // fast wing flap
  const shimmer = Math.sin(t / 400) * 0.5 + 0.5;

  // Golden outer glow
  const glow = ctx.createRadialGradient(bx, by, 0, bx, by, br * 4);
  glow.addColorStop(0,   `rgba(255,215,0,${0.35 + shimmer * 0.15})`);
  glow.addColorStop(0.5, 'rgba(255,180,0,0.12)');
  glow.addColorStop(1,   'rgba(255,140,0,0)');
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(bx, by, br * 4, 0, Math.PI * 2); ctx.fill();

  ctx.save();

  // Wings (drawn behind the ball)
  const wingW  = br * 2.8;
  const wingH  = br * (1.1 + Math.abs(flap) * 1.2);
  const tiltY  = flap * br * 0.4;

  ctx.globalAlpha = 0.82;

  // Left wing
  ctx.save();
  ctx.translate(bx - br * 1.6, by + tiltY);
  ctx.rotate(-Math.PI / 8 + flap * 0.18);
  const lwg = ctx.createRadialGradient(-wingW * 0.3, 0, 0, -wingW * 0.3, 0, wingW * 0.9);
  lwg.addColorStop(0, 'rgba(255,255,220,0.95)');
  lwg.addColorStop(0.5, 'rgba(240,210,120,0.7)');
  lwg.addColorStop(1,   'rgba(200,160,50,0)');
  ctx.fillStyle = lwg;
  ctx.beginPath(); ctx.ellipse(0, 0, wingW * 0.85, wingH * 0.55, 0, 0, Math.PI * 2); ctx.fill();
  // Wing feather lines
  ctx.strokeStyle = 'rgba(200,170,80,0.4)'; ctx.lineWidth = 0.8;
  for (let i = 1; i <= 3; i++) {
    const fx = -wingW * 0.7 * (i / 3.5);
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(fx, -wingH * 0.45); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(fx, wingH * 0.45); ctx.stroke();
  }
  ctx.restore();

  // Right wing
  ctx.save();
  ctx.translate(bx + br * 1.6, by + tiltY);
  ctx.rotate(Math.PI / 8 - flap * 0.18);
  const rwg = ctx.createRadialGradient(wingW * 0.3, 0, 0, wingW * 0.3, 0, wingW * 0.9);
  rwg.addColorStop(0, 'rgba(255,255,220,0.95)');
  rwg.addColorStop(0.5, 'rgba(240,210,120,0.7)');
  rwg.addColorStop(1,   'rgba(200,160,50,0)');
  ctx.fillStyle = rwg;
  ctx.beginPath(); ctx.ellipse(0, 0, wingW * 0.85, wingH * 0.55, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = 'rgba(200,170,80,0.4)'; ctx.lineWidth = 0.8;
  for (let i = 1; i <= 3; i++) {
    const fx = wingW * 0.7 * (i / 3.5);
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(fx, -wingH * 0.45); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(fx, wingH * 0.45); ctx.stroke();
  }
  ctx.restore();

  ctx.globalAlpha = 1.0;

  // Golden ball body
  const bg = ctx.createRadialGradient(bx - br * 0.3, by - br * 0.35, br * 0.05, bx, by, br);
  bg.addColorStop(0,   '#fffde0');
  bg.addColorStop(0.4, '#ffd700');
  bg.addColorStop(0.8, '#c8900a');
  bg.addColorStop(1,   '#7a5200');
  ctx.fillStyle = bg;
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();

  // Specular highlight
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.beginPath(); ctx.ellipse(bx - br * 0.28, by - br * 0.32, br * 0.28, br * 0.18, -Math.PI / 4, 0, Math.PI * 2); ctx.fill();

  ctx.restore();
}

function _drawPortals(portals, S) {
  if (!portals || portals.length < 2) return;
  const t  = Date.now();
  const x0 = portals[0].x * S, y0 = portals[0].y * S;
  const x1 = portals[1].x * S, y1 = portals[1].y * S;

  // Dashed connecting beam between the two portals
  ctx.save();
  const pulse = Math.sin(t / 500) * 0.5 + 0.5;
  ctx.strokeStyle = `rgba(180,80,255,${(0.12 + pulse * 0.08).toFixed(2)})`;
  ctx.lineWidth   = 1.5;
  ctx.setLineDash([5, 9]);
  ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();

  _drawSinglePortal(x0, y0, PORTAL_RADIUS * S, t, portals[0].rotation ?? 0);
  _drawSinglePortal(x1, y1, PORTAL_RADIUS * S, t, portals[1].rotation ?? 0);
}

function _drawSinglePortal(x, y, r, t, rotation) {
  const spin  = (t / 900) % (Math.PI * 2);
  const pulse = Math.sin(t / 450) * 0.5 + 0.5;
  const pr    = r * (1 + 0.08 * Math.sin(t / 650));

  ctx.save();

  // Outer glow
  const glow = ctx.createRadialGradient(x, y, 0, x, y, pr * 2.2);
  glow.addColorStop(0,   `rgba(160,60,255,${(0.28 + pulse * 0.12).toFixed(2)})`);
  glow.addColorStop(0.6, 'rgba(100,30,200,0.08)');
  glow.addColorStop(1,   'rgba(60,0,180,0)');
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(x, y, pr * 2.2, 0, Math.PI * 2); ctx.fill();

  ctx.translate(x, y);

  // Two spinning arcs (purple + cyan, opposite halves)
  ctx.rotate(spin);
  ctx.lineWidth   = 2.5;
  ctx.shadowBlur  = 10;
  ctx.strokeStyle = `rgba(220,130,255,${(0.65 + pulse * 0.25).toFixed(2)})`;
  ctx.shadowColor = '#c060ff';
  ctx.beginPath(); ctx.arc(0, 0, pr * 0.72, 0, Math.PI * 1.35); ctx.stroke();
  ctx.rotate(Math.PI);
  ctx.strokeStyle = `rgba(100,210,255,${(0.65 + pulse * 0.25).toFixed(2)})`;
  ctx.shadowColor = '#40c0ff';
  ctx.beginPath(); ctx.arc(0, 0, pr * 0.72, 0, Math.PI * 1.35); ctx.stroke();
  ctx.shadowBlur  = 0;
  ctx.rotate(-spin - Math.PI);

  // Outer ring
  ctx.strokeStyle = `rgba(200,90,255,${(0.80 + pulse * 0.15).toFixed(2)})`;
  ctx.lineWidth   = 2;
  ctx.shadowColor = '#9030ff';
  ctx.shadowBlur  = 14;
  ctx.beginPath(); ctx.arc(0, 0, pr, 0, Math.PI * 2); ctx.stroke();

  // Exit-direction arrow (yellow, points where the ball will go)
  const arrowAlpha = (0.80 + pulse * 0.20).toFixed(2);
  const shaft      = pr * 0.80;
  const head       = pr * 0.30;
  ctx.save();
  ctx.rotate(rotation);
  ctx.shadowColor  = '#ffff40';
  ctx.shadowBlur   = 12;
  ctx.strokeStyle  = `rgba(255,255,80,${arrowAlpha})`;
  ctx.fillStyle    = `rgba(255,255,80,${arrowAlpha})`;
  ctx.lineWidth    = 2.5;
  ctx.lineCap      = 'round';
  ctx.beginPath();
  ctx.moveTo(-shaft * 0.1, 0);
  ctx.lineTo(shaft, 0);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(shaft, 0);
  ctx.lineTo(shaft - head, -head * 0.45);
  ctx.lineTo(shaft - head, head * 0.45);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  ctx.restore();
}

function _drawHurricane(S, t) {
  const cx   = S * 0.5, cy = S * 0.5;
  const r    = HURRICANE_RADIUS * S;
  const spin = (t / 1600) % (Math.PI * 2);

  ctx.save();

  // Subtle tinted field area
  const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
  halo.addColorStop(0,   'rgba(0,200,180,0.10)');
  halo.addColorStop(0.6, 'rgba(0,160,140,0.05)');
  halo.addColorStop(1,   'rgba(0,80,60,0)');
  ctx.fillStyle = halo;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();

  ctx.translate(cx, cy);

  // 3 spiral arms rotating clockwise
  for (let arm = 0; arm < 3; arm++) {
    ctx.save();
    ctx.rotate(spin + (arm * Math.PI * 2 / 3));
    const alpha = 0.18 + 0.07 * Math.sin(t / 700 + arm);
    ctx.strokeStyle = `rgba(0,220,200,${alpha.toFixed(2)})`;
    ctx.lineWidth   = 2.5;
    ctx.shadowColor = '#00ddcc';
    ctx.shadowBlur  = 10;
    ctx.beginPath();
    const steps = 64;
    for (let i = 0; i <= steps; i++) {
      const frac  = i / steps;
      const rad   = frac * r * 0.82;
      const angle = frac * Math.PI * 1.6;
      const px    = Math.cos(angle) * rad;
      const py    = Math.sin(angle) * rad;
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();
  }
  ctx.shadowBlur = 0;

  // Eye — small glowing dot at center
  const eyeR = r * 0.055;
  const eye  = ctx.createRadialGradient(0, 0, 0, 0, 0, eyeR);
  eye.addColorStop(0,   'rgba(200,255,250,0.75)');
  eye.addColorStop(0.5, 'rgba(0,200,180,0.4)');
  eye.addColorStop(1,   'rgba(0,120,100,0)');
  ctx.fillStyle = eye;
  ctx.beginPath(); ctx.arc(0, 0, eyeR, 0, Math.PI * 2); ctx.fill();

  ctx.restore();
}

function _drawPowerup(pu, S) {
  const x  = pu.x * S, y = pu.y * S;
  const r  = POWERUP_RADIUS * S;
  const pr = r * (1 + 0.12 * Math.sin(Date.now() / 900));

  ctx.save();
  const styles = {
    double:     { fill: 'rgba(68,170,255,0.18)',  stroke: '#4af',    shadow: '#4af',    label: '2X', font: `bold ${Math.floor(pr)}px 'Bebas Neue', sans-serif` },
    movinggoal: { fill: 'rgba(180,80,255,0.18)',   stroke: '#b45fff', shadow: '#b45fff', label: '↔', font: `${Math.floor(pr * 1.1)}px Arial` },
    speed:      { fill: 'rgba(255,136,0,0.18)',    stroke: '#f80',    shadow: '#f80',    label: '⚡', font: `${Math.floor(pr * 1.2)}px Arial` },
    snitch:     { fill: 'rgba(255,215,0,0.18)',    stroke: '#ffd700', shadow: '#ffd700', label: '✦', font: `${Math.floor(pr * 1.15)}px Arial` },
    portal:     { fill: 'rgba(160,60,255,0.18)',   stroke: '#a040ff', shadow: '#a040ff', label: '◈', font: `${Math.floor(pr * 1.1)}px Arial` },
    hurricane:  { fill: 'rgba(0,200,180,0.18)',    stroke: '#00c8b4', shadow: '#00c8b4', label: '🌀', font: `${Math.floor(pr * 1.1)}px Arial` },
    ghostgoal:  { fill: 'rgba(255,215,0,0.18)',    stroke: '#ffdd00', shadow: '#ffdd00', label: '⚽', font: `${Math.floor(pr * 1.1)}px Arial` },
  };
  const s = styles[pu.type] || styles.speed;
  ctx.fillStyle   = s.fill;
  ctx.strokeStyle = s.stroke;
  ctx.shadowColor = s.shadow;
  ctx.shadowBlur  = 12;
  ctx.lineWidth   = 2;
  ctx.beginPath(); ctx.arc(x, y, pr, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.shadowBlur      = 0;
  ctx.fillStyle       = s.stroke;
  ctx.font            = s.font;
  ctx.textAlign       = 'center';
  ctx.textBaseline    = 'middle';
  ctx.fillText(s.label, x, y);
  ctx.restore();
}

function _paddleCenter(slot, fT, fB, fL, fR) {
  const dp = state.displayPads;
  const S  = fR / (1 - FIELD_MARGIN);   // recover S from fR
  switch (slot) {
    case 0: return { x: dp[0] * S, y: fT };
    case 1: return { x: dp[1] * S, y: fB };
    case 2: return { x: fL,        y: dp[2] * S };
    case 3: return { x: fR,        y: dp[3] * S };
  }
}

function _nearestBallDist(slot, st) {
  const balls = st.balls || [];
  if (!balls.length) return Infinity;
  const isH    = slot <= 1;
  const wall   = (slot === 0 || slot === 2) ? FIELD_MARGIN : 1.0 - FIELD_MARGIN;
  const padPos = (st.paddles || [0.5, 0.5, 0.5, 0.5])[slot];
  const half   = isH ? PADDLE_LEN_H / 2 : PADDLE_LEN_V / 2;
  let best = Infinity;
  for (const b of balls) {
    const pos  = isH ? b.y : b.x;
    const perp = isH ? b.x : b.y;
    const dist = Math.abs(pos - wall);
    if (Math.abs(perp - padPos) <= half * 2.5 && dist < best) best = dist;
  }
  return best;
}

function _drawPulseReadiness(st, fT, fB, fL, fR, S) {
  if (state.mySlot < 0 || state.gameState !== 'playing') return;
  if ((st.eliminated || [])[state.mySlot]) return;

  const ready = (Date.now() - state.pulseLastFired) / 1000 >= PULSE_COOLDOWN_SECS;
  const lm    = st.paddle_len_mult || [1, 1, 1, 1];
  const isH   = state.mySlot <= 1;
  const len   = (isH ? PADDLE_LEN_H : PADDLE_LEN_V) * lm[state.mySlot] * S;
  const pt    = PADDLE_THICK * S;
  const { x, y } = _paddleCenter(state.mySlot, fT, fB, fL, fR);

  if (!ready) {
    // Cooldown bar inside paddle
    const elapsed  = (Date.now() - state.pulseLastFired) / 1000;
    const fraction = Math.min(elapsed / PULSE_COOLDOWN_SECS, 1);
    const barLen   = len * fraction;
    const barH     = pt * 0.38;
    ctx.save();
    ctx.globalAlpha = 0.80;
    ctx.fillStyle   = '#3399ff';
    ctx.shadowColor = '#3399ff';
    ctx.shadowBlur  = 6;
    if (isH) {
      ctx.fillRect(x - barLen / 2, y - barH / 2, barLen, barH);
    } else {
      ctx.fillRect(x - barH / 2, y - barLen / 2, barH, barLen);
    }
    ctx.shadowBlur = 0;
    ctx.restore();
    return;
  }

  // Ready — proximity glow
  const dist = _nearestBallDist(state.mySlot, st);
  let glowColor;
  if      (dist <= PULSE_RADIUS_PERFECT) glowColor = 'rgba(255,215,0,0.70)';
  else if (dist <= PULSE_RADIUS_NORMAL)  glowColor = 'rgba(100,220,255,0.55)';
  else                                   glowColor = 'rgba(80,160,255,0.28)';

  ctx.save();
  ctx.shadowColor = glowColor;
  ctx.shadowBlur  = 14;
  ctx.strokeStyle = glowColor;
  ctx.lineWidth   = 2;
  if (isH) {
    _rrPath(x - len / 2 - 3, y - pt / 2 - 3, len + 6, pt + 6, 7);
  } else {
    _rrPath(x - pt / 2 - 3, y - len / 2 - 3, pt + 6, len + 6, 7);
  }
  ctx.stroke();
  ctx.shadowBlur = 0;
  ctx.restore();
}

function _drawPulseEffects(fT, fB, fL, fR, S) {
  const now = Date.now();
  state.pulseEffects = state.pulseEffects.filter(e => now - e.startTime < 550);

  // Per-slot: semicircle faces inward (toward field center)
  const ARCS = [
    [0,            Math.PI],        // slot 0 TOP    → lower half
    [Math.PI,      Math.PI * 2],    // slot 1 BOTTOM → upper half
    [-Math.PI / 2, Math.PI / 2],    // slot 2 LEFT   → right half
    [Math.PI / 2,  Math.PI * 1.5],  // slot 3 RIGHT  → left half
  ];

  for (const e of state.pulseEffects) {
    const progress = (now - e.startTime) / 550;
    const alpha    = (1 - progress) * (e.perfect ? 0.85 : 0.70);
    const r        = progress * S * 0.30;
    const lw       = Math.max(1, 3.5 * (1 - progress * 0.6));
    const { x, y } = _paddleCenter(e.slot, fT, fB, fL, fR);
    const [startA, endA] = ARCS[e.slot] || [0, Math.PI * 2];

    const color = e.perfect ? `rgba(255,215,0,${alpha.toFixed(2)})`
                : e.hit     ? `rgba(100,220,255,${alpha.toFixed(2)})`
                :              `rgba(140,140,140,${alpha.toFixed(2)})`;

    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, startA, endA);
    ctx.strokeStyle = color;
    ctx.lineWidth   = lw;
    if (e.perfect) { ctx.shadowColor = 'rgba(255,215,0,0.6)'; ctx.shadowBlur = 10; }
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();
  }
}

function _drawPadH(cx, cy, len, thick, elim, isMe) {
  const x = cx - len / 2, y = cy - thick / 2;
  ctx.fillStyle = elim ? '#181818' : '#7a2030'; _rrFill(x-4, y-2, len+8, thick+4, 6);
  ctx.fillStyle = elim ? '#2a2a2a' : isMe ? '#4a90d9' : '#2a6db5'; _rrFill(x, y, len, thick, 5);
  if (!elim) { ctx.fillStyle = 'rgba(255,255,255,.18)'; _rrFill(x+4, y+2, len-8, thick*0.35, 2); }
}

function _drawPadV(cx, cy, thick, len, elim, isMe) {
  const x = cx - thick / 2, y = cy - len / 2;
  ctx.fillStyle = elim ? '#181818' : '#7a2030'; _rrFill(x-2, y-4, thick+4, len+8, 6);
  ctx.fillStyle = elim ? '#2a2a2a' : isMe ? '#4a90d9' : '#2a6db5'; _rrFill(x, y, thick, len, 5);
  if (!elim) { ctx.fillStyle = 'rgba(255,255,255,.18)'; _rrFill(x+2, y+4, thick*0.35, len-8, 2); }
}

function _drawCornerPowerups(st, S, fm) {
  const cps = st.corner_powerups || [null, null, null, null];
  // Corner centres (normalized): TL, TR, BL, BR — centred in the margin area
  const cx = fm * 0.5, cy = fm * 0.5;
  const CORNER_POS = [
    { x: cx,     y: cy },
    { x: 1 - cx, y: cy },
    { x: cx,     y: 1 - cy },
    { x: 1 - cx, y: 1 - cy },
  ];
  // Owner slot pairs per corner (must match backend _CORNER_DEFS)
  const OWNER_COLORS = [
    ['#4a90d9', '#4a90d9'],  // TL: slot 0 + slot 2
    ['#4a90d9', '#4a90d9'],  // TR: slot 0 + slot 3
    ['#4a90d9', '#4a90d9'],  // BL: slot 1 + slot 2
    ['#4a90d9', '#4a90d9'],  // BR: slot 1 + slot 3
  ];

  const STYLES = {
    movinggoal: { stroke: '#b45fff', shadow: '#b45fff', label: '↔' },
  };

  const t  = Date.now();
  const r  = fm * 0.27 * S;

  for (let i = 0; i < 4; i++) {
    const cp = cps[i];
    if (!cp) continue;

    const px     = CORNER_POS[i].x * S;
    const py     = CORNER_POS[i].y * S;
    const charge = cp.charge || 0;
    const pulse  = Math.sin(t / 700) * 0.5 + 0.5;
    const pr     = r * (1 + 0.10 * pulse);
    const s      = STYLES[cp.type] || STYLES.movinggoal;

    ctx.save();

    // Background glow
    const glow = ctx.createRadialGradient(px, py, 0, px, py, pr * 2);
    glow.addColorStop(0,   `rgba(180,80,255,${(0.15 + pulse * 0.10).toFixed(2)})`);
    glow.addColorStop(1,   'rgba(100,0,180,0)');
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(px, py, pr * 2, 0, Math.PI * 2); ctx.fill();

    // Circle outline
    ctx.strokeStyle = s.stroke;
    ctx.shadowColor = s.shadow;
    ctx.shadowBlur  = 10;
    ctx.lineWidth   = charge > 0 ? 2.5 : 1.5;
    ctx.beginPath(); ctx.arc(px, py, pr, 0, Math.PI * 2); ctx.stroke();
    ctx.shadowBlur  = 0;

    // Icon label
    ctx.fillStyle    = s.stroke;
    ctx.font         = `bold ${Math.floor(pr * 1.05)}px Arial`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(s.label, px, py);

    // Charge arc (yellow ring that fills clockwise)
    if (charge > 0) {
      ctx.strokeStyle = charge >= 0.95 ? '#ffffff' : '#ffdd00';
      ctx.lineWidth   = 3;
      ctx.shadowColor = '#ffff00';
      ctx.shadowBlur  = 12;
      ctx.lineCap     = 'round';
      ctx.beginPath();
      ctx.arc(px, py, pr + 4, -Math.PI / 2, -Math.PI / 2 + charge * Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.lineCap    = 'butt';
    }

    ctx.restore();
  }
}

function _drawKickoff(S, st) {
  const ko      = state.kickoff;
  const cx      = S * 0.5, cy = S * 0.5;
  const t       = Date.now();
  const elapsed  = (t - ko.startTime) / 1000;
  const angle    = elapsed * ko.rotSpeed;
  const pulse    = Math.sin(t / 350) * 0.5 + 0.5;
  const r        = S * 0.065;
  const br       = BALL_R * S;
  const timeLeft = Math.max(0, ko.timeout - elapsed);
  const fraction = Math.max(0, timeLeft / ko.timeout);

  // ── Ball at centre ─────────────────────────────────────────────────────────
  const bg = ctx.createRadialGradient(cx - br * 0.3, cy - br * 0.3, br * 0.05, cx, cy, br);
  bg.addColorStop(0,   '#ffffff');
  bg.addColorStop(0.6, '#e8e8e0');
  bg.addColorStop(1,   '#aaaaaa');
  ctx.fillStyle = bg;
  ctx.beginPath(); ctx.arc(cx, cy, br, 0, Math.PI * 2); ctx.fill();

  // ── Rotating glow ring ─────────────────────────────────────────────────────
  ctx.save();
  ctx.strokeStyle = `rgba(255,220,50,${(0.22 + pulse * 0.14).toFixed(2)})`;
  ctx.lineWidth   = 2;
  ctx.shadowColor = '#ffd700';
  ctx.shadowBlur  = 18;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
  ctx.shadowBlur  = 0;
  ctx.restore();

  // ── Arrow (shaft + head) ───────────────────────────────────────────────────
  const shaft = r * 0.85;
  const head  = r * 0.32;
  const alpha = (0.85 + pulse * 0.15).toFixed(2);

  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);
  ctx.shadowColor = '#ffff40';
  ctx.shadowBlur  = 14;
  ctx.strokeStyle = `rgba(255,255,80,${alpha})`;
  ctx.lineWidth   = 3.5;
  ctx.lineCap     = 'round';
  ctx.beginPath();
  ctx.moveTo(br * 1.2, 0);
  ctx.lineTo(shaft, 0);
  ctx.stroke();
  ctx.fillStyle = `rgba(255,255,80,${alpha})`;
  ctx.beginPath();
  ctx.moveTo(shaft + head * 0.5, 0);
  ctx.lineTo(shaft - head * 0.35, -head * 0.48);
  ctx.lineTo(shaft - head * 0.35,  head * 0.48);
  ctx.closePath();
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.restore();

  // ── Label ──────────────────────────────────────────────────────────────────
  const isMe       = state.mySlot === ko.scorer;
  const scorerName = st.names[ko.scorer] || `Jogador ${ko.scorer + 1}`;
  ctx.save();
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'bottom';
  ctx.shadowColor  = '#000000';
  ctx.shadowBlur   = 8;
  if (isMe) {
    ctx.font      = `bold ${Math.floor(S * 0.042)}px 'Bebas Neue', sans-serif`;
    ctx.fillStyle = '#ffee55';
    ctx.fillText('CHUTE! (espaço / botão)', cx, cy - r - 8);
  } else {
    ctx.font      = `bold ${Math.floor(S * 0.038)}px 'Bebas Neue', sans-serif`;
    ctx.fillStyle = '#dddddd';
    ctx.fillText(`${scorerName} vai chutar…`, cx, cy - r - 8);
  }
  ctx.restore();

  // ── Progress bar inside scorer's paddle ────────────────────────────────────
  const fm  = FIELD_MARGIN;
  const fT  = fm * S, fB = (1 - fm) * S;
  const fL  = fm * S, fR = (1 - fm) * S;
  const pt  = PADDLE_THICK * S;
  const dp  = state.displayPads;
  const lm  = st.paddle_len_mult || [1, 1, 1, 1];
  const sc  = ko.scorer;
  const isH = sc <= 1;
  const padLen   = (isH ? PADDLE_LEN_H : PADDLE_LEN_V) * lm[sc] * S;
  const barLen   = padLen * fraction;
  const barH     = pt * 0.38;
  const hue      = fraction * 120;
  const barColor = `hsl(${hue.toFixed(0)},100%,58%)`;

  ctx.save();
  ctx.globalAlpha = 0.88;
  ctx.fillStyle   = barColor;
  ctx.shadowColor = barColor;
  ctx.shadowBlur  = 10;
  if (sc === 0) {
    ctx.fillRect(dp[sc]*S - barLen/2, fT + pt*0.5 - barH/2, barLen, barH);
  } else if (sc === 1) {
    ctx.fillRect(dp[sc]*S - barLen/2, fB - pt*0.5 - barH/2, barLen, barH);
  } else if (sc === 2) {
    ctx.fillRect(fL + pt*0.5 - barH/2, dp[sc]*S - barLen/2, barH, barLen);
  } else {
    ctx.fillRect(fR - pt*0.5 - barH/2, dp[sc]*S - barLen/2, barH, barLen);
  }
  ctx.shadowBlur = 0;
  ctx.restore();
}

function _rrPath(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y);
  ctx.quadraticCurveTo(x+w, y,   x+w, y+r);   ctx.lineTo(x+w, y+h-r);
  ctx.quadraticCurveTo(x+w, y+h, x+w-r, y+h); ctx.lineTo(x+r, y+h);
  ctx.quadraticCurveTo(x, y+h,   x, y+h-r);   ctx.lineTo(x, y+r);
  ctx.quadraticCurveTo(x, y,     x+r, y);      ctx.closePath();
}

function _rrFill(x, y, w, h, r) { _rrPath(x, y, w, h, r); ctx.fill(); }

function _lerp(a, b, t) { return a + (b - a) * t; }
