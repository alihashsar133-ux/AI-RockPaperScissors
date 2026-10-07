import {
  FilesetResolver,
  HandLandmarker,
  DrawingUtils
} from './vision_bundle.mjs';

// ========== DOM ==========
const video = document.getElementById('webcam');
const canvas = document.getElementById('output');
const ctx = canvas.getContext('2d');
const cameraStatus = document.getElementById('camera-status');
const startBtn = document.getElementById('start-btn');
const resetBtn = document.getElementById('reset-btn');
const helpBtn = document.getElementById('help-btn');
const closeHelpBtn = document.getElementById('close-help');
const helpPanel = document.getElementById('help-panel');
const countdownEl = document.getElementById('countdown');
const resultMsg = document.getElementById('result-msg');
const playerScoreEl = document.getElementById('player-score');
const computerScoreEl = document.getElementById('computer-score');
const playerMoveEl = document.getElementById('player-move');
const computerMoveEl = document.getElementById('computer-move');
const gestureHint = document.getElementById('gesture-hint');

// ========== State ==========
let handLandmarker = null;
let drawingUtils = null;
let running = false;
let lastVideoTime = -1;
let playerScore = 0;
let computerScore = 0;
let gamePhase = 'idle'; // idle | countdown | result
let currentPlayerGesture = null;
let isProcessingRound = false;

// Landmark connections for drawing
const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[0,17],[17,18],[18,19],[19,20]
];

// ========== Gesture Detection ==========
function isFingerExtended(landmarks, tipIdx, pipIdx, mcpIdx) {
  const wrist = landmarks[0];
  const tip = landmarks[tipIdx];
  const pip = landmarks[pipIdx];
  const distTip = Math.hypot(tip.x - wrist.x, tip.y - wrist.y);
  const distPip = Math.hypot(pip.x - wrist.x, pip.y - wrist.y);
  return distTip > distPip * 1.1;
}

function isThumbExtended(landmarks) {
  const tip = landmarks[4];
  const ip = landmarks[3];
  const wrist = landmarks[0];
  const tipDist = Math.hypot(tip.x - wrist.x, tip.y - wrist.y);
  const ipDist = Math.hypot(ip.x - wrist.x, ip.y - wrist.y);
  return tipDist > ipDist * 1.05;
}

function classifyGesture(landmarks) {
  if (!landmarks || landmarks.length < 21) return null;

  const thumb = isThumbExtended(landmarks);
  const index = isFingerExtended(landmarks, 8, 6, 5);
  const middle = isFingerExtended(landmarks, 12, 10, 9);
  const ring = isFingerExtended(landmarks, 16, 14, 13);
  const pinky = isFingerExtended(landmarks, 20, 18, 17);

  const extendedCount = [index, middle, ring, pinky].filter(Boolean).length;

  if (extendedCount === 0) return 'rock';
  if (index && middle && !ring && !pinky) return 'scissors';
  if (extendedCount >= 3) return 'paper';
  if (extendedCount === 2 && index && middle) return 'scissors';
  if (extendedCount >= 1) return 'paper';
  return 'rock';
}

const GESTURE_EMOJI = {
  rock: '✊',
  paper: '✋',
  scissors: '✌️',
  null: '—'
};

const GESTURE_FA = {
  rock: 'سنگ',
  paper: 'کاغذ',
  scissors: 'قیچی'
};

// ========== Game Logic ==========
function computerChoice() {
  const opts = ['rock', 'paper', 'scissors'];
  return opts[Math.floor(Math.random() * 3)];
}

function decideWinner(player, computer) {
  if (player === computer) return 'tie';
  if (
    (player === 'rock' && computer === 'scissors') ||
    (player === 'paper' && computer === 'rock') ||
    (player === 'scissors' && computer === 'paper')
  ) return 'player';
  return 'computer';
}

