/**
 * Renderer — owns the canvas element and all drawing logic.
 * Reads state for game data; does not write to state.
 */
import {
  FIELD_MARGIN, PADDLE_THICK, PADDLE_LEN_H, PADDLE_LEN_V,
  BALL_R, GOAL_DEPTH, GOAL_HALF_H, GOAL_HALF_V, POWERUP_RADIUS, PORTAL_RADIUS,
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

  for (const pu of (st.powerups || [])) _drawPowerup(pu, S);
  _drawPortals(st.portals || [], S);

  _drawPaddles(st, pt, fT, fB, fL, fR, S);
  updateAndDrawFire(ctx);
  _drawBalls(st, S);
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

function _drawGoalPockets(st, S, fT, fB, fL, fR, gd, gwH, gwV, go) {
  const bg = (st.goal_moving) ? '#6a3080' : '#7a2030';
  if (st.names[0] && !st.eliminated[0]) { const x=S*(0.5+go[0])-gwH, y=fT-gd, w=gwH*2, h=gd+4; ctx.fillStyle=bg; _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'top'); }
  if (st.names[1] && !st.eliminated[1]) { const x=S*(0.5+go[1])-gwH, y=fB-4,  w=gwH*2, h=gd+4; ctx.fillStyle=bg; _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'bottom'); }
  if (st.names[2] && !st.eliminated[2]) { const x=fL-gd, y=S*(0.5+go[2])-gwV, w=gd+4, h=gwV*2; ctx.fillStyle=bg; _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'left'); }
  if (st.names[3] && !st.eliminated[3]) { const x=fR-4,  y=S*(0.5+go[3])-gwV, w=gd+4, h=gwV*2; ctx.fillStyle=bg; _rrFill(x,y,w,h,6); _drawNetLines(x,y,w,h,'right'); }
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
  if (st.names[0]) _drawPadH(dp[0]*S, fT+pt*0.5, PADDLE_LEN_H*S, pt, st.eliminated[0], state.mySlot === 0);
  if (st.names[1]) _drawPadH(dp[1]*S, fB-pt*0.5, PADDLE_LEN_H*S, pt, st.eliminated[1], state.mySlot === 1);
  if (st.names[2]) _drawPadV(fL+pt*0.5, dp[2]*S, pt, PADDLE_LEN_V*S, st.eliminated[2], state.mySlot === 2);
  if (st.names[3]) _drawPadV(fR-pt*0.5, dp[3]*S, pt, PADDLE_LEN_V*S, st.eliminated[3], state.mySlot === 3);
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

  _drawSinglePortal(x0, y0, PORTAL_RADIUS * S, t);
  _drawSinglePortal(x1, y1, PORTAL_RADIUS * S, t);
}

function _drawSinglePortal(x, y, r, t) {
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
