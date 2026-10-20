/* Sands of the Citadel — Core Engine
   Vanilla JS Canvas, 60fps, pooled objects, procedural rendering
*/
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const gameFrame = document.getElementById('gameFrame');
const hudScore = document.getElementById('hudScore');
const hudWave = document.getElementById('hudWave');
const hudCombo = document.getElementById('hudCombo');
const comboPill = document.getElementById('comboPill');
const hudHealthText = document.getElementById('hudHealthText');
const hudBest = document.getElementById('hudBest');
const healthFill = document.getElementById('healthFill');
const reticle = document.getElementById('reticle');
const touchHint = document.getElementById('touchHint');
const touchControls = document.getElementById('touchControls');
const toastEl = document.getElementById('toast');

// Overlays
const startScreen = document.getElementById('startScreen');
const howScreen = document.getElementById('howScreen');
const pauseScreen = document.getElementById('pauseScreen');
const overScreen = document.getElementById('overScreen');
const boardScreen = document.getElementById('boardScreen');

// Buttons
const btnPlay = document.getElementById('btnPlay');
const btnHow = document.getElementById('btnHow');
const btnHow2 = document.getElementById('btnHow2');
const btnHowPlay = document.getElementById('btnHowPlay');
const btnHowClose = document.getElementById('btnHowClose');
const btnScoresTop = document.getElementById('btnScoresTop');
const btnPause = document.getElementById('btnPause');
const btnResume = document.getElementById('btnResume');
const btnRestart1 = document.getElementById('btnRestart1');
const btnHome1 = document.getElementById('btnHome1');
const btnAgain = document.getElementById('btnAgain');
const btnHome2 = document.getElementById('btnHome2');
const btnSaveScore = document.getElementById('btnSaveScore');
const btnBoardClose = document.getElementById('btnBoardClose');
const btnBoardClear = document.getElementById('btnBoardClear');
const btnSound = document.getElementById('btnSound');
const nameInput = document.getElementById('nameInput');
const nameEntry = document.getElementById('nameEntry');
const chkReduce = document.getElementById('chkReduceMotion');

// HUD board
const overScoreEl = document.getElementById('overScore');
const overWaveEl = document.getElementById('overWave');
const overKillsEl = document.getElementById('overKills');
const overAccEl = document.getElementById('overAcc');
const overComboEl = document.getElementById('overCombo');
const overBadge = document.getElementById('overBadge');
const overTitle = document.getElementById('overTitle');
const miniBoard = document.getElementById('miniBoard');
const boardTable = document.getElementById('boardTable');

// ----- Constants -----
const LOG_W = 1280;
const LOG_H = 720;
const WALL_X = 185;
const WALL_TOP = 128;
const WALL_BOT = 612;
const GATE_Y = LOG_H/2;
const GATE_W = 22;
const GATE_H = 210;

// Game state
let phase = 'start'; // start, playing, paused, over
let score = 0;
let wave = 1;
let gateHealth = 100;
let gateMax = 100;
let kills = 0;
let shots = 0;
let hits = 0;
let combo = 0;
let comboTimer = 0;
let bestCombo = 0;
let spawnTimer = 0;
let spawnInterval = 1.15;
let waveKills = 0;
let elapsed = 0;
let difficulty = 1;
let isMuted = false;
let reduceMotion = false;

// Player
const player = {
  x: WALL_X + 28,
  y: LOG_H/2,
  vy: 0,
  w: 32, h: 52,
  cooldown: 0,
  aimX: LOG_W*0.6,
  aimY: LOG_H/2,
  rapid: 0,
};

// Pools
let enemies = [];
let arrows = [];
let particles = [];
let pickups = [];
let floaters = [];

// Input
const keys = new Set();
let pointer = { x: LOG_W*0.6, y: LOG_H/2, down:false, active:false };
let moveDir = { x:0, y:0 };
let fireHeld = false;

// Shake & effects
let shake = 0;
let shakeDecay = 0.92;
let hitStop = 0;

// High scores
const LS_KEY = 'citadel_legends_v2';
const LS_BEST = 'citadel_best_v2';
let highScores = loadScores();
let bestScore = parseInt(localStorage.getItem(LS_BEST)||'0',10);
hudBest.textContent = bestScore.toLocaleString();

// Audio
let audioCtx = null;
function ensureAudio(){
  if(audioCtx) return;
  try{ audioCtx = new (window.AudioContext||window.webkitAudioContext)(); }catch{}
}
function tone(freq, dur, type='sine', gain=0.18, slideTo){
  if(isMuted || !audioCtx || reduceMotion) return;
  const t = audioCtx.currentTime;
  const o = audioCtx.createOscillator();
  const g = audioCtx.createGain();
  o.type = type; o.frequency.value = freq;
  o.connect(g); g.connect(audioCtx.destination);
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t+dur);
  if(slideTo){ o.frequency.linearRampToValueAtTime(slideTo, t+dur*0.9); }
  o.start(t); o.stop(t+dur+0.02);
}
function noiseBurst(dur=0.18, gain=0.22){
  if(isMuted || !audioCtx || reduceMotion) return;
  const t = audioCtx.currentTime;
  const bufferSize = Math.floor(audioCtx.sampleRate*dur);
  const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
  const data = buffer.getChannelData(0);
  for(let i=0;i<bufferSize;i++) data[i]=(Math.random()*2-1)*Math.pow(1-i/bufferSize,1.2);
  const src = audioCtx.createBufferSource(); src.buffer=buffer;
  const g = audioCtx.createGain(); g.gain.value=gain;
  const f = audioCtx.createBiquadFilter(); f.type='lowpass'; f.frequency.value=1800;
  src.connect(f); f.connect(g); g.connect(audioCtx.destination);
  g.gain.exponentialRampToValueAtTime(0.0001, t+dur);
  src.start(t);
}
const SFX = {
  shoot(){ ensureAudio(); tone(860,0.12,'triangle',0.16,420); setTimeout(()=>tone(1200,0.06,'sine',0.08),30); },
  hit(){ ensureAudio(); tone(220,0.16,'square',0.12,90); noiseBurst(0.1,0.12); },
  gate(){ ensureAudio(); tone(110,0.35,'sawtooth',0.2, 60); noiseBurst(0.25,0.18); },
  pickup(){ ensureAudio(); tone(520,0.12,'sine',0.14,780); setTimeout(()=>tone(880,0.14,'sine',0.12),80); },
  ramHorn(){ ensureAudio(); tone(180,0.5,'triangle',0.18, 120); setTimeout(()=>tone(140,0.7,'sawtooth',0.16),240); },
  over(){ ensureAudio(); tone(440,0.3,'sine',0.14, 330); setTimeout(()=>tone(330,0.4,'triangle',0.14, 220),180); setTimeout(()=>tone(220,0.6,'sine',0.12),380); },
  click(){ ensureAudio(); tone(700,0.08,'sine',0.08,900); }
};

// Utilities
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function lerp(a,b,t){return a+(b-a)*t;}
function rand(a,b){return a+Math.random()*(b-a);}
function choice(a){return a[Math.floor(Math.random()*a.length)];}