async function startRound() {
  if (isProcessingRound || gamePhase !== 'idle') return;
  isProcessingRound = true;
  gamePhase = 'countdown';
  startBtn.disabled = true;
  resultMsg.textContent = '';
  playerMoveEl.textContent = '—';
  computerMoveEl.textContent = '—';

  for (let i = 3; i >= 1; i--) {
    countdownEl.textContent = i;
    countdownEl.classList.remove('hidden');
    void countdownEl.offsetWidth;
    countdownEl.style.animation = 'none';
    void countdownEl.offsetWidth;
    countdownEl.style.animation = '';
    await sleep(900);
  }
  countdownEl.classList.add('hidden');

  let detected = null;
  for (let t = 0; t < 8; t++) {
    if (currentPlayerGesture) {
      detected = currentPlayerGesture;
      break;
    }
    await sleep(80);
  }
  if (!detected) detected = currentPlayerGesture || 'rock';

  const comp = computerChoice();
  const winner = decideWinner(detected, comp);

  playerMoveEl.textContent = GESTURE_EMOJI[detected];
  computerMoveEl.textContent = GESTURE_EMOJI[comp];

  if (winner === 'player') {
    playerScore++;
    resultMsg.textContent = '🎉 شما برنده شدید!';
    resultMsg.style.color = '#68d391';
  } else if (winner === 'computer') {
    computerScore++;
    resultMsg.textContent = 'کامپیوتر برنده شد 😅';
    resultMsg.style.color = '#fc8181';
  } else {
    resultMsg.textContent = 'مساوی شد!';
    resultMsg.style.color = '#f6ad55';
  }

  playerScoreEl.textContent = toPersianNum(playerScore);
  computerScoreEl.textContent = toPersianNum(computerScore);

  gamePhase = 'result';
  await sleep(2200);
  gamePhase = 'idle';
  startBtn.disabled = false;
  isProcessingRound = false;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function toPersianNum(n) {
  return String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

// ========== MediaPipe Init ==========
async function initMediaPipe() {
  try {
    cameraStatus.textContent = 'در حال بارگذاری مدل تشخیص دست...';

    const vision = await FilesetResolver.forVisionTasks('../wasm');
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: '../models/hand_landmarker.task',
        delegate: 'GPU'
      },
      runningMode: 'VIDEO',
      numHands: 1,
      minHandDetectionConfidence: 0.6,
      minHandPresenceConfidence: 0.6,
      minTrackingConfidence: 0.5
    });

    drawingUtils = new DrawingUtils(ctx);
    cameraStatus.textContent = 'لطفاً اجازه دسترسی به دوربین را بدهید';
    await setupWebcam();
  } catch (err) {
    console.error(err);
    cameraStatus.textContent = 'خطا در بارگذاری مدل. فایل‌ها را بررسی کنید.\n' + (err.message || '');
  }
}

async function setupWebcam() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false
    });
    video.srcObject = stream;
    video.addEventListener('loadeddata', () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      cameraStatus.style.display = 'none';
      startBtn.disabled = false;
      gestureHint.textContent = 'دست خود را در مقابل دوربین بگیرید';
      running = true;
      detectLoop();
    });
  } catch (err) {
    console.error(err);
    cameraStatus.textContent = 'دسترسی به دوربین رد شد یا دوربین پیدا نشد.\nلطفاً اجازه دسترسی بدهید و صفحه را رفرش کنید.';
  }
}

function detectLoop() {
  if (!running) return;

  const now = performance.now();
  if (video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    const results = handLandmarker.detectForVideo(video, now);

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (results.landmarks && results.landmarks.length > 0) {
      const landmarks = results.landmarks[0];
      drawingUtils.drawConnectors(landmarks, HAND_CONNECTIONS, { color: '#00FF88', lineWidth: 3 });
      drawingUtils.drawLandmarks(landmarks, { color: '#FF4466', lineWidth: 1, radius: 4 });

      currentPlayerGesture = classifyGesture(landmarks);
      if (gamePhase === 'idle') {
        gestureHint.textContent = currentPlayerGesture
          ? `تشخیص: ${GESTURE_FA[currentPlayerGesture]} ${GESTURE_EMOJI[currentPlayerGesture]}`
          : 'دست خود را واضح‌تر نشان دهید';
      }
    } else {
      currentPlayerGesture = null;
      if (gamePhase === 'idle') {
        gestureHint.textContent = 'دست خود را در مقابل دوربین بگیرید';
      }
    }
    ctx.restore();
  }
  requestAnimationFrame(detectLoop);
}

// ========== Events ==========
startBtn.addEventListener('click', startRound);
resetBtn.addEventListener('click', () => {
  playerScore = 0;
  computerScore = 0;
  playerScoreEl.textContent = '۰';
  computerScoreEl.textContent = '۰';
  resultMsg.textContent = '';
  playerMoveEl.textContent = '—';
  computerMoveEl.textContent = '—';
});
helpBtn.addEventListener('click', () => helpPanel.classList.remove('hidden'));
closeHelpBtn.addEventListener('click', () => helpPanel.classList.add('hidden'));

// Start
initMediaPipe();
