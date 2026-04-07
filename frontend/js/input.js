/**
 * Input — keyboard and mobile touch → paddle position → server.
 * Receives `send` as an injected dependency to avoid circular imports.
 */
import { PADDLE_LEN_H, PADDLE_SPEED } from './config.js';
import { state } from './state.js';
import { unlockAudio } from './audio.js';

const _keys = {};
let _mLeftHeld  = false;
let _mRightHeld = false;

function _tryKick(send) {
  const ko = state.kickoff;
  if (!ko || state.gameState !== 'kickoff' || state.mySlot !== ko.scorer) return;
  const elapsed = (Date.now() - ko.startTime) / 1000;
  const angle   = elapsed * ko.rotSpeed;
  send({ type: 'kick_direction', angle });
}

/** Wire up all input listeners once at startup. */
export function setupInputListeners(send) {
  window.addEventListener('keydown', e => {
    _keys[e.code] = true;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code))
      e.preventDefault();
    unlockAudio();
    if (e.code === 'Space') _tryKick(send);
  });
  window.addEventListener('keyup', e => { _keys[e.code] = false; });

  _bindMobileButton(document.getElementById('mLeft'),
    () => { _mLeftHeld = true; unlockAudio(); _tryKick(send); },
    () => { _mLeftHeld = false; }
  );
  _bindMobileButton(document.getElementById('mRight'),
    () => { _mRightHeld = true; unlockAudio(); _tryKick(send); },
    () => { _mRightHeld = false; }
  );
}

/**
 * Returns [negKey, posKey] for a given wall slot.
 * Accounts for both wall orientation (H vs V) AND tangent direction sign,
 * so that ArrowLeft always moves the paddle visually left/up as expected.
 */
function _getWallKeys(slot, numSides) {
  if (numSides === 4) {
    return (slot === 0 || slot === 1) ? ['ArrowLeft', 'ArrowRight'] : ['ArrowUp', 'ArrowDown'];
  }
  const angle = -Math.PI / 2 + slot * 2 * Math.PI / numSides;
  const nx = Math.cos(angle), ny = Math.sin(angle);
  const tx = -ny, ty = nx;
  if (Math.abs(ny) > Math.abs(nx)) {
    // Horizontal wall: paddle moves along tx. tx>0 → tangent points right → natural L/R.
    // tx<0 → tangent points left → increasing pos moves paddle LEFT → swap keys.
    return tx >= 0 ? ['ArrowLeft', 'ArrowRight'] : ['ArrowRight', 'ArrowLeft'];
  } else {
    // Vertical wall: paddle moves along ty. ty>0 → tangent points down → natural U/D.
    // ty<0 → tangent points up → increasing pos moves paddle UP → swap keys.
    return ty >= 0 ? ['ArrowUp', 'ArrowDown'] : ['ArrowDown', 'ArrowUp'];
  }
}

/** Called every animation frame; sends a move message when the paddle moves. */
export function inputTick(send, dt = 1 / 60) {
  if (state.mySlot < 0 || state.gameState !== 'playing') return;

  const numSides = state.server.numSides || 4;
  const [negKey, posKey] = _getWallKeys(state.mySlot, numSides);
  const lenMult  = state.server.paddle_len_mult?.[state.mySlot] ?? 1.0;
  const spdMult  = state.server.speed_mult?.[state.mySlot] ?? 1.0;
  const half     = (PADDLE_LEN_H * lenMult) / 2;
  const speed    = PADDLE_SPEED * spdMult * dt * 60;
  let moved      = false;

  if (_keys[negKey] || _mLeftHeld) {
    state.localPadPos = Math.max(half, state.localPadPos - speed);
    moved = true;
  }
  if (_keys[posKey] || _mRightHeld) {
    state.localPadPos = Math.min(1 - half, state.localPadPos + speed);
    moved = true;
  }
  if (moved) send({ type: 'move', pos: state.localPadPos });
}

function _bindMobileButton(el, onDown, onRelease) {
  el.addEventListener('pointerdown',  onDown);
  el.addEventListener('pointerup',    onRelease);
  el.addEventListener('pointerleave', onRelease);
}
