// Global Variables
var board = null;
var game = new Chess();
var gameId = null;
var isAnalysis = false;
var orientation = 'white';
var $status = $('#status-text');
var $fen = $('#fen');
var $pgn = $('#pgn');
var $engineStatus = $('#engine-status');

// API Base URL (assuming backend runs on same host/port or configured proxy)
// If opening index.html directly, we need absolute URL. 
// Assuming backend is localhost:5000 for now.
const API_BASE = '';

// --- Initialization ---

function onDragStart (source, piece, position, orientation) {
  // do not pick up pieces if the game is over
  if (game.game_over()) return false;

  // only pick up pieces for the side to move
  if (!isAnalysis) {
      // Get selected side
      const userSide = $('#side-select').val(); // 'white' or 'black'
      const turn = game.turn(); // 'w' or 'b'
      
      // Prevent moving if it's not user's turn
      if ((userSide === 'white' && turn === 'b') || 
          (userSide === 'black' && turn === 'w')) {
          return false;
      }
      
      // Prevent moving opponent's pieces even if it's their turn (shouldn't happen in normal play but good safety)
      if ((userSide === 'white' && piece.search(/^b/) !== -1) ||
          (userSide === 'black' && piece.search(/^w/) !== -1)) {
          return false;
      }
  }
}

function onDrop (source, target) {
  // see if the move is legal
  var move = game.move({
    from: source,
    to: target,
    promotion: 'q' // NOTE: always promote to a queen for example simplicity
  });

  // illegal move
  if (move === null) return 'snapback';

  // Legal move made on client. Send to backend.
  makeUserMove(source + target + (move.promotion ? move.promotion : ''));
  
  highlightMove(source, target);
  updateStatus();
  updateMoveList();
  updateCaptures();
}

// update the board position after the piece snap
// for castling, en passant, pawn promotion
function onSnapEnd () {
  board.position(game.fen());
}

var config = {
  draggable: true,
  position: 'start',
  onDragStart: onDragStart,
  onDrop: onDrop,
  onSnapEnd: onSnapEnd,
  pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
};

board = Chessboard('board', config);

// --- API Functions ---

async function startNewGame() {
    try {
        $engineStatus.text("Starting new game...");
        const response = await fetch(`${API_BASE}/start_game`, { method: 'POST' });
        const data = await response.json();
        
        if (data.ok) {
            gameId = data.game_id;
            game.load(data.fen);
            board.position(data.fen);
            
            // Handle Side Selection
            const userSide = $('#side-select').val();
            if (userSide === 'black') {
                board.orientation('black');
                makeBotMove(); // Bot (White) moves first
            } else {
                board.orientation('white');
            }
            orientation = userSide;
            
            updateStatus();
            updateMoveList();
            updateCaptures();
            resetEval();
            $('#board .square-55d63').removeClass('highlight-square'); // Clear highlights
            $engineStatus.text("Game Started");
            console.log("Game started:", gameId);
        } else {
            alert("Failed to start game: " + data.error);
        }
    } catch (e) {
        console.error(e);
        $engineStatus.text("Error connecting to backend");
    }
}

