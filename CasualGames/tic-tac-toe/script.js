const boardEl = document.getElementById('board');
const turnEl = document.getElementById('turn-player');
const restartBtn = document.getElementById('restart');
const resetScoresBtn = document.getElementById('reset-scores');
const modeLocal = document.getElementById('mode-local');
const modeAi = document.getElementById('mode-ai');
const difficultySelect = document.getElementById('difficulty');
const announcer = document.getElementById('announcer');
const scoreXEl = document.getElementById('score-x');
const scoreOEl = document.getElementById('score-o');
// swap feature removed

// confetti canvas (created dynamically)
const confettiCanvas = document.createElement('canvas');
confettiCanvas.id = 'confetti';
document.body.appendChild(confettiCanvas);
const confettiCtx = confettiCanvas.getContext('2d');
let confettiPieces = [];
function resizeConfetti(){ confettiCanvas.width = window.innerWidth; confettiCanvas.height = window.innerHeight; }
window.addEventListener('resize', resizeConfetti);
resizeConfetti();


let board = Array(9).fill(null);
let current = 'X';
let running = true;
let scores = { X: 0, O: 0 };

// Mode and AI symbols (human always X in single-player mode)
function getMode(){ return modeAi.checked ? 'ai' : 'local'; }
const HUMAN = 'X';
const AI = 'O';

const winningCombos = [
  [0,1,2],[3,4,5],[6,7,8],
  [0,3,6],[1,4,7],[2,5,8],
  [0,4,8],[2,4,6]
];

function createBoard(){
  boardEl.innerHTML = '';
  for(let i=0;i<9;i++){
    const cell = document.createElement('button');
    cell.className = 'cell';
    cell.type = 'button';
    cell.dataset.index = i;
    cell.setAttribute('aria-label', `Cell ${i+1}`);
    cell.setAttribute('role','gridcell');
    cell.tabIndex = 0;
    cell.addEventListener('click', onCellClick);
    cell.addEventListener('keydown', onCellKeyDown);
    boardEl.appendChild(cell);
  }
}

function onCellKeyDown(e){
  const key = e.key;
  const idx = Number(e.currentTarget.dataset.index);
  if(key === 'Enter' || key === ' '){
    e.preventDefault();
    e.currentTarget.click();
    return;
  }

  let target = null;
  if(key === 'ArrowRight') target = (idx % 3 === 2) ? idx - 2 : idx + 1;
  if(key === 'ArrowLeft') target = (idx % 3 === 0) ? idx + 2 : idx - 1;
  if(key === 'ArrowDown') target = (idx + 3) % 9;
  if(key === 'ArrowUp') target = (idx + 6) % 9;

  if(target !== null){
    const el = boardEl.querySelector(`[data-index='${target}']`);
    if(el) el.focus();
  }
}

function onCellClick(e){
  const idx = Number(e.currentTarget.dataset.index);
  if(!running || board[idx]) return;
  // normal click handling
  // In single-player mode human must be X
  if(getMode() === 'ai'){
    if(current !== HUMAN) return; // wait for AI turn
    makeMove(idx, HUMAN);
    // schedule AI response
    if(running) setTimeout(()=>{ if(running) aiTurn(); }, 300 + Math.random()*300);
  } else {
    makeMove(idx, current);
  }
}

function makeMove(idx, player){
  board[idx] = player;
  const cell = boardEl.querySelector(`[data-index='${idx}']`);
  cell.classList.add('filled');
  const mark = document.createElement('span');
  mark.className = `mark ${player.toLowerCase()}`;
  mark.textContent = player;
  cell.appendChild(mark);

  // check win or draw
  const winner = checkWinner();
  if(winner){
    running = false;
    scores[winner]++;
    updateScores();
    highlightWin(winner);
    const msg = `${winner} wins!`;
    showResult(msg);
    announce(`${winner} wins`);
    showPopup('win', msg);
    // confetti
    launchConfetti();
    return;
  }

  if(board.every(Boolean)){
    running = false;
    const msg = 'Draw';
    showResult(msg);
    announce('Draw');
    showPopup('draw', msg);
    launchConfetti();
    return;
  }

  current = current === 'X' ? 'O' : 'X';
  turnEl.textContent = current;
  announce(`Turn: ${current}`);
}

// swap functionality removed

// confetti implementation (minimal)
function launchConfetti(){
  confettiPieces = [];
  const count = 80;
  for(let i=0;i<count;i++){
    confettiPieces.push({
      x: Math.random()*confettiCanvas.width,
      y: -10 - Math.random()*200,
      vx: (Math.random()-0.5)*6,
      vy: 2 + Math.random()*4,
      r: 6 + Math.random()*6,
      color: `hsl(${Math.random()*360},90%,60%)`,
      rot: Math.random()*360
    });
  }
  requestAnimationFrame(stepConfetti);
  setTimeout(()=>{ confettiPieces = []; confettiCtx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height); }, 4000);
}

function stepConfetti(){
  confettiCtx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height);
  for(const p of confettiPieces){
    p.x += p.vx; p.y += p.vy; p.vy += 0.08; p.rot += 4;
    confettiCtx.save();
    confettiCtx.translate(p.x,p.y);
    confettiCtx.rotate(p.rot*Math.PI/180);
    confettiCtx.fillStyle = p.color;
    confettiCtx.fillRect(-p.r/2,-p.r/2,p.r,p.r*0.6);
    confettiCtx.restore();
  }
  confettiPieces = confettiPieces.filter(p=>p.y < confettiCanvas.height + 50);
  if(confettiPieces.length) requestAnimationFrame(stepConfetti);
}

