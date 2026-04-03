/**
 * main.js — entry point.
 * Wires all modules together: starts the game loop, binds buttons, and
 * initialises the WebSocket connection.
 */
import { connect, send, reconnect } from './network.js';
import { setupInputListeners, inputTick } from './input.js';
import { draw, resize } from './renderer.js';
import { showOverlay } from './ui.js';
import { unlockAudio, tickHurricaneAmbient } from './audio.js';
import { state } from './state.js';
import { clearParticles } from './particles.js';
import { initDebug, debugTick } from './debug.js';

// ── Layout ─────────────────────────────────────────────────────────────────────
resize();
window.addEventListener('resize', resize);

// ── Input ──────────────────────────────────────────────────────────────────────
setupInputListeners(send);

// ── Debug ──────────────────────────────────────────────────────────────────────
initDebug();

// ── Main loop ──────────────────────────────────────────────────────────────────
function loop() {
  requestAnimationFrame(loop);
  inputTick(send);
  draw();
  debugTick();
  tickHurricaneAmbient(state.server.hurricane_active);
}
loop();

// ── Buttons ────────────────────────────────────────────────────────────────────
document.getElementById('btnJoin').addEventListener('click', () => {
  unlockAudio();
  const name = document.getElementById('inpName').value.trim() || 'Jogador';
  let   room = document.getElementById('inpRoom').value.trim().toUpperCase();
  if (!room) room = Math.random().toString(36).substring(2, 7).toUpperCase();
  state.myRoom      = room;
  state.localPadPos = 0.5;
  send({ type: 'join', name, room });
});

document.getElementById('btnStartGame').addEventListener('click', () => {
  send({ type: 'start_game' });
});

document.getElementById('btnReplay').addEventListener('click', () => {
  const name = document.getElementById('inpName').value.trim() || 'Jogador';
  state.localPadPos = 0.5;
  state.displayBallMap.clear();
  clearParticles();
  const s = state.server;
  s.balls = []; s.paddles = [0.5, 0.5, 0.5, 0.5];
  s.lives = [3, 3, 3, 3]; s.eliminated = [false, false, false, false];
  s.names = ['', '', '', '']; s.powerups = []; s.powerup_queue = [];
  reconnect({ type: 'join', name, room: state.myRoom });
});

document.getElementById('btnLeave').addEventListener('click', () => {
  state.mySlot = -1;
  state.myRoom = '';
  showOverlay('ovConnect');
  reconnect();
});

document.getElementById('room-code').addEventListener('click', () => {
  navigator.clipboard?.writeText(state.myRoom.toUpperCase()).catch(() => {});
  document.getElementById('room-code').textContent = 'COPIADO!';
  setTimeout(() => {
    document.getElementById('room-code').textContent = state.myRoom.toUpperCase();
  }, 1200);
});

['inpName', 'inpRoom'].forEach(id =>
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btnJoin').click();
  })
);

// ── Init ───────────────────────────────────────────────────────────────────────
connect();
