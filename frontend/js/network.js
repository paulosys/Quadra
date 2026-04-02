/**
 * Network — WebSocket lifecycle and server message routing.
 * Writes to state; calls ui and audio side-effects on game events.
 */
import { WS_URL } from './config.js';
import { state } from './state.js';
import { playBounce, playGoal, playPowerupCollect, playEliminated } from './audio.js';
import {
  showOverlay, hideAllOverlays,
  showWaiting, updateScoreUI, updatePowerupQueue,
} from './ui.js';

let _ws = null;

export function connect(joinMsg) {
  const statusEl = document.getElementById('connStatus');
  statusEl.textContent = 'conectando...';
  statusEl.className   = 'conn-status';

  _ws = new WebSocket(WS_URL);

  _ws.addEventListener('open', () => {
    statusEl.textContent = '● conectado ao servidor';
    statusEl.className   = 'conn-status ok';
    if (joinMsg) send(joinMsg);
  });

  _ws.addEventListener('close', () => {
    statusEl.textContent = '✕ desconectado — recarregue';
    statusEl.className   = 'conn-status err';
    document.getElementById('ovConnect').style.display = 'flex';
    document.getElementById('ovWaiting').style.display = 'none';
  });

  _ws.addEventListener('error', () => {
    statusEl.textContent = '✕ erro de conexão';
    statusEl.className   = 'conn-status err';
  });

  _ws.addEventListener('message', e => _handleMessage(JSON.parse(e.data)));
}

export function send(obj) {
  if (_ws && _ws.readyState === WebSocket.OPEN) _ws.send(JSON.stringify(obj));
}

export function reconnect(joinMsg) {
  if (_ws) { _ws.close(); _ws = null; }
  connect(joinMsg);
}

// ── Message routing ───────────────────────────────────────────────────────────

function _handleMessage(msg) {
  switch (msg.type) {

    case 'joined':
      state.mySlot       = msg.slot;
      state.myRoom       = msg.room;
      state.server.names = msg.names;
      showWaiting(msg.players);
      break;

    case 'player_joined':
    case 'player_left':
      state.server.names = msg.names;
      if (state.gameState === 'waiting') showWaiting(msg.players);
      updateScoreUI();
      break;

    case 'countdown':
      showOverlay('ovCountdown');
      document.getElementById('cdText').textContent = msg.value;
      state.gameState = 'countdown';
      break;

    case 'start':
      hideAllOverlays();
      state.localPadPos = 0.5;
      state.gameState = 'playing';
      break;

    case 'state': {
      for (const ball  of (msg.balls     || [])) { if (ball.bounce)  playBounce();              }
      for (const ptype of (msg.collected || [])) { playPowerupCollect(ptype);                   }
      const s         = state.server;
      s.balls         = msg.balls         || [];
      s.paddles       = msg.paddles;
      s.lives         = msg.lives;
      s.eliminated    = msg.eliminated;
      s.names         = msg.names;
      s.powerups      = msg.powerups      || [];
      s.powerup_queue = msg.powerup_queue || [];
      s.goal_offsets  = msg.goal_offsets  || [0, 0, 0, 0];
      s.goal_moving   = msg.goal_moving   || false;
      updateScoreUI();
      updatePowerupQueue(s.powerup_queue);
      break;
    }

    case 'goal': {
      const s      = state.server;
      s.lives      = msg.lives;
      s.eliminated = msg.eliminated;
      s.names      = msg.names;
      updateScoreUI();
      state.gameState = 'goal';

      if (msg.eliminated_now) playEliminated(); else playGoal();
      _flashScreen();

      if (msg.game_over) {
        setTimeout(() => {
          const wname = msg.winner >= 0
            ? (msg.names[msg.winner] || `Jogador ${msg.winner + 1}`)
            : '???';
          document.getElementById('winnerName').textContent = wname;
          showOverlay('ovEnd');
          state.gameState = 'gameover';
        }, 1600);
      }
      break;
    }

    case 'error':
      alert('Erro: ' + msg.msg);
      break;
  }
}

function _flashScreen() {
  const fl = document.getElementById('gflash');
  fl.style.transition = 'none';
  fl.style.background = 'rgba(200,50,50,.4)';
  fl.style.opacity    = '1';
  setTimeout(() => { fl.style.transition = 'opacity .7s'; fl.style.opacity = '0'; }, 80);
}
