import random
from pieces import Pawn, Knight, Bishop, Rook, Queen, King
from constants import WHITE, PIECEBLACK

# Standard chess piece values
PIECE_VALUES = {
    Pawn: 10,
    Knight: 30,
    Bishop: 30,
    Rook: 50,
    Queen: 90,
    King: 900
}

def evaluate_board(pieces):
    """
    Evaluates the current board state.
    Positive score favors White, negative score favors Black.
    """
    score = 0
    for piece in pieces:
        if piece:
            val = PIECE_VALUES.get(type(piece), 0)
            if piece.color == WHITE:
                score += val
            else:
                score -= val
    return score

def get_all_legal_moves(game, color):
    """Returns a list of tuples (from_sq, to_sq) of all legal moves for a given color."""
    moves = []
    for square, piece in enumerate(game.pieces):
        if piece and piece.color == color:
            for dest in game.getLegalMoves(square):
                moves.append((square, dest))
    return moves

def minimax(game, depth, alpha, beta, maximizing_player):
    """
    Recursive Minimax algorithm with Alpha-Beta pruning.
    """
    if depth == 0:
        return evaluate_board(game.pieces)
        
    color = WHITE if maximizing_player else PIECEBLACK
    moves = get_all_legal_moves(game, color)
    
    # Terminal states (Checkmate or Stalemate)
    if not moves:
        if game.isKingInCheck(color):
            # Checkmate: returning a massive penalty/reward
            return -9999 if maximizing_player else 9999
        return 0  # Stalemate
        
    if maximizing_player:
        max_eval = -float('inf')
        for fr, to in moves:
            # Simulate the move by temporarily swapping array elements
            piece = game.pieces[fr]
            captured = game.pieces[to]
            game.pieces[to] = piece
            game.pieces[fr] = None
            
            eval_score = minimax(game, depth - 1, alpha, beta, False)
            
            # Revert the simulation
            game.pieces[fr] = piece
            game.pieces[to] = captured
            
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cutoff
        return max_eval
    else:
        min_eval = float('inf')
        for fr, to in moves:
            piece = game.pieces[fr]
            captured = game.pieces[to]
            game.pieces[to] = piece
            game.pieces[fr] = None
            
            eval_score = minimax(game, depth - 1, alpha, beta, True)
            
            game.pieces[fr] = piece
            game.pieces[to] = captured
            
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cutoff
        return min_eval

def get_best_move(game, depth=2):
    """
    Kickstarts the Minimax tree to find the best move for the current turn.
    """
    maximizing = (game.turn == WHITE)
    best_move = None
    
    moves = get_all_legal_moves(game, game.turn)
    if not moves:
        return None
        
    # Shuffle moves so the AI doesn't repeatedly play the exact same opening every game
    random.shuffle(moves)
    
    # Seed the alpha/beta values
    alpha = -float('inf')
    beta = float('inf')
    best_score = -float('inf') if maximizing else float('inf')
    
    for fr, to in moves:
        piece = game.pieces[fr]
        captured = game.pieces[to]
        game.pieces[to] = piece
        game.pieces[fr] = None
        
        score = minimax(game, depth - 1, alpha, beta, not maximizing)
        
        game.pieces[fr] = piece
        game.pieces[to] = captured
        
        if maximizing:
            if score > best_score:
                best_score = score
                best_move = (fr, to)
            alpha = max(alpha, score)
        else:
            if score < best_score:
                best_score = score
                best_move = (fr, to)
            beta = min(beta, score)
            
    return best_move