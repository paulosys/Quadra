/**
 * UI — manages DOM overlays, scoreboard, and power-up queue display.
 * Reads state; does not write to state.
 */
import { SIDE_LABELS } from './config.js';
import { state } from './state.js';

const OVERLAYS = ['ovConnect', 'ovWaiting', 'ovCountdown', 'ovGoal', 'ovEnd', 'ovUpgrade'];

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
  const numSlots = Math.max(4, activePlayers.length > 0 ? Math.max(...activePlayers) + 1 : 4);
  for (let i = 0; i < numSlots; i++) {
    const filled = activePlayers.includes(i);
    const name   = state.server.names[i] || (filled ? `Jogador ${i + 1}` : '— vazio —');
    const div    = document.createElement('div');
    div.className = 'wp-slot' + (filled ? ' filled' : '');
    div.innerHTML = `<span class="dot"></span><span>${SIDE_LABELS[i] || `Slot ${i + 1}`}: ${name}</span>`;
    wp.appendChild(div);
  }
}


// ── Upgrade cards ──────────────────────────────────────────────────────────

let _upgradeTimerInterval = null;

export function showUpgradeCards(cards, goalsScored, mySlot, timeout, send) {
  OVERLAYS.forEach(x => {
    document.getElementById(x).style.display = 'none';
  });
  const overlay = document.getElementById('ovUpgrade');
  overlay.style.display = 'flex';

  const timerEl = document.getElementById('upgradeTimer');
  const cardsEl = document.getElementById('upgradeCards');
  cardsEl.innerHTML = '';

  let picked   = false;
  let timeLeft = timeout;

  timerEl.textContent = `${timeLeft}s`;
  if (_upgradeTimerInterval) clearInterval(_upgradeTimerInterval);
  _upgradeTimerInterval = setInterval(() => {
    timeLeft--;
    if (timeLeft <= 0) {
      clearInterval(_upgradeTimerInterval);
      _upgradeTimerInterval = null;
      timerEl.textContent = '0s';
    } else {
      timerEl.textContent = `${timeLeft}s`;
    }
  }, 1000);

  const myGoals = goalsScored[mySlot] ?? 0;

  for (const card of cards) {
    const canAfford = myGoals >= card.cost_goals;
    const div = document.createElement('div');
    div.className = 'upgrade-card' + (canAfford ? '' : ' locked');

    div.innerHTML = `
      <div class="upgrade-cost">${card.cost_goals > 0 ? `⚽ ${card.cost_goals} gols` : 'Grátis'}</div>
      <div class="upgrade-label">${card.label}</div>
      <div class="upgrade-desc">${card.desc}</div>
    `;

    if (canAfford) {
      div.addEventListener('click', () => {
        if (picked) return;
        picked = true;
        send({ type: 'pick_upgrade', card: card.id });
        cardsEl.querySelectorAll('.upgrade-card').forEach(c => c.classList.add('unchosen'));
        div.classList.remove('unchosen');
        div.classList.add('chosen');
        if (_upgradeTimerInterval) { clearInterval(_upgradeTimerInterval); _upgradeTimerInterval = null; }
        timerEl.textContent = 'Aguardando...';
      });
    }

    cardsEl.appendChild(div);
  }
}

export function showLifeOffer(goalsScored, mySlot, timeout, send) {
  OVERLAYS.forEach(x => {
    document.getElementById(x).style.display = 'none';
  });
  const overlay = document.getElementById('ovUpgrade');
  overlay.style.display = 'flex';

  const timerEl = document.getElementById('upgradeTimer');
  const cardsEl = document.getElementById('upgradeCards');
  cardsEl.innerHTML = '';

  let decided  = false;
  let timeLeft = timeout;

  timerEl.textContent = `${timeLeft}s`;
  if (_upgradeTimerInterval) clearInterval(_upgradeTimerInterval);
  _upgradeTimerInterval = setInterval(() => {
    timeLeft--;
    if (timeLeft <= 0) {
      clearInterval(_upgradeTimerInterval);
      _upgradeTimerInterval = null;
      timerEl.textContent = '0s';
    } else {
      timerEl.textContent = `${timeLeft}s`;
    }
  }, 1000);

  const myGoals  = goalsScored[mySlot] ?? 0;
  const canAfford = myGoals >= 3;

  // Title
  const title = document.createElement('div');
  title.className = 'life-offer-title';
  title.textContent = '⚠ Você perdeu todas as suas vidas!';
  cardsEl.appendChild(title);

  // Buy button
  const buyDiv = document.createElement('div');
  buyDiv.className = 'upgrade-card' + (canAfford ? '' : ' locked');
  buyDiv.innerHTML = `
    <div class="upgrade-cost">⚽ 3 gols</div>
    <div class="upgrade-label">Comprar 1 vida</div>
    <div class="upgrade-desc">${canAfford ? `Você tem ${myGoals} gols — clique para sobreviver!` : `Gols insuficientes (${myGoals}/3) — você será eliminado`}</div>
  `;
  if (canAfford) {
    buyDiv.addEventListener('click', () => {
      if (decided) return;
      decided = true;
      send({ type: 'pick_upgrade', card: 'life' });
      buyDiv.classList.add('chosen');
      if (_upgradeTimerInterval) { clearInterval(_upgradeTimerInterval); _upgradeTimerInterval = null; }
      timerEl.textContent = 'Aguardando...';
    });
  }
  cardsEl.appendChild(buyDiv);

  // Skip button
  const skipDiv = document.createElement('div');
  skipDiv.className = 'upgrade-card';
  skipDiv.innerHTML = `
    <div class="upgrade-cost" style="color:#888">—</div>
    <div class="upgrade-label">Desistir</div>
    <div class="upgrade-desc">Sair do jogo agora</div>
  `;
  skipDiv.addEventListener('click', () => {
    if (decided) return;
    decided = true;
    send({ type: 'pick_upgrade', card: null });
    skipDiv.classList.add('chosen');
    if (_upgradeTimerInterval) { clearInterval(_upgradeTimerInterval); _upgradeTimerInterval = null; }
    timerEl.textContent = 'Aguardando...';
  });
  cardsEl.appendChild(skipDiv);
}

export function hideUpgradeCards() {
  if (_upgradeTimerInterval) { clearInterval(_upgradeTimerInterval); _upgradeTimerInterval = null; }
  document.getElementById('ovUpgrade').style.display = 'none';
}

export function updatePowerupQueue(queue) {
  const el     = document.getElementById('pq-items');
  const labels = { double: '2X', speed: '⚡', movinggoal: '↔', snitch: '✦', portal: '◈', hurricane: '🌀', ghostgoal: '⚽' };
  el.innerHTML = '';
  for (const ptype of queue) {
    const div       = document.createElement('div');
    div.className   = `pq-item ${ptype}`;
    div.textContent = labels[ptype] || '?';
    el.appendChild(div);
  }
}

const SPAWN_MAX = 14.0; // matches POWERUP_SPAWN_MAX in config.py

export function updateSpawnTimer(timer) {
  const secEl  = document.getElementById('pq-timer-sec');
  const fillEl = document.getElementById('pq-timer-fill');
  if (!secEl || !fillEl) return;
  const pct = timer > 0 ? Math.max(0, Math.min(100, (1 - timer / SPAWN_MAX) * 100)) : 100;
  secEl.textContent  = timer > 0 ? `${Math.ceil(timer)}s` : '…';
  fillEl.style.height = `${pct}%`;
}
