/**
 * Input — keyboard and mobile touch → paddle position → server.
 * Receives `send` as an injected dependency to avoid circular imports.
 */
import { SIDE_KEYS, PADDLE_LEN_H, PADDLE_LEN_V, PADDLE_SPEED } from './config.js';
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

/** Called every animation frame; sends a move message when the paddle moves. */
export function inputTick(send) {
  if (state.mySlot < 0 || state.gameState !== 'playing') return;

  const isH      = state.mySlot === 0 || state.mySlot === 1;
  const k        = SIDE_KEYS[state.mySlot];
  const lenMult  = state.server.paddle_len_mult?.[state.mySlot] ?? 1.0;
  const spdMult  = state.server.speed_mult?.[state.mySlot] ?? 1.0;
  const half     = isH ? (PADDLE_LEN_H * lenMult) / 2 : (PADDLE_LEN_V * lenMult) / 2;
  const speed    = PADDLE_SPEED * spdMult;
  let moved      = false;

  if (_keys[k.neg] || _mLeftHeld) {
    state.localPadPos = Math.max(half, state.localPadPos - speed);
    moved = true;
  }
  if (_keys[k.pos] || _mRightHeld) {
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
