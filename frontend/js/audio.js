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
  } else {
    _tone(300, 0.28, 'sawtooth', 0.25, 900);
  }
}

export function playEliminated() {
  _tone(250, 0.15, 'sawtooth', 0.3);
  setTimeout(() => _tone(180, 0.4, 'sawtooth', 0.25), 150);
}
