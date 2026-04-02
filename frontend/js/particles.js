/**
 * Fire particle system — self-contained; renderer calls spawnFire and
 * updateAndDrawFire each frame.
 */

const _particles = [];

export function spawnFire(bx, by, vx, vy) {
  const baseAngle = Math.atan2(-vy, -vx);
  for (let i = 0; i < 4; i++) {
    const angle = baseAngle + (Math.random() - 0.5) * 1.1;
    const spd   = 1.8 + Math.random() * 2.2;
    _particles.push({
      x:    bx + (Math.random() - 0.5) * 4,
      y:    by + (Math.random() - 0.5) * 4,
      vx:   Math.cos(angle) * spd,
      vy:   Math.sin(angle) * spd,
      life: 1.0,
      size: 3.5 + Math.random() * 3.5,
    });
  }
}

export function updateAndDrawFire(ctx) {
  for (let i = _particles.length - 1; i >= 0; i--) {
    const p = _particles[i];
    p.x    += p.vx;
    p.y    += p.vy;
    p.vy   += 0.04;     // slight gravity
    p.life -= 0.045;
    if (p.life <= 0) { _particles.splice(i, 1); continue; }
    const g = Math.floor(200 * p.life * p.life);
    ctx.globalAlpha = p.life * 0.85;
    ctx.fillStyle   = `rgb(255,${g},0)`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

export function clearParticles() {
  _particles.length = 0;
}