function checkWinner(b = board){
  for(const [a,bIdx,c] of winningCombos){
    if(b[a] && b[a] === b[bIdx] && b[a] === b[c]){
      return b[a];
    }
  }
  return null;
}

function highlightWin(player){
  // find winning combo
  for(const combo of winningCombos){
    const [a,b,c] = combo;
    if(board[a] === player && board[b] === player && board[c] === player){
      // add simple highlight by scaling cells
      [a,b,c].forEach(i=>{
        const el = boardEl.querySelector(`[data-index='${i}']`);
        el.style.boxShadow = `0 10px 30px rgba(0,0,0,0.6), 0 0 0 6px rgba(124,58,237,0.12)`;
        el.animate([{transform:'scale(1)'},{transform:'scale(1.06)'},{transform:'scale(1)'}],{duration:700,iterations:1});
      });
      break;
    }
  }
}

function showResult(text){
  turnEl.textContent = text;
}

function announce(text){
  if(!announcer) return;
  announcer.textContent = text;
}

function updateScores(){
  scoreXEl.textContent = scores.X;
  scoreOEl.textContent = scores.O;
}

function resetBoard(keepScore = true){
  board = Array(9).fill(null);
  running = true;
  current = 'X';
  turnEl.textContent = current;
  createBoard();
  // focus first cell for keyboard users
  const first = boardEl.querySelector(`[data-index='0']`);
  if(first) first.focus();
  if(!keepScore){scores = {X:0,O:0}; updateScores();}
}

restartBtn.addEventListener('click', ()=>{ resetBoard(true); announce('Board restarted'); });

resetScoresBtn.addEventListener('click', ()=>{ scores = {X:0,O:0}; updateScores(); announce('Scores reset'); });

modeLocal.addEventListener('change', ()=>{ resetBoard(true); announce('Two-player mode'); });
modeAi.addEventListener('change', ()=>{ resetBoard(true); announce('Single-player mode'); });
difficultySelect.addEventListener('change', ()=>{ announce(`Difficulty ${difficultySelect.value}`); });

// swap listeners removed

// Popup elements
const popup = document.getElementById('popup');
const popupCard = document.getElementById('popup-card');
const popupMessage = document.getElementById('popup-message');
const popupIcon = document.getElementById('popup-icon');
const popupRestart = document.getElementById('popup-restart');
const popupClose = document.getElementById('popup-close');

function showPopup(type, text){
  if(!popup) return;
  popup.setAttribute('aria-hidden','false');
  popupMessage.textContent = text;
  popupIcon.textContent = type === 'win' ? '🏆' : type === 'lose' ? '😞' : '🤝';
  // focus first action for keyboard users
  popupRestart.focus();
}

function hidePopup(){
  if(!popup) return;
  popup.setAttribute('aria-hidden','true');
  // return focus to first cell
  const first = boardEl.querySelector(`[data-index='0']`);
  if(first) first.focus();
}

popupRestart.addEventListener('click', ()=>{ hidePopup(); resetBoard(true); announce('Board restarted'); });
popupClose.addEventListener('click', ()=>{ hidePopup(); announce('Closed result'); });


// AI logic
function aiTurn(){
  if(!running) return;
  const diff = difficultySelect.value || 'medium';
  let idx = null;
  const avail = board.map((v,i)=>v===null?i:null).filter(v=>v!==null);

  if(diff === 'easy'){
    idx = avail[Math.floor(Math.random()*avail.length)];
  } else if(diff === 'medium'){
    // Win if possible
    idx = findWinningMove(AI) ?? findWinningMove(HUMAN) ?? avail[Math.floor(Math.random()*avail.length)];
  } else {
    // hard -> minimax
    const best = minimax(board, AI, 0);
    idx = best.index;
  }

  if(idx !== null && idx !== undefined) makeMove(idx, AI);
}

function findWinningMove(player){
  const avail = board.map((v,i)=>v===null?i:null).filter(v=>v!==null);
  for(const i of avail){
    const copy = board.slice();
    copy[i] = player;
    if(checkWinner(copy) === player) return i;
  }
  return null;
}

function availableMoves(bd){
  return bd.map((v,i)=>v===null?i:null).filter(v=>v!==null);
}

function minimax(newBoard, player, depth){
  const winner = checkWinner(newBoard);
  if(winner === AI) return {score: 10 - depth};
  if(winner === HUMAN) return {score: depth - 10};
  if(newBoard.every(Boolean)) return {score: 0};

  const moves = [];
  const avail = availableMoves(newBoard);

  for(const i of avail){
    const copy = newBoard.slice();
    copy[i] = player;
    const result = minimax(copy, player === AI ? HUMAN : AI, depth+1);
    moves.push({index: i, score: result.score});
  }

  // choose best depending on player
  let bestMove;
  if(player === AI){
    let bestScore = -Infinity;
    for(const m of moves) if(m.score > bestScore){ bestScore = m.score; bestMove = m; }
  } else {
    let bestScore = Infinity;
    for(const m of moves) if(m.score < bestScore){ bestScore = m.score; bestMove = m; }
  }

  return bestMove;
}

// initialize
createBoard();
updateScores();
