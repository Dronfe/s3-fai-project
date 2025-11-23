// Configuration
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// State
let board = null;
let game = new Chess();
let isEngineThinking = false;
let currentSide = 'white'; // 'white' or 'black'
let engineDepth = 10; // Visual only for now
let gameMode = 'play'; // 'play' or 'analysis'

// DOM Elements
const boardEl = document.getElementById('board');
const statusEl = document.getElementById('gameStatus');
const engineStatusEl = document.getElementById('engineStatus');
const playerStatusEl = document.getElementById('playerStatus');
const pgnEl = document.getElementById('pgn-container');
const evalFillEl = document.getElementById('eval-fill');
const capturedWhiteEl = document.getElementById('captured-white');
const capturedBlackEl = document.getElementById('captured-black');

// Modals
const newGameModal = document.getElementById('newGameModal');
const gameOverModal = document.getElementById('gameOverModal');

// Buttons
const newGameTrigger = document.getElementById('newGameTrigger');
const flipBoardBtn = document.getElementById('flipBoardBtn');
const themeToggle = document.getElementById('themeToggle');
const confirmNewGameBtn = document.getElementById('confirmNewGame');
const cancelNewGameBtn = document.getElementById('cancelNewGame');
const closeGameOverBtn = document.getElementById('closeGameOver');

// Inputs
const depthRange = document.getElementById('depthRange');
const depthValue = document.getElementById('depthValue');
const newGameMode = document.getElementById('newGameMode');

// Initialization
$(document).ready(function() {
    initBoard();
    setupEventListeners();
    // Open new game modal on load
    openModal(newGameModal);
});

function initBoard() {
    const boardEl = document.getElementById('board');
    if (!boardEl) {
        console.error("Board element not found!");
        return;
    }

    const config = {
        draggable: true,
        position: 'start',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
    };
    
    // Ensure board element has dimensions
    if (boardEl.clientWidth === 0) {
        console.warn("Board element has 0 width, resizing might be needed later.");
    }

    try {
        board = Chessboard('board', config);
        $(window).resize(board.resize);
        
        // Force resize after a short delay to handle layout settling
        setTimeout(board.resize, 200);
    } catch (e) {
        console.error("Error initializing chessboard:", e);
    }
}

function setupEventListeners() {
    // Modal Triggers
    newGameTrigger.addEventListener('click', () => openModal(newGameModal));
    cancelNewGameBtn.addEventListener('click', () => closeModal(newGameModal));
    closeGameOverBtn.addEventListener('click', () => closeModal(gameOverModal));
    
    // Game Controls
    confirmNewGameBtn.addEventListener('click', startNewGame);
    flipBoardBtn.addEventListener('click', () => board.flip());
    
    // Settings
    depthRange.addEventListener('input', (e) => {
        depthValue.innerText = e.target.value;
        engineDepth = parseInt(e.target.value);
    });
    
    themeToggle.addEventListener('click', toggleTheme);
}

function toggleTheme() {
    const body = document.body;
    const current = body.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    body.setAttribute('data-theme', next);
}

function openModal(modal) {
    modal.classList.remove('hidden');
    // Small delay to allow display:flex to apply before opacity transition
    setTimeout(() => modal.classList.add('active'), 10);
}

function closeModal(modal) {
    modal.classList.remove('active');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

// Game Logic
function onDragStart(source, piece, position, orientation) {
    if (game.game_over()) return false;
    if (isEngineThinking) return false;

    // Only allow moving own pieces in play mode
    if (gameMode === 'play') {
        if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
            (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
            return false;
        }
        // If playing as black, don't let move white
        if (currentSide === 'black' && game.turn() === 'w') return false;
        if (currentSide === 'white' && game.turn() === 'b') return false;
    }
}

function onDrop(source, target) {
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });

    if (move === null) return 'snapback';

    updateStatus();
    
    if (gameMode === 'play' && !game.game_over()) {
        // Check if it's engine's turn
        const engineColor = currentSide === 'white' ? 'b' : 'w';
        if (game.turn() === engineColor) {
            setTimeout(makeBotMove, 500); // Small delay for realism
        }
    }
}

function onSnapEnd() {
    board.position(game.fen());
}

function updateStatus() {
    let status = '';
    let moveColor = game.turn() === 'w' ? 'White' : 'Black';

    if (game.in_checkmate()) {
        status = 'Game over, ' + moveColor + ' is in checkmate.';
        showGameOver(moveColor === 'White' ? 'Black Wins!' : 'White Wins!', status);
    } else if (game.in_draw()) {
        status = 'Game over, drawn position';
        showGameOver('Draw', status);
    } else {
        status = moveColor + ' to move';
        if (game.in_check()) {
            status += ', ' + moveColor + ' is in check';
        }
    }

    // Update status text
    if (gameMode === 'play') {
        if (game.turn() === (currentSide === 'white' ? 'w' : 'b')) {
            playerStatusEl.innerText = "Your Turn";
            playerStatusEl.style.color = "var(--accent-primary)";
            engineStatusEl.innerText = "Waiting";
            engineStatusEl.style.color = "var(--text-secondary)";
        } else {
            playerStatusEl.innerText = "Waiting";
            playerStatusEl.style.color = "var(--text-secondary)";
            engineStatusEl.innerText = "Thinking...";
            engineStatusEl.style.color = "var(--accent-primary)";
        }
    } else {
        playerStatusEl.innerText = status;
    }

    updatePGN();
    updateCapturedPieces();
}