async function makeUserMove(uciMove) {
    if (!gameId) return;
    
    try {
        const response = await fetch(`${API_BASE}/make_move`, {
            method: 'POST',
            body: JSON.stringify({ game_id: gameId, move: uciMove }),
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.ok) {
            // Backend accepted move.
            // Trigger bot move if not in analysis mode and game isn't over
            // Bot should move if it's now the bot's turn
            const userSide = $('#side-select').val(); // 'white' or 'black'
            const currentTurn = game.turn(); // 'w' or 'b' after our move
            
            const isBotTurn = (userSide === 'white' && currentTurn === 'b') || 
                              (userSide === 'black' && currentTurn === 'w');
            
            if (!isAnalysis && !game.game_over() && isBotTurn) {
                makeBotMove();
            }
        } else {
            console.error("Move rejected by backend:", data.error);
            game.undo(); // Undo on client if backend rejects
            board.position(game.fen());
            alert("Illegal move rejected by server");
        }
    } catch (e) {
        console.error(e);
        game.undo();
        board.position(game.fen());
    }
}

async function makeBotMove() {
    if (!gameId) return;
    $engineStatus.text("Engine thinking...");
    
    try {
        const response = await fetch(`${API_BASE}/bot_move`, {
            method: 'POST',
            body: JSON.stringify({ game_id: gameId, depth: 3 }), // Default depth 3 for responsiveness
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.ok) {
            const bestMove = data.best_move; // UCI format e.g. "e7e5"
            const from = bestMove.substring(0, 2);
            const to = bestMove.substring(2, 4);
            const promotion = bestMove.length > 4 ? bestMove.substring(4, 5) : undefined;
            
            game.move({ from, to, promotion });
            board.position(game.fen());
            
            highlightMove(from, to);
            updateStatus();
            updateMoveList();
            updateCaptures();
            updateEval(data.eval);
            
            $engineStatus.text(`Engine played ${bestMove} (${data.time_s.toFixed(2)}s)`);
        } else {
            $engineStatus.text("Engine failed to move");
        }
    } catch (e) {
        console.error(e);
        $engineStatus.text("Error getting bot move");
    }
}

// --- UI Updates ---

function updateStatus () {
  var status = '';

  var moveColor = 'White';
  if (game.turn() === 'b') {
    moveColor = 'Black';
  }

  // checkmate?
  if (game.in_checkmate()) {
    status = 'Game over, ' + moveColor + ' is in checkmate.';
  }

  // draw?
  else if (game.in_draw()) {
    status = 'Game over, drawn position';
  }

  // game still on
  else {
    status = moveColor + ' to move';

    // check?
    if (game.in_check()) {
      status += ', ' + moveColor + ' is in check';
    }
  }

  $status.text(status);
}

function updateMoveList() {
    const history = game.history();
    const $list = $('#move-history');
    $list.empty();
    
    for (let i = 0; i < history.length; i += 2) {
        const num = (i / 2) + 1;
        const w = history[i];
        const b = history[i + 1] || '';
        
        const row = `
            <div class="move-row">
                <div class="move-num">${num}.</div>
                <div class="move-white">${w}</div>
                <div class="move-black">${b}</div>
            </div>
        `;
        $list.append(row);
    }
    
    // Scroll to bottom
    $list.scrollTop($list[0].scrollHeight);
}

function updateCaptures() {
    // Calculate material difference
    const currentFen = game.fen();
    const boardPart = currentFen.split(' ')[0];
    
    // Count current pieces
    const currentCounts = {
        'p': 0, 'n': 0, 'b': 0, 'r': 0, 'q': 0, 'k': 0,
        'P': 0, 'N': 0, 'B': 0, 'R': 0, 'Q': 0, 'K': 0
    };
    
    for (let char of boardPart) {
        if (/[pnbrqkPNBRQK]/.test(char)) {
            currentCounts[char]++;
        }
    }
    
    // Starting counts
    const startCounts = {
        'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1, 'k': 1,
        'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1, 'K': 1
    };
    
    const capturedW = []; // Captured by White (Black pieces missing)
    const capturedB = []; // Captured by Black (White pieces missing)
    
    // Check Black pieces missing (captured by White)
    ['p', 'n', 'b', 'r', 'q', 'k'].forEach(p => {
        const diff = startCounts[p] - currentCounts[p];
        for (let i = 0; i < diff; i++) capturedW.push(p);
    });
    
    // Check White pieces missing (captured by Black)
    ['P', 'N', 'B', 'R', 'Q', 'K'].forEach(p => {
        const diff = startCounts[p] - currentCounts[p];
        for (let i = 0; i < diff; i++) capturedB.push(p.toLowerCase());
    });
    
    renderCaptures('#captures-white', capturedW, 'b'); // White captured Black pieces
    renderCaptures('#captures-black', capturedB, 'w'); // Black captured White pieces
}

function renderCaptures(selector, pieces, colorPrefix) {
    const $container = $(selector);
    $container.empty();
    
    // Map piece char to symbol or image
    // Using simple text for now, or font awesome if available
    const pieceMap = {
        'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
    };
    // If using images, we would construct <img> tags.
    // For "Modern", let's use the actual piece images from chessboard.js theme if possible,
    // or just unicode. Unicode is easiest for single file.
    
    pieces.forEach(p => {
        const span = $('<span>').addClass('captured-piece').text(pieceMap[p]);
        // Style color
        if (colorPrefix === 'w') span.css('color', '#eee'); // White pieces
        else span.css('color', '#444'); // Black pieces (dark grey)
        
        // Better: use images from wikipedia theme
        // https://wikimedia.org/api/rest_v1/media/math/render/svg/... no
        // Let's use the same URL as chessboard.js default
        const imgUrl = `https://chessboardjs.com/img/chesspieces/wikipedia/${colorPrefix}${p.toUpperCase()}.png`;
        const img = $('<img>').attr('src', imgUrl).addClass('captured-piece');
        
        $container.append(img);
    });
}

function updateEval(score) {
    // Score is from White's perspective.
    // Range: -1000 to 1000 (roughly).
    // Bar: 50% is 0. 100% is +1000 (White win). 0% is -1000 (Black win).
    
    if (score === null || score === undefined) return;
    
    // Clamp score
    let clamped = Math.max(-2.0, Math.min(2.0, score));
    
    // Normalize to 0-100%
    // 0 -> 50%
    // 2.0 -> 100%
    // -2.0 -> 0%
    let percent = 50 + (clamped * 25); // 2.0 * 25 = 50. 50+50=100.
    
    $('#eval-bar-fill').css('height', percent + '%');
    $('#eval-score').text(score.toFixed(2));
}

function resetEval() {
    $('#eval-bar-fill').css('height', '50%');
    $('#eval-score').text('0.0');
}

// --- Event Listeners ---

$('#btn-new-game').on('click', startNewGame);

$('#btn-flip').on('click', function() {
    board.flip();
    orientation = board.orientation();
});

$('#btn-analysis').on('click', function() {
    isAnalysis = !isAnalysis;
    const btn = $(this);
    if (isAnalysis) {
        btn.html('<i class="fa-solid fa-microscope"></i> Analysis: On');
        btn.addClass('btn-primary').removeClass('btn-secondary');
    } else {
        btn.html('<i class="fa-solid fa-microscope"></i> Analysis: Off');
        btn.addClass('btn-secondary').removeClass('btn-primary');
    }
});

$('#theme-select').on('change', function() {
    const theme = this.value;
    const $boardContainer = $('#board');
    const $boardWrapper = $boardContainer.parent();
    
    // Remove all theme classes from board container
    $boardContainer.removeClass('theme-classic theme-blue theme-dark theme-wood');
    $boardWrapper.removeClass('theme-classic theme-blue theme-dark theme-wood');
    
    // Add new theme class
    $boardContainer.addClass('theme-' + theme);
    
    // Force Chessboard.js to redraw by updating position
    board.position(game.fen());
});

function highlightMove(from, to) {
    // Remove old highlights
    $('#board .square-55d63').removeClass('highlight-square');
    
    // Add new highlights
    $('#board .square-' + from).addClass('highlight-square');
    $('#board .square-' + to).addClass('highlight-square');
}

// Start a game on load
$(document).ready(function() {
    startNewGame();
});
