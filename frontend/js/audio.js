/**
 * AudioManager — thin wrapper around Web Audio API.
 * All sound logic is contained here; nothing else touches AudioContext.
 */

let _ctx = null;

function _getCtx() {
  if (!_ctx) {
    try { _ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (_) {}
  }
  return _ctx;
}

/** Must be called from a user gesture to unlock the AudioContext. */
export function unlockAudio() { _getCtx(); }

function _tone(freq, dur, type = 'sine', vol = 0.25, freqEnd = null) {
  const ctx = _getCtx(); if (!ctx) return;
  const osc  = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.type = type;
  osc.frequency.setValueAtTime(freq, ctx.currentTime);
  if (freqEnd) osc.frequency.exponentialRampToValueAtTime(freqEnd, ctx.currentTime + dur);
  gain.gain.setValueAtTime(vol, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
  osc.start();
  osc.stop(ctx.currentTime + dur);
}

export function playBounce() {
  _tone(520, 0.07, 'square', 0.12);
}

export function playGoal() {
  _tone(180, 0.35, 'sawtooth', 0.35);
  setTimeout(() => _tone(120, 0.45, 'sawtooth', 0.25), 220);
}

export function playPowerupCollect(type) {
  if (type === 'double') {
    _tone(600, 0.09, 'sine', 0.2);
    setTimeout(() => _tone(800,  0.09, 'sine', 0.2), 90);
    setTimeout(() => _tone(1050, 0.14, 'sine', 0.2), 180);
  } else if (type === 'snitch') {
    // Magical shimmer: rapid ascending arpeggio
    _tone(880,  0.08, 'sine', 0.18);
    setTimeout(() => _tone(1108, 0.08, 'sine', 0.18), 70);
    setTimeout(() => _tone(1320, 0.08, 'sine', 0.18), 140);
    setTimeout(() => _tone(1760, 0.18, 'sine', 0.22), 210);
    setTimeout(() => _tone(1320, 0.22, 'sine', 0.12, 440), 360);
  } else if (type === 'hurricane') {
    // Deep whooshing vortex
    _tone(80,  0.6, 'sawtooth', 0.22, 180);
    setTimeout(() => _tone(160, 0.5, 'sawtooth', 0.15, 80),  200);
    setTimeout(() => _tone(220, 0.4, 'sine',     0.18, 440), 350);
  } else {
    _tone(300, 0.28, 'sawtooth', 0.25, 900);
  }
}

let _hurricaneAmbientTick = 0;

export function tickHurricaneAmbient(active) {
  if (!active) { _hurricaneAmbientTick = 0; return; }
  _hurricaneAmbientTick--;
  if (_hurricaneAmbientTick > 0) return;
  _hurricaneAmbientTick = 96; // ~1.6 s at 60 fps

  const ctx = _getCtx(); if (!ctx) return;
  const dur = 1.6;
  const sr  = ctx.sampleRate;
  const buf = ctx.createBuffer(1, Math.floor(sr * dur), sr);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;

  const src    = ctx.createBufferSource();
  src.buffer   = buf;
  const filter = ctx.createBiquadFilter();
  filter.type  = 'bandpass';
  filter.frequency.setValueAtTime(250, ctx.currentTime);
  filter.frequency.exponentialRampToValueAtTime(550, ctx.currentTime + 0.8);
  filter.frequency.exponentialRampToValueAtTime(250, ctx.currentTime + dur);
  filter.Q.value = 1.8;
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.001, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + 0.25);
  gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + 1.2);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);

  src.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
  src.start(); src.stop(ctx.currentTime + dur);
}

export function playPulse(perfect, hit) {
  if (perfect) {
    _tone(440, 0.06, 'sine',   0.20);
    setTimeout(() => _tone(660,  0.08, 'sine', 0.22), 50);
    setTimeout(() => _tone(880,  0.14, 'sine', 0.25), 100);
    setTimeout(() => _tone(1320, 0.18, 'sine', 0.20, 660), 160);
  } else if (hit) {
    _tone(300, 0.06, 'square', 0.14);
    setTimeout(() => _tone(480, 0.10, 'sine', 0.16, 240), 55);
  } else {
    _tone(140, 0.10, 'triangle', 0.12, 80);
  }
}

export function playEliminated() {
  _tone(250, 0.15, 'sawtooth', 0.3);
  setTimeout(() => _tone(180, 0.4, 'sawtooth', 0.25), 150);
}