function showGameOver(title, message) {
    document.getElementById('gameOverTitle').innerText = title;
    document.getElementById('gameOverMessage').innerText = message;
    openModal(gameOverModal);
}

// Bot Logic (Client-side Random/Simple)
function makeBotMove() {
    isEngineThinking = true;
    engineStatusEl.innerText = "Thinking...";
    
    // Simple random move for now since backend is removed
    // In a real frontend-only engine, we'd use a JS engine or WebAssembly
    const moves = game.moves();
    if (moves.length === 0) return;

    const randomMove = moves[Math.floor(Math.random() * moves.length)];
    game.move(randomMove);
    
    board.position(game.fen());
    updateStatus();
    
    // Mock eval update
    updateEvaluation(Math.random() * 2 - 1); // Random small eval
    
    isEngineThinking = false;
}

function startNewGame() {
    // Get settings from modal
    const sideInputs = document.getElementsByName('newGameSide');
    for (const input of sideInputs) {
        if (input.checked) currentSide = input.value;
    }
    gameMode = newGameMode.value;
    engineDepth = parseInt(depthRange.value);

    closeModal(newGameModal);
    
    // Wait for modal transition to finish/layout to stabilize then resize board
    setTimeout(() => {
        board.resize();
    }, 350);

    game.reset();
    board.start();
    
    // Handle side selection
    if (currentSide === 'black') {
        board.orientation('black');
        // If playing black, engine moves first
        if (gameMode === 'play') {
            setTimeout(makeBotMove, 500);
        }
    } else {
        board.orientation('white');
    }
    
    updateStatus();
    resetEval();
    updateCapturedPieces();
}

// UI Updates
function updatePGN() {
    const history = game.history();
    let html = '';
    for (let i = 0; i < history.length; i += 2) {
        const num = (i / 2) + 1;
        const w = history[i];
        const b = history[i + 1] || '';
        html += `
            <div class="move-row">
                <span class="move-num">${num}.</span>
                <span class="move-ply">${w}</span>
                <span class="move-ply">${b}</span>
            </div>
        `;
    }
    pgnEl.innerHTML = html || '<div class="pgn-placeholder">Game started</div>';
    pgnEl.scrollTop = pgnEl.scrollHeight;
}

function updateCapturedPieces() {
    // Simple captured piece tracking
    // Compare current board counts vs start counts
    // This is a bit complex to do perfectly without tracking every capture event
    // For now, we'll just clear it or implement a basic diff if needed
    // But since the user wants "frontend only", maybe just leave it empty or mock it
    // Let's try to do a basic diff based on material
    
    const pieceValues = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
    const startCounts = { w: {p:8,n:2,b:2,r:2,q:1}, b: {p:8,n:2,b:2,r:2,q:1} };
    
    // Count current pieces
    const currentCounts = { w: {p:0,n:0,b:0,r:0,q:0}, b: {p:0,n:0,b:0,r:0,q:0} };
    const boardState = game.board();
    
    for(let row of boardState) {
        for(let sq of row) {
            if(sq) {
                currentCounts[sq.color][sq.type]++;
            }
        }
    }
    
    // Calculate captured
    let whiteCapturedHtml = ''; // Pieces white captured (Black pieces)
    let blackCapturedHtml = ''; // Pieces black captured (White pieces)
    
    ['p','n','b','r','q'].forEach(type => {
        // Black pieces missing (captured by White)
        let bMissing = startCounts.b[type] - currentCounts.b[type];
        for(let i=0; i<bMissing; i++) {
            whiteCapturedHtml += `<img src="https://chessboardjs.com/img/chesspieces/wikipedia/b${type.toUpperCase()}.png" class="captured-piece">`;
        }
        
        // White pieces missing (captured by Black)
        let wMissing = startCounts.w[type] - currentCounts.w[type];
        for(let i=0; i<wMissing; i++) {
            blackCapturedHtml += `<img src="https://chessboardjs.com/img/chesspieces/wikipedia/w${type.toUpperCase()}.png" class="captured-piece">`;
        }
    });
    
    capturedWhiteEl.innerHTML = whiteCapturedHtml;
    capturedBlackEl.innerHTML = blackCapturedHtml;
}

function updateEvaluation(score) {
    if (score === undefined || score === null) return;
    
    let evalVal = 50; // Default 50%
    
    // Simple mock visual for now
    const clamped = Math.max(-5, Math.min(5, score));
    evalVal = 50 + (clamped * 10); 
    
    evalFillEl.style.height = `${evalVal}%`;
}

function resetEval() {
    evalFillEl.style.height = '50%';
}