// Load/Save scores
function loadScores(){
  try{ const v=JSON.parse(localStorage.getItem(LS_KEY)||'[]'); return Array.isArray(v)?v:[]; }catch{ return []; }
}
function saveScores(){
  localStorage.setItem(LS_KEY, JSON.stringify(highScores));
  const best = highScores[0]?.score||0;
  localStorage.setItem(LS_BEST, String(best));
  hudBest.textContent = String(best);
}
function addScore(name, scoreVal, waveVal, killsVal){
  highScores.push({name: (name||'Defender').slice(0,14), score:scoreVal, wave:waveVal, kills:killsVal, date: new Date().toLocaleDateString()});
  highScores.sort((a,b)=>b.score-a.score);
  highScores = highScores.slice(0,10);
  saveScores();
}
function renderBoard(container, highlightScore=null){
  if(highScores.length===0){
    container.innerHTML = `<div style="padding:14px;text-align:center;color:var(--muted)">No legends yet — be the first to hold the gate!</div>`;
    return;
  }
  let html = `<div class="board-row head"><div>#</div><div>Name</div><div>Score</div><div>Wave</div><div>Date</div></div>`;
  highScores.forEach((s,i)=>{
    const me = highlightScore!==null && s.score===highlightScore ? ' me':'';
    html += `<div class="board-row${me}"><div>${i+1}</div><div>${escapeHtml(s.name)}</div><div><b>${s.score.toLocaleString()}</b></div><div>W${s.wave}</div><div>${s.date}</div></div>`;
  });
  container.innerHTML = html;
}
function escapeHtml(s){ return s.replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function showToast(msg, ms=1600){
  toastEl.textContent = msg;
  toastEl.classList.remove('hidden');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(()=>toastEl.classList.add('hidden'), ms);
}

// ----- Coordinate mapping -----
function toLogical(e){
  const rect = canvas.getBoundingClientRect();
  const sx = LOG_W / rect.width;
  const sy = LOG_H / rect.height;
  return {
    x: (e.clientX - rect.left)*sx,
    y: (e.clientY - rect.top)*sy
  };
}
function updateReticle(){
  // Position reticle DOM element to mirror pointer
  const rect = canvas.getBoundingClientRect();
  const rx = (player.aimX / LOG_W)*rect.width;
  const ry = (player.aimY / LOG_H)*rect.height;
  reticle.style.left = (rect.left + rx - gameFrame.getBoundingClientRect().left) + 'px'; // will be repositioned relative to gameFrame? Actually reticle is absolute inside gameFrame
  // Simpler: set inside gameFrame coords as %
  reticle.style.left = (player.aimX / LOG_W * 100) + '%';
  reticle.style.top = (player.aimY / LOG_H * 100) + '%';
  reticle.style.opacity = phase==='playing' ? '1' : '0';
}
function refreshDPR(){
  const dpr = Math.min(2, window.devicePixelRatio||1);
  canvas.width = LOG_W * dpr;
  canvas.height = LOG_H * dpr;
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
window.addEventListener('resize', ()=>{ refreshDPR(); updateReticle(); });
refreshDPR();

// ----- Input handlers -----
canvas.addEventListener('pointerdown', e=>{
  ensureAudio();
  canvas.setPointerCapture(e.pointerId);
  const p = toLogical(e);
  pointer.x=p.x; pointer.y=p.y; pointer.down=true; pointer.active=true;
  player.aimX = p.x; player.aimY = p.y;
  updateReticle();
  if(phase==='playing'){
    // If clicking on left third, treat as move hint not aim? But we allow aim anywhere.
    // Prevent firing if over HUD? Simple fire on down
    // We'll fire via main loop hold handling; give instant shot
    tryShoot();
  }
});
canvas.addEventListener('pointermove', e=>{
  if(!pointer.active && phase!=='playing') return;
  const p = toLogical(e);
  pointer.x=p.x; pointer.y=p.y;
  player.aimX = p.x; player.aimY = p.y;
  updateReticle();
});
canvas.addEventListener('pointerup', e=>{
  pointer.down=false;
  // keep active for aim
});
canvas.addEventListener('pointercancel', ()=>{ pointer.down=false; });
window.addEventListener('keydown', e=>{
  const k = e.key.toLowerCase();
  keys.add(k);
  if(k==='p' || k===' ' && e.code==='Space' && phase==='playing' && e.target===document.body) { /* handled */ }
  if(k==='p'){
    if(phase==='playing'){ setPaused(true); }
    else if(phase==='paused'){ setPaused(false); }
  }
  if(k==='r'){
    if(phase==='paused' || phase==='over'){ startGame(); }
  }
  if(k===' ' || k==='spacebar'){
    if(phase==='playing') { e.preventDefault(); tryShoot(); }
  }
  if(k==='escape'){
    if(phase==='paused'){ setPaused(false); }
    else if(phase==='playing'){ setPaused(true); }
    else if(!howScreen.classList.contains('hidden') || !boardScreen.classList.contains('hidden') || !overScreen.classList.contains('hidden')){
      howScreen.classList.add('hidden'); boardScreen.classList.add('hidden');
      if(phase==='over'){} else if(phase==='start'){}
    }
  }
});
window.addEventListener('keyup', e=>{ keys.delete(e.key.toLowerCase()); });

// Touch pads
const moveButtons = document.querySelectorAll('[data-mv]');
moveButtons.forEach(btn=>{
  const handler = (e)=>{
    e.preventDefault();
    const mv = btn.dataset.mv;
    // set moveDir
    if(mv==='up') moveDir.y = -1;
    if(mv==='down') moveDir.y = 1;
    if(mv==='left') moveDir.x = -1;
    if(mv==='right') moveDir.x = 1;
    SFX.click();
  };
  btn.addEventListener('touchstart', handler, {passive:false});
  btn.addEventListener('mousedown', handler);
  btn.addEventListener('touchend', ()=>{ moveDir={x:0,y:0}; });
  btn.addEventListener('mouseup', ()=>{ moveDir={x:0,y:0}; });
  btn.addEventListener('mouseleave', ()=>{ moveDir={x:0,y:0}; });
});
document.getElementById('fireBtn').addEventListener('touchstart', e=>{ e.preventDefault(); fireHeld=true; ensureAudio(); }, {passive:false});
document.getElementById('fireBtn').addEventListener('touchend', e=>{ e.preventDefault(); fireHeld=false; });
document.getElementById('fireBtn').addEventListener('mousedown', ()=>{ fireHeld=true; });
document.getElementById('fireBtn').addEventListener('mouseup', ()=>{ fireHeld=false; });

// Buttons
btnPlay.addEventListener('click', ()=>{ SFX.click(); startGame(); });
btnHow.addEventListener('click', ()=>{ SFX.click(); howScreen.classList.remove('hidden'); });
btnHow2.addEventListener('click', ()=>{ SFX.click(); howScreen.classList.remove('hidden'); });
btnHowPlay.addEventListener('click', ()=>{ SFX.click(); howScreen.classList.add('hidden'); if(phase==='start') startGame(); });
btnHowClose.addEventListener('click', ()=>{ howScreen.classList.add('hidden'); });
btnScoresTop.addEventListener('click', ()=>{ SFX.click(); boardScreen.classList.remove('hidden'); renderBoard(boardTable); });
btnPause.addEventListener('click', ()=>{ SFX.click(); if(phase==='playing') setPaused(true); });
btnResume.addEventListener('click', ()=>{ SFX.click(); setPaused(false); });
btnRestart1.addEventListener('click', ()=>{ SFX.click(); startGame(); });
btnHome1.addEventListener('click', ()=>{ SFX.click(); goHome(); });
btnAgain.addEventListener('click', ()=>{ SFX.click(); startGame(); });
btnHome2.addEventListener('click', ()=>{ SFX.click(); goHome(); });
btnSaveScore.addEventListener('click', saveName);
nameInput.addEventListener('keydown', e=>{ if(e.key==='Enter') saveName(); });
btnBoardClose.addEventListener('click', ()=> boardScreen.classList.add('hidden'));
btnBoardClear.addEventListener('click', ()=>{
  if(confirm('Clear all local legends?')){
    highScores=[]; saveScores(); renderBoard(boardTable); renderBoard(miniBoard);
    showToast('Legends cleared');
  }
});
btnSound.addEventListener('click', ()=>{
  isMuted = !isMuted;
  btnSound.textContent = isMuted ? '🔇' : '🔊';
  btnSound.style.opacity = isMuted ? '0.6' : '1';
  showToast(isMuted ? 'Sound muted' : 'Sound on');
});
chkReduce.addEventListener('change', ()=>{ reduceMotion = chkReduce.checked; showToast(reduceMotion ? 'Reduced motion on' : 'Motion effects on'); });
document.getElementById('movePad').addEventListener('touchmove', e=>{ e.preventDefault(); }, {passive:false});


// ----- Game flow -----
function goHome(){
  phase='start';
  pauseScreen.classList.add('hidden');
  overScreen.classList.add('hidden');
  boardScreen.classList.add('hidden');
  startScreen.classList.remove('hidden');
  resetWorld(true);
  hudWave.textContent = '1';
  updateHUD();
}
function setPaused(v){
  if(phase==='over' || phase==='start') return;
  if(v){
    phase='paused';
    pauseScreen.classList.remove('hidden');
  } else {
    phase='playing';
    pauseScreen.classList.add('hidden');
  }
}
function resetWorld(showStart){
  score=0; wave=1; gateHealth=gateMax; kills=0; shots=0; hits=0; combo=0; comboTimer=0; bestCombo=0; waveKills=0; elapsed=0; difficulty=1; spawnTimer=0; spawnInterval=1.15;
  player.y=LOG_H/2; player.rapid=0; player.cooldown=0;
  enemies.length=0; arrows.length=0; particles.length=0; pickups.length=0; floaters.length=0;
  shake=0;
  if(showStart) startScreen.classList.remove('hidden');
  else startScreen.classList.add('hidden');
  overScreen.classList.add('hidden');
  pauseScreen.classList.add('hidden');
  updateHUD();
}
function startGame(){
  ensureAudio();
  resetWorld(false);
  phase='playing';
  startScreen.classList.add('hidden');
  overScreen.classList.add('hidden');
  pauseScreen.classList.add('hidden');
  howScreen.classList.add('hidden');
  boardScreen.classList.add('hidden');
  touchControls.classList.add('visible');
  // initial enemies soon
  spawnTimer = 0.3;
  showToast('Defend the gate! Wave 1', 1200);
  // auto-hide touch hint after few secs
  setTimeout(()=>{ touchHint.style.opacity='0'; }, 3800);
}
function endGame(){
  phase='over';
  SFX.over();
  // stats
  overScoreEl.textContent = score.toLocaleString();
  overWaveEl.textContent = wave;
  overKillsEl.textContent = kills;
  const acc = shots? Math.round(hits/shots*100):0;
  overAccEl.textContent = acc+'%';
  overComboEl.textContent = '×'+ (bestCombo>0? (1+bestCombo*0.2).toFixed(1) : '1.0');

  let title = 'City Held for Glory';
  let badge = 'THE GATE HAS FALLEN';
  if(score >= 9000) { title='Legend of the Citadel!'; badge='MYTHIC DEFENSE'; }
  else if(score >= 5500) { title='Unbreakable Defender'; badge='HEROIC STAND'; }
  else if(score >= 2500) { title='Steadfast Guardian'; badge='VALIANT EFFORT'; }
  else if(score < 800) { title='First Stand — Learn & Return'; badge='THE GATE HAS FALLEN'; }
  overTitle.textContent = title;
  overBadge.textContent = badge;

  // check high score condition
  const lowest = highScores[highScores.length-1]?.score ?? -1;
  const isHigh = highScores.length<10 || score > lowest;
  if(isHigh && score>0){
    nameEntry.style.display='block';
    nameInput.value='';
    setTimeout(()=>nameInput.focus(), 220);
  } else {
    nameEntry.style.display='none';
  }
  renderBoard(miniBoard, isHigh? score:null);
  overScreen.classList.remove('hidden');
  // best
  if(score>bestScore){ bestScore=score; localStorage.setItem(LS_BEST, String(bestScore)); hudBest.textContent=String(bestScore); }
}
function saveName(){
  const n = (nameInput.value.trim()||'Defender');
  addScore(n, score, wave, kills);
  nameEntry.style.display='none';
  renderBoard(miniBoard, score);
  renderBoard(boardTable, score);
  showToast('Legend saved — '+n);
  SFX.pickup();
}

function tryShoot(){
  if(phase!=='playing') return;
  if(player.cooldown>0) return;
  // spawn arrow
  const fromX = player.x + 18;
  const fromY = player.y - 4;
  // Aim towards player.aim
  const dx = player.aimX - fromX;
  const dy = player.aimY - fromY;
  const len = Math.hypot(dx,dy) || 1;
  const speed = 740 + Math.min(180, wave*12);
  const vx = dx/len*speed;
  const vy = dy/len*speed;
  arrows.push({ x:fromX, y:fromY, vx, vy, life:2.2, trail:[] });
  shots++;
  player.cooldown = player.rapid>0 ? 0.11 : 0.24;
  // recoil & muzzle
  spawnMuzzle(fromX, fromY, Math.atan2(vy,vx));
  // small screen kick
  if(!reduceMotion) shake = Math.min(shake+1.2, 4);
  SFX.shoot();
  // touch feedback
  if(navigator.vibrate) try{ navigator.vibrate(10);}catch{}
}

// ----- Spawning -----
function spawnEnemy(forceRam=false){
  const laneYchoices = [190, 260, 340, 420, 500, 580];
  // bias to middle lanes for fairness
  let y = choice(laneYchoices) + rand(-14,14);
  y = clamp(y, 170, 600);
  let type = 0;
  if(forceRam) type = 3;
  else {
    const r = Math.random();
    if(wave>=5 && r < 0.08 + wave*0.008) type=3; // ram chance grows
    else if(r < 0.22) type=2; // shield
    else if(r < 0.55) type=1; // spear
    else type=0; // sword
  }
  // adjust difficulty
  const speedMul = 1 + (wave-1)*0.06 + (difficulty-1)*0.04;
  let hp, speed, w,h, scoreVal;
  if(type===0){ hp=1; speed=rand(58,78)*speedMul; w=28; h=46; scoreVal=100; }
  else if(type===1){ hp=1; speed=rand(78,102)*speedMul; w=26; h=48; scoreVal=125; }
  else if(type===2){ hp=3; speed=rand(42,58)*speedMul; w=34; h=52; scoreVal=250; }
  else { hp=10 + Math.floor(wave*0.8); speed=rand(28,38)*speedMul; w=96; h=54; scoreVal=900+wave*60; y = rand(320, 560); }
  enemies.push({
    x: LOG_W + rand(10, 80),
    y, w, h, vx: -speed, vy: 0,
    hp, maxHp: hp,
    type, scoreVal,
    hitFlash:0,
    bob: Math.random()*Math.PI*2,
    stepPhase: Math.random()*Math.PI,
  });
}
function maybeSpawnPickup(x,y){
  if(Math.random()<0.14){
    const t = Math.random()<0.5 ? 'heal' : 'rapid';
    pickups.push({ x, y: y-8, vx: rand(-20,20), vy: -80, type:t, life:7, rot:0 });
  }
}

// ----- Particles -----
function spawnParticles(x,y, count, color, spread=90, power=120){
  if(reduceMotion) count = Math.max(1, Math.floor(count*0.35));
  for(let i=0;i<count;i++){
    const ang = rand(-Math.PI, Math.PI);
    const sp = rand(power*0.4, power);
    particles.push({
      x, y,
      vx: Math.cos(ang)*sp + rand(-20,20),
      vy: Math.sin(ang)*sp + rand(-60, -10),
      life: rand(0.28, 0.55),
      maxLife: 0.55,
      size: rand(2.2, 4.8),
      color,
      alpha:1,
      grav: 520,
      drag: 0.98,
    });
  }
}
function spawnMuzzle(x,y, ang){
  for(let i=0;i<6;i++){
    particles.push({
      x: x + Math.cos(ang)*12, y: y + Math.sin(ang)*12,
      vx: Math.cos(ang)*rand(180,260) + rand(-20,20),
      vy: Math.sin(ang)*rand(180,260) + rand(-20,20),
      life: 0.12, maxLife:0.12, size: rand(2,3.5), color:'#fde68a', alpha:0.9, grav:0, drag:0.92
    });
  }
}
function spawnImpact(x,y, isHead){
  spawnParticles(x,y, 10, isHead ? '#facc15' : '#e2e8f0', 120, 160);
  spawnParticles(x,y, 5, '#f59e0b', 90, 90);
  if(isHead) spawnParticles(x,y, 4, '#fff', 80, 200);
}
function addFloater(x,y, text, color='#fff'){
  floaters.push({ x, y, vy:-42, life:0.85, text, color });
}

// ----- Update loop -----
let lastT = performance.now();
function frame(now){
  const dtRaw = Math.min(0.033, (now - lastT)/1000);
  lastT = now;
  const dt = hitStop>0 ? 0 : dtRaw;
  if(hitStop>0) hitStop-=dtRaw;

  // Input continuous
  if(phase==='playing'){
    // keyboard move
    let my = 0, mx = 0;
    if(keys.has('w')||keys.has('arrowup')) my -= 1;
    if(keys.has('s')||keys.has('arrowdown')) my += 1;
    if(keys.has('a')||keys.has('arrowleft')) mx -= 1;
    if(keys.has('d')||keys.has('arrowright')) mx += 1;
    // combine with touch pad dir
    my += moveDir.y;
    mx += moveDir.x;
    // player moves primarily vertical along wall, but allow slight x drift for feel (clamped)
    const moveSpeed = 320;
    if(my!==0) player.y += Math.sign(my)*moveSpeed*dt;
    // x drift limited
    if(mx!==0) player.x += Math.sign(mx)* 90 * dt;
    player.y = clamp(player.y, WALL_TOP+28, WALL_BOT-22);
    player.x = clamp(player.x, WALL_X+6, WALL_X+56);

    // aim follows pointer; allow keyboard nudge aim?
    if(keys.has('arrowup')||keys.has('arrowdown')||keys.has('arrowleft')||keys.has('arrowright')){
      // nudge aim slowly
      if(keys.has('arrowup')) player.aimY -= 380*dt;
      if(keys.has('arrowdown')) player.aimY += 380*dt;
      if(keys.has('arrowleft')) player.aimX -= 380*dt;
      if(keys.has('arrowright')) player.aimX += 380*dt;
      player.aimX = clamp(player.aimX, WALL_X+40, LOG_W-20);
      player.aimY = clamp(player.aimY, 40, LOG_H-20);
    }

    // firing hold (auto)
    if(fireHeld && player.cooldown<=0) tryShoot();
    // space held
    if(keys.has(' ') && player.cooldown<=0) tryShoot();

    // cooldown
    if(player.cooldown>0) player.cooldown -= dt;
    if(player.rapid>0) player.rapid -= dt;
    if(comboTimer>0){ comboTimer-=dt; if(comboTimer<=0){ combo=0; updateHUD(); } }

    // spawning
    spawnTimer -= dt;
    if(spawnTimer<=0){
      // spawn 1-2 enemies per tick
      const burst = wave>6 && Math.random()<0.35 ? 2 : 1;
      for(let i=0;i<burst;i++) spawnEnemy();
      // ram warning every 5 waves
      if(waveKills>= 14 + wave*2){ // wave progression by kills
        wave++; waveKills=0; difficulty++; spawnInterval = Math.max(0.38, 1.15 - wave*0.045);
        showToast('⚔️ Wave '+wave+' — Hold fast!', 1500);
        if(wave%5===0){ // ram wave
          showToast('🐏 RAM APPROACHING! Concentrate fire!', 2000);
          SFX.ramHorn();
          for(let i=0;i<2;i++) setTimeout(()=>spawnEnemy(true), i*320);
        }
        updateHUD();
      }
      spawnTimer = spawnInterval * rand(0.85,1.15);
      if(wave>8) spawnTimer *= 0.88;
    }
    elapsed += dt;

    // Enemies update
    for(let i=enemies.length-1;i>=0;i--){
      const e = enemies[i];
      e.x += e.vx * dt;
      e.y += Math.sin(elapsed*2 + e.bob)* 8 * dt; // subtle bob
      if(e.hitFlash>0) e.hitFlash-=dt;
      e.stepPhase += dt* (Math.abs(e.vx)/40);
      // reached gate?
      if(e.x <= WALL_X + 18){
        // damage gate
        const dmg = e.type===3 ? 28 : e.type===2 ? 14 : 10;
        gateHealth = clamp(gateHealth - dmg, 0, gateMax);
        shake = Math.min(18, shake + (e.type===3? 14: 8));
        SFX.gate();
        spawnParticles(WALL_X+12, e.y, e.type===3? 22:12, '#f59e0b', 140, 220);
        spawnParticles(WALL_X+10, clamp(e.y, WALL_TOP, WALL_BOT), 8, '#57534e', 80, 120);
        enemies.splice(i,1);
        updateHUD();
        if(gateHealth<=0){ endGame(); break; }
        continue;
      }
      // cull far left? Already handled
      if(e.x < -100){ enemies.splice(i,1); continue; }
    }

    // Arrows update
    for(let i=arrows.length-1;i>=0;i--){
      const a = arrows[i];
      a.x += a.vx * dt;
      a.y += a.vy * dt;
      a.vy += 520 * dt; // gravity
      a.life -= dt;
      // trail
      a.trail.push({x:a.x, y:a.y});
      if(a.trail.length>6) a.trail.shift();
      // offscreen
      if(a.x>LOG_W+60 || a.x<-60 || a.y>LOG_H+60 || a.life<=0){
        arrows.splice(i,1); continue;
      }
      // collision with enemies
      let hit = false;
      for(let j=enemies.length-1;j>=0;j--){
        const e = enemies[j];
        // simple AABB with arrow point
        const ex1 = e.x - e.w/2, ex2 = e.x + e.w/2;
        const ey1 = e.y - e.h/2 - 8, ey2 = e.y + e.h/2;
        if(a.x>=ex1 && a.x<=ex2 && a.y>=ey1 && a.y<=ey2){
          // hit!
          const isHead = a.y < e.y - e.h*0.18;
          e.hp -= isHead ? 2 : 1; // headshot bonus
          e.hitFlash = 0.12;
          hits++;
          combo++;
          bestCombo = Math.max(bestCombo, combo);
          comboTimer = 1.9;
          // score
          let pts = e.scoreVal;
          if(isHead) pts += 60;
          const mult = 1 + combo*0.18;
          const gained = Math.round(pts * mult * (1 + wave*0.04));
          score += gained;
          SFX.hit();
          spawnImpact(a.x, a.y, isHead);
          addFloater(e.x, e.y-18, '+'+gained + (isHead?' ★':'') + (combo>=3? ' ×'+mult.toFixed(1):''), isHead? '#facc15':'#fff');
          // tiny hitstop for satisfying impact on kill
          if(e.hp<=0){
            // kill
            kills++; waveKills++;
            spawnParticles(e.x, e.y, e.type===3? 26:14, '#fef3c7', 160, 190);
            spawnParticles(e.x, e.y, 10, '#0f766e', 140, 160);
            if(e.type===3) hitStop = 0.06;
            else if(!reduceMotion) hitStop = 0.02;
            // bonus for ram
            if(e.type===3) { score += 400; addFloater(e.x, e.y-30, '+400 RAM!', '#f59e0b'); shake = Math.min(shake+6, 16); }
            maybeSpawnPickup(e.x, e.y);
            enemies.splice(j,1);
          }
          arrows.splice(i,1);
          hit=true;
          updateHUD();
          break;
        }
      }
      if(hit) continue;
      // hit wall? ignore
    }

    // Pickups
    for(let i=pickups.length-1;i>=0;i--){
      const p = pickups[i];
      p.vy += 420*dt;
      p.x += p.vx*dt;
      p.y += p.vy*dt;
      p.rot += dt*2.2;
      p.life -= dt;
      p.vx *= 0.98;
      if(p.life<=0){ pickups.splice(i,1); continue; }
      // bounce floor
      if(p.y > LOG_H-48){ p.y = LOG_H-48; p.vy = -Math.abs(p.vy)*0.45; p.vx*=0.8; }
      // player collect (near player)
      const dx = p.x - player.x, dy = p.y - player.y;
      if(Math.hypot(dx,dy) < 42){
        if(p.type==='heal'){
          gateHealth = clamp(gateHealth + 22, 0, gateMax);
          addFloater(player.x, player.y-36, '+HEAL', '#10b981');
          SFX.pickup();
          showToast('Gate repaired +22', 1000);
        } else {
          player.rapid = 5.0;
          addFloater(player.x, player.y-36, 'RAPID FIRE!', '#38bdf8');
          SFX.pickup();
          showToast('⚡ Rapid volley 5s', 1200);
        }
        spawnParticles(p.x,p.y,12, p.type==='heal'? '#10b981':'#38bdf8');
        pickups.splice(i,1);
        updateHUD();
      }
    }

    // Particles
    for(let i=particles.length-1;i>=0;i--){
      const pt = particles[i];
      pt.vy += (pt.grav||0)*dt;
      pt.x += pt.vx*dt;
      pt.y += pt.vy*dt;
      pt.vx *= pt.drag ?? 0.99;
      pt.vy *= pt.drag ?? 0.99;
      pt.life -= dt;
      pt.alpha = pt.life / (pt.maxLife||0.5);
      if(pt.life<=0) particles.splice(i,1);
    }
    // Floaters
    for(let i=floaters.length-1;i>=0;i--){
      const f=floaters[i];
      f.y += f.vy*dt;
      f.life-=dt;
      if(f.life<=0) floaters.splice(i,1);
    }
    // shake decay
    if(shake>0) shake*= Math.pow(shakeDecay, dt*60);
    if(shake<0.2) shake=0;
  }

  render(dtRaw);
  requestAnimationFrame(frame);
}

function updateHUD(){
  hudScore.textContent = score.toLocaleString();
  hudWave.textContent = wave;
  const mult = 1 + combo*0.18;
  hudCombo.textContent = '×'+mult.toFixed(1);
  if(combo>=3) comboPill.classList.add('hot');
  else comboPill.classList.remove('hot');
  const pct = Math.round(gateHealth/gateMax*100);
  hudHealthText.textContent = pct+'%';
  healthFill.style.width = pct+'%';
  healthFill.classList.remove('low','crit');
  if(pct<32) healthFill.classList.add('crit');
  else if(pct<58) healthFill.classList.add('low');
}

// ----- Rendering -----
function render(dt){
  // shake offset
  let sx=0, sy=0;
  if(shake>0){
    sx = (Math.random()-0.5)*shake*2;
    sy = (Math.random()-0.5)*shake*1.2;
  }
  ctx.save();
  if(sx||sy) ctx.translate(sx,sy);

  // Clear
  ctx.clearRect(-10,-10, LOG_W+20, LOG_H+20);

  drawBackground();
  drawDunes();
  drawWall();
  drawEnemies();
  drawPickups();
  drawPlayer();
  drawArrows();
  drawParticles();
  drawFloaters();
  drawGateEffects();

  ctx.restore();

  // reticle update for smoothness
  updateReticle();
}

function drawBackground(){
  // sky gradient
  const g = ctx.createLinearGradient(0,0,0,LOG_H);
  g.addColorStop(0,'#0b1020');
  g.addColorStop(0.45,'#1e1b4b');
  g.addColorStop(0.75,'#312e81');
  g.addColorStop(1,'#451a03');
  ctx.fillStyle=g;
  ctx.fillRect(0,0,LOG_W,LOG_H);

  // stars
  const t = Date.now()*0.0003;
  ctx.fillStyle='rgba(255,255,255,0.9)';
  for(let i=0;i<90;i++){
    const x = (i*137.5)%LOG_W;
    const y = (i*67.3)%280;
    const tw = Math.sin(t* (0.8 + i%3) + i) *0.5 + 0.8;
    ctx.globalAlpha = 0.55*tw;
    ctx.fillRect(x, y, 1.4, 1.4);
  }
  ctx.globalAlpha=1;

  // moon
  ctx.save();
  ctx.translate(LOG_W-150, 78);
  ctx.fillStyle='#fef3c7';
  ctx.shadowColor='rgba(254,243,199,0.6)'; ctx.shadowBlur=18;
  ctx.beginPath(); ctx.arc(0,0,34,0,Math.PI*2); ctx.fill();
  ctx.shadowBlur=0;
  ctx.fillStyle='#0b1020';
  ctx.beginPath(); ctx.arc(12,-6,32,0,Math.PI*2); ctx.fill();
  // soft halo
  ctx.fillStyle='rgba(250,204,21,0.08)';
  ctx.beginPath(); ctx.arc(0,0,58,0,Math.PI*2); ctx.fill();
  ctx.restore();

  // mosque silhouette far
  ctx.fillStyle='rgba(0,0,0,0.22)';
  ctx.beginPath();
  ctx.moveTo(260, 300); ctx.lineTo(300, 260); ctx.lineTo(340, 300); ctx.lineTo(360, 300); ctx.lineTo(360, 340); ctx.lineTo(260,340); ctx.closePath(); ctx.fill();
  ctx.fillRect(290, 220, 8, 40);
  ctx.fillRect(320, 210, 6, 50);
  // minaret tops
  ctx.fillStyle='rgba(255,255,255,0.06)';
  ctx.fillRect(288, 216, 12, 4);
  ctx.fillRect(318, 206, 10, 4);
}

function drawDunes(){
  // ground dunes with parallax
  // horizon
  ctx.fillStyle='#78350f';
  ctx.fillRect(0, 580, LOG_W, 140);
  // dune shapes
  const dunes = [
    {x:0, y:540, w:520, h:70, c:'#92400e'},
    {x:380, y:520, w:640, h:90, c:'#a16207'},
    {x:820, y:560, w:520, h:60, c:'#92400e'},
  ];
  dunes.forEach(d=>{
    ctx.fillStyle=d.c;
    ctx.beginPath();
    ctx.ellipse(d.x + d.w/2, d.y, d.w/2, d.h/2, 0, Math.PI, Math.PI*2);
    ctx.fill();
    // highlight
    ctx.fillStyle='rgba(253,230,138,0.12)';
    ctx.beginPath();
    ctx.ellipse(d.x + d.w/2 -20, d.y -6, d.w*0.42, d.h*0.32, -0.2, Math.PI, Math.PI*2);
    ctx.fill();
  });
  // ground texture ticks
  ctx.strokeStyle='rgba(0,0,0,0.12)';
  ctx.lineWidth=1;
  for(let x=0;x<LOG_W;x+=28){
    const y = 590 + Math.sin(x*0.02)*8;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x+12, y+2); ctx.stroke();
  }
  // wall shadow
  ctx.fillStyle='rgba(0,0,0,0.25)';
  ctx.fillRect(WALL_X-16, 600, 32, 14);
}

function drawWall(){
  // main citadel wall
  const wallX = WALL_X;
  // tower
  ctx.fillStyle='#1f2937';
  ctx.fillRect(wallX-26, WALL_TOP-36, 52, 40);
  // crenellations
  ctx.fillStyle='#334155';
  for(let i=0;i<5;i++){
    ctx.fillRect(wallX-24 + i*12, WALL_TOP-44, 8, 12);
  }
  // wall body
  const wallGrad = ctx.createLinearGradient(wallX-18,0, wallX+18,0);
  wallGrad.addColorStop(0,'#334155');
  wallGrad.addColorStop(0.5,'#e7d8a8');
  wallGrad.addColorStop(1,'#a16207');
  ctx.fillStyle=wallGrad;
  ctx.fillRect(wallX-18, WALL_TOP, 36, WALL_BOT-WALL_TOP);

  // geometric tile pattern (Islamic 8-point)
  ctx.save();
  ctx.clip();
  // We'll draw pattern via lines
  ctx.strokeStyle='rgba(14,118,110,0.18)';
  ctx.lineWidth=1;
  for(let y=WALL_TOP+18; y<WALL_BOT; y+=22){
    for(let x= wallX-14; x< wallX+16; x+=22){
      // diamond
      ctx.beginPath();
      ctx.moveTo(x, y-7); ctx.lineTo(x+7,y); ctx.lineTo(x,y+7); ctx.lineTo(x-7,y); ctx.closePath(); ctx.stroke();
      // inner
      ctx.strokeStyle='rgba(250,204,21,0.14)';
      ctx.beginPath(); ctx.arc(x,y,3.2,0,Math.PI*2); ctx.stroke();
      ctx.strokeStyle='rgba(14,118,110,0.18)';
    }
  }
  ctx.restore();
  // outline
  ctx.strokeStyle='rgba(0,0,0,0.25)'; ctx.lineWidth=2;
  ctx.strokeRect(wallX-18, WALL_TOP, 36, WALL_BOT-WALL_TOP);

  // gate
  const gateCx = wallX;
  const gateTop = GATE_Y - GATE_H/2;
  ctx.fillStyle='#451a03';
  // arch
  ctx.beginPath();
  ctx.moveTo(gateCx-16, gateTop+GATE_H);
  ctx.lineTo(gateCx-16, gateTop+28);
  ctx.arc(gateCx, gateTop+28, 16, Math.PI, 0);
  ctx.lineTo(gateCx+16, gateTop+GATE_H);
  ctx.closePath();
  ctx.fill();
  // gate door planks
  ctx.fillStyle='#78350f';
  ctx.fillRect(gateCx-13, gateTop+36, 26, GATE_H-36);
  ctx.strokeStyle='rgba(0,0,0,0.35)'; ctx.lineWidth=1;
  for(let y=gateTop+46; y<gateTop+GATE_H; y+=18){
    ctx.beginPath(); ctx.moveTo(gateCx-13,y); ctx.lineTo(gateCx+13,y); ctx.stroke();
  }
  // metal bands
  ctx.fillStyle='#334155';
  ctx.fillRect(gateCx-14, gateTop+68, 28, 5);
  ctx.fillRect(gateCx-14, gateTop+110, 28, 5);
  ctx.fillRect(gateCx-14, gateTop+152, 28, 5);
  // studs
  ctx.fillStyle='#facc15';
  for(let y of [70,112,154]){
    ctx.beginPath(); ctx.arc(gateCx-9, gateTop+y,2.2,0,Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(gateCx+9, gateTop+y,2.2,0,Math.PI*2); ctx.fill();
  }
  // arch keystone
  ctx.fillStyle='#fde68a';
  ctx.fillRect(gateCx-6, gateTop+20,12,10);
  ctx.fillStyle='#0f766e';
  ctx.font='700 8px Cinzel'; ctx.textAlign='center';
  ctx.fillText('◈', gateCx, gateTop+28);

  // gate damage cracks overlay
  const pct = gateHealth/gateMax;
  if(pct<0.85){
    ctx.strokeStyle='rgba(0,0,0,0.55)'; ctx.lineWidth=2;
    const cracks = Math.floor((1-pct)*9);
    for(let i=0;i<cracks;i++){
      ctx.beginPath();
      const sx = gateCx + rand(-10,10);
      const sy = gateTop+ rand(40, GATE_H-10);
      ctx.moveTo(sx,sy);
      ctx.lineTo(sx+ rand(-10,10), sy+ rand(8,18));
      ctx.stroke();
    }
    if(pct<0.45){
      // flicker fire light
      ctx.fillStyle='rgba(244,63,94,'+(0.12+ Math.sin(Date.now()*0.008)*0.05)+')';
      ctx.fillRect(gateCx-12, gateTop+36,24,GATE_H-36);
    }
  }

  // wall walkway
  ctx.fillStyle='#1f2937';
  ctx.fillRect(wallX-20, WALL_TOP-2, 40, 6);
  // defender platform glow when rapid
  if(player.rapid>0){
    ctx.fillStyle='rgba(56,189,248,'+(0.25+Math.sin(Date.now()*0.015)*0.1)+')';
    ctx.fillRect(wallX-18, player.y-22, 36, 4);
  }
}

function drawPlayer(){
  const {x,y} = player;
  // shadow
  ctx.fillStyle='rgba(0,0,0,0.25)';
  ctx.beginPath(); ctx.ellipse(x, y+28, 14, 5, 0,0,Math.PI*2); ctx.fill();

  // legs
  ctx.fillStyle='#0f172a';
  ctx.fillRect(x-7, y+8, 6, 14);
  ctx.fillRect(x+1, y+8, 6, 14);
  // boots
  ctx.fillStyle='#422006';
  ctx.fillRect(x-8, y+20, 7, 4);
  ctx.fillRect(x+1, y+20, 8, 4);

  // body — turquoise qamis with gold trim
  ctx.fillStyle='#0f766e';
  ctx.beginPath();
  // tunic
  ctx.moveTo(x-10, y-10); ctx.lineTo(x+10, y-10); ctx.lineTo(x+8, y+10); ctx.lineTo(x-8, y+10); ctx.closePath(); ctx.fill();
  // sash
  ctx.fillStyle='#f59e0b';
  ctx.fillRect(x-10, y-2, 20, 4);
  // cape
  ctx.fillStyle= player.rapid>0 ? '#38bdf8' : '#1e40af';
  ctx.globalAlpha=0.92;
  ctx.beginPath(); ctx.moveTo(x-10, y-8); ctx.lineTo(x-16, y+6); ctx.lineTo(x-10, y+12); ctx.closePath(); ctx.fill();
  ctx.globalAlpha=1;

  // arms & bow
  // bow stave
  const aimAng = Math.atan2(player.aimY - (y-4), player.aimX - x);
  ctx.save();
  ctx.translate(x+6, y-4);
  ctx.rotate(aimAng);
  ctx.strokeStyle='#451a03'; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.arc(0,0,14, -0.9, 0.9); ctx.stroke();
  // string
  ctx.strokeStyle='#fef3c7'; ctx.lineWidth=1.2;
  ctx.beginPath(); ctx.moveTo(-6, -12); ctx.lineTo(2,0); ctx.lineTo(-6,12); ctx.stroke();
  // arrow nocked
  if(player.cooldown<0.08){
    ctx.fillStyle='#fde68a';
    ctx.fillRect(2, -1.2, 14, 2.4);
    ctx.fillStyle='#e5e7eb'; ctx.beginPath(); ctx.moveTo(16,-3); ctx.lineTo(20,0); ctx.lineTo(16,3); ctx.closePath(); ctx.fill();
  }
  ctx.restore();

  // head
  ctx.fillStyle='#fde68a';
  ctx.beginPath(); ctx.arc(x, y-16, 9, 0, Math.PI*2); ctx.fill();
  // keffiyeh / helmet turban
  ctx.fillStyle='#e7d8a8';
  ctx.beginPath(); ctx.arc(x, y-18,10, Math.PI*1.05, Math.PI*1.95); ctx.fill();
  ctx.fillStyle='#0f766e';
  ctx.fillRect(x-10, y-20,20,3);
  // face
  ctx.fillStyle='#92400e';
  ctx.beginPath(); ctx.arc(x+2, y-15,1.1,0,Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.arc(x+6, y-15,1.1,0,Math.PI*2); ctx.fill();
  // beard
  ctx.fillStyle='#451a03';
  ctx.beginPath(); ctx.arc(x, y-12,4, 0.1, Math.PI-0.1); ctx.fill();

  // aim line faint
  if(phase==='playing'){
    ctx.strokeStyle='rgba(253,230,138,0.28)';
    ctx.setLineDash([6,8]);
    ctx.lineWidth=1;
    ctx.beginPath();
    ctx.moveTo(x+12, y-4);
    // predict a bit
    const tx = player.aimX, ty = player.aimY;
    ctx.lineTo(lerp(x+12, tx, 0.55), lerp(y-4, ty, 0.55));
    ctx.stroke();
    ctx.setLineDash([]);
    // dot at aim
    ctx.fillStyle='rgba(250,204,21,0.9)';
    ctx.beginPath(); ctx.arc(player.aimX, player.aimY, 2.2,0,Math.PI*2); ctx.fill();
  }

  // rapid indicator
  if(player.rapid>0){
    ctx.fillStyle='rgba(56,189,248,0.9)';
    ctx.font='700 10px Inter'; ctx.textAlign='center';
    ctx.fillText('⚡ RAPID', x, y-32);
    // bar
    ctx.fillStyle='rgba(15,23,42,0.7)'; ctx.fillRect(x-14, y-30,28,4);
    ctx.fillStyle='#38bdf8'; ctx.fillRect(x-14, y-30, 28*(player.rapid/5),4);
  }
  ctx.textAlign='left';
}

function drawEnemies(){
  enemies.forEach(e=>{
    const {x,y,w,h,type} = e;
    // shadow
    ctx.fillStyle='rgba(0,0,0,0.22)';
    ctx.beginPath(); ctx.ellipse(x, 602, w*0.5, 6, 0,0,Math.PI*2); ctx.fill();

    // hit flash
    let flash = e.hitFlash>0;
    // body base
    ctx.save();
    // step bob
    const bob = Math.sin(e.stepPhase)*2;
    ctx.translate(0, bob);

    if(type===3){
      // RAM: wooden ram with roof
      ctx.fillStyle = flash ? '#fee2e2' : '#78350f';
      // wheels
      ctx.fillStyle='#1f2937';
      ctx.beginPath(); ctx.arc(x-24, y+14,9,0,Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(x+24, y+14,9,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#57534e'; ctx.beginPath(); ctx.arc(x-24,y+14,3,0,Math.PI*2); ctx.fill(); ctx.beginPath(); ctx.arc(x+24,y+14,3,0,Math.PI*2); ctx.fill();
      // body
      ctx.fillStyle= flash ? '#fecaca' : '#92400e';
      ctx.fillRect(x-38, y-18, 76, 32);
      ctx.fillStyle='#451a03'; ctx.fillRect(x-38, y-18,76,6);
      // roof
      ctx.fillStyle='#422006';
      ctx.beginPath(); ctx.moveTo(x-42, y-18); ctx.lineTo(x, y-30); ctx.lineTo(x+42, y-18); ctx.closePath(); ctx.fill();
      // ram log
      ctx.fillStyle='#1c1917';
      ctx.fillRect(x+10, y-8, 48, 8);
      ctx.fillStyle='#57534e'; ctx.beginPath(); ctx.arc(x+58, y-4,8,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#f59e0b'; ctx.beginPath(); ctx.arc(x+58,y-4,4,0,Math.PI*2); ctx.fill();
      // crew
      ctx.fillStyle='#991b1b';
      ctx.fillRect(x-18, y-28, 10, 14);
      ctx.fillRect(x+8, y-28, 10, 14);
      // banner
      ctx.fillStyle='#dc2626';
      ctx.fillRect(x-30, y-36,14,10);
      ctx.fillStyle='#fff'; ctx.font='700 7px Inter'; ctx.fillText('✠', x-26, y-28);
      // health bar
      ctx.fillStyle='rgba(0,0,0,0.5)'; ctx.fillRect(x-30,y-42,60,6);
      ctx.fillStyle='#22c55e'; ctx.fillRect(x-30,y-42,60*(e.hp/e.maxHp),6);
      ctx.fillStyle='#fff'; ctx.font='700 7px Inter'; ctx.textAlign='center'; ctx.fillText(e.hp+'/'+e.maxHp, x, y-38); ctx.textAlign='left';
    } else {
      // infantry: silhouette style
      // legs marching
      const legOff = Math.sin(e.stepPhase*2)*4;
      ctx.fillStyle='#1f2937';
      ctx.fillRect(x-6+legOff, y+10, 5, 10);
      ctx.fillRect(x+2-legOff, y+10, 5, 10);
      // tunic
      let tunic = type===2 ? '#991b1b' : type===1 ? '#7c2d12' : '#9f1239';
      if(flash) tunic='#fff';
      ctx.fillStyle=tunic;
      ctx.fillRect(x-w/2+2, y-14, w-4, 18);
      // armor detail for shield type
      if(type===2){
        ctx.fillStyle= flash? '#fff' : '#e5e7eb';
        // shield in front
        ctx.beginPath();
        ctx.moveTo(x+8, y-16); ctx.lineTo(x+16, y-10); ctx.lineTo(x+16, y+10); ctx.lineTo(x+8, y+16); ctx.lineTo(x+2, y+10); ctx.lineTo(x+2, y-10); ctx.closePath(); ctx.fill();
        ctx.strokeStyle='#991b1b'; ctx.lineWidth=1.5;
        ctx.stroke();
        // cross faint
        ctx.strokeStyle='rgba(153,27,27,0.9)'; ctx.beginPath(); ctx.moveTo(x+9,y-4); ctx.lineTo(x+9,y+4); ctx.moveTo(x+5,y); ctx.lineTo(x+13,y); ctx.stroke();
      }
      // helmet
      ctx.fillStyle= flash? '#fef3c7' : '#e7e5e4';
      ctx.beginPath(); ctx.arc(x, y-14, 9, 0, Math.PI*2); ctx.fill();
      // nasal helm
      ctx.fillStyle='#57534e';
      ctx.fillRect(x-1, y-18,2,10);
      // cross/emblem for attackers
      if(type!==2){
        ctx.fillStyle='#dc2626';
        ctx.fillRect(x-5, y-12,10,2);
        ctx.fillRect(x-1, y-16,2,8);
      }
      // weapon
      ctx.fillStyle='#44403c';
      if(type===1){
        // spear forward
        ctx.fillRect(x-14, y-4, 22, 2);
        ctx.fillStyle='#e5e7eb'; ctx.beginPath(); ctx.moveTo(x+8,y-4); ctx.lineTo(x+12,y-5); ctx.lineTo(x+12,y-1); ctx.closePath(); ctx.fill();
      } else {
        ctx.fillRect(x-10, y+2, 14, 2);
        ctx.fillStyle='#e5e7eb'; ctx.beginPath(); ctx.moveTo(x+4,y+2); ctx.lineTo(x+8,y-1); ctx.lineTo(x+8,y+5); ctx.closePath(); ctx.fill();
      }
      // health pips for shield
      if(type===2 && e.hp<e.maxHp){
        ctx.fillStyle='rgba(0,0,0,0.5)'; ctx.fillRect(x-12, y-28,24,4);
        ctx.fillStyle='#22c55e'; ctx.fillRect(x-12,y-28,24*(e.hp/e.maxHp),4);
      }
    }
    ctx.restore();

    // dust behind feet
    if(!reduceMotion && Math.random()<0.18){
      ctx.fillStyle='rgba(120,113,108,0.35)';
      ctx.fillRect(x+ w/2, y+14, rand(2,6), 1.5);
    }
  });
}

function drawPickups(){
  pickups.forEach(p=>{
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.rot);
    const isHeal = p.type==='heal';
    // banner
    ctx.fillStyle = isHeal ? '#facc15' : '#38bdf8';
    ctx.fillRect(-14,-8,28,16);
    ctx.fillStyle='#0f172a';
    ctx.font='800 10px Inter'; ctx.textAlign='center';
    ctx.fillText(isHeal? '✚':'⚡', 0, 3);
    // tail
    ctx.fillStyle= isHeal? '#f59e0b' : '#0ea5e9';
    ctx.beginPath(); ctx.moveTo(-14,8); ctx.lineTo(-10,14); ctx.lineTo(-6,8); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(6,8); ctx.lineTo(10,14); ctx.lineTo(14,8); ctx.closePath(); ctx.fill();
    // glow
    ctx.shadowColor= isHeal? '#facc15' : '#38bdf8'; ctx.shadowBlur=8;
    ctx.strokeStyle= isHeal? 'rgba(250,204,21,0.6)' : 'rgba(56,189,248,0.6)';
    ctx.lineWidth=1.5; ctx.strokeRect(-14,-8,28,16);
    ctx.restore();
    ctx.textAlign='left';
  });
}

function drawArrows(){
  arrows.forEach(a=>{
    // trail
    ctx.strokeStyle='rgba(253,230,138,0.18)';
    ctx.lineWidth=2;
    ctx.beginPath();
    if(a.trail.length>1){
      ctx.moveTo(a.trail[0].x, a.trail[0].y);
      for(let i=1;i<a.trail.length;i++) ctx.lineTo(a.trail[i].x, a.trail[i].y);
      ctx.stroke();
    }
    // shaft
    const ang = Math.atan2(a.vy, a.vx);
    ctx.save();
    ctx.translate(a.x, a.y);
    ctx.rotate(ang);
    ctx.fillStyle='#fde68a';
    ctx.fillRect(-10, -1.2, 16, 2.4);
    // head
    ctx.fillStyle='#e5e7eb';
    ctx.beginPath(); ctx.moveTo(6,-3.5); ctx.lineTo(10,0); ctx.lineTo(6,3.5); ctx.closePath(); ctx.fill();
    // fletching
    ctx.fillStyle='#f43f5e';
    ctx.fillRect(-10,-3,5,2);
    ctx.fillRect(-10,1,5,2);
    ctx.restore();
  });
}

function drawParticles(){
  particles.forEach(pt=>{
    ctx.globalAlpha = clamp(pt.alpha,0,1);
    ctx.fillStyle=pt.color;
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, pt.size,0,Math.PI*2);
    ctx.fill();
  });
  ctx.globalAlpha=1;
}

function drawFloaters(){
  floaters.forEach(f=>{
    const a = clamp(f.life/0.85,0,1);
    ctx.globalAlpha=a;
    ctx.fillStyle=f.color;
    ctx.font='900 14px Inter';
    ctx.strokeStyle='rgba(0,0,0,0.7)'; ctx.lineWidth=3;
    ctx.textAlign='center';
    ctx.strokeText(f.text, f.x, f.y);
    ctx.fillText(f.text, f.x, f.y);
    ctx.textAlign='left';
  });
  ctx.globalAlpha=1;
}

function drawGateEffects(){
  // combo ring near gate when high
  if(combo>=4){
    const cx = WALL_X+42, cy = GATE_Y;
    ctx.strokeStyle=`rgba(250,204,21,${0.18 + Math.sin(Date.now()*0.008)*0.08})`;
    ctx.lineWidth=2;
    ctx.beginPath(); ctx.arc(cx, cy, 26 + combo*2,0,Math.PI*2); ctx.stroke();
    ctx.fillStyle='#facc15'; ctx.font='800 11px Inter'; ctx.textAlign='center';
    ctx.fillText('COMBO ×'+(1+combo*0.18).toFixed(1), cx, cy-36);
    ctx.textAlign='left';
  }
}

// ----- Start loop -----
updateHUD();
requestAnimationFrame(frame);

// Initial UI state — show touch controls if touch device
if('ontouchstart' in window || navigator.maxTouchPoints>0){
  touchControls.classList.add('visible');
  touchHint.style.display='block';
} else {
  // desktop: hide touch controls, keep hint subtle
  touchHint.textContent = 'Mouse to aim • Click / Space to fire • W/S to move';
}

// Preload best
if(highScores.length) renderBoard(boardTable);

// Reduce motion checkbox init
chkReduce.checked = reduceMotion;

// Visibility pause
document.addEventListener('visibilitychange', ()=>{
  if(document.hidden && phase==='playing'){ setPaused(true); }
});

// Prevent scrolling on touch
canvas.addEventListener('touchmove', e=>{ e.preventDefault(); }, {passive:false});
gameFrame.addEventListener('touchmove', e=>{ if(phase==='playing') e.preventDefault(); }, {passive:false});

// Instant restart via R anywhere
window.addEventListener('keydown', e=>{
  if(e.key.toLowerCase()==='r' && (phase==='over'||phase==='paused')){
    e.preventDefault(); startGame();
  }
});
