/**
 * UI — manages DOM overlays, scoreboard, and power-up queue display.
 * Reads state; does not write to state.
 */
import { SIDE_LABELS } from './config.js';
import { state } from './state.js';

const OVERLAYS = ['ovConnect', 'ovWaiting', 'ovCountdown', 'ovGoal', 'ovEnd'];

export function showOverlay(id) {
  OVERLAYS.forEach(x => {
    document.getElementById(x).style.display = x === id ? 'flex' : 'none';
  });
}

export function hideAllOverlays() {
  OVERLAYS.forEach(x => {
    document.getElementById(x).style.display = 'none';
  });
}

export function showWaiting(activePlayers) {
  state.gameState = 'waiting';
  showOverlay('ovWaiting');
  document.getElementById('room-code').textContent = state.myRoom.toUpperCase();

  const wp = document.getElementById('waiting-players');
  wp.innerHTML = '';
  for (let i = 0; i < 4; i++) {
    const filled = activePlayers.includes(i);
    const name   = state.server.names[i] || (filled ? `Jogador ${i + 1}` : '— vazio —');
    const div    = document.createElement('div');
    div.className = 'wp-slot' + (filled ? ' filled' : '');
    div.innerHTML = `<span class="dot"></span><span>${SIDE_LABELS[i]}: ${name}</span>`;
    wp.appendChild(div);
  }
  updateScoreUI();
}

export function updateScoreUI() {
  for (let i = 0; i < 4; i++) {
    const name   = state.server.names[i] || '—';
    const hearts = state.server.lives[i] > 0
      ? ('♥ ').repeat(state.server.lives[i]).trim()
      : '✕';
    document.getElementById('sn' + i).textContent = name;
    document.getElementById('sl' + i).textContent = hearts;
    document.getElementById('sc' + i).classList.toggle('me',   i === state.mySlot);
    document.getElementById('sc' + i).classList.toggle('elim', state.server.eliminated[i]);
    document.getElementById('h'  + i).classList.toggle('me',   i === state.mySlot);
  }
}

export function updatePowerupQueue(queue) {
  const el     = document.getElementById('pq-items');
  const labels = { double: '2X', speed: '⚡', movinggoal: '↔', snitch: '✦' };
  el.innerHTML = '';
  for (const ptype of queue) {
    const div       = document.createElement('div');
    div.className   = `pq-item ${ptype}`;
    div.textContent = labels[ptype] || '?';
    el.appendChild(div);
  }
}
