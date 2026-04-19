from pieces import Pawn, King, Rook, Bishop, Knight, Queen
from constants import WHITE, PIECEBLACK

class ChessLogic:
    """
    Pure chess logic module separating rules and math from rendering.
    """
    def __init__(self):
        self.pieces = [None] * 64
        self.turn = WHITE
        self.enPassantSquare = None
        self.whiteKingMoved = False
        self.blackKingMoved = False
        self.whiteRookMoved = [False, False]  # [queenside, kingside]
        self.blackRookMoved = [False, False]
        self.moveHistory = []
        self.moveNotation = []

    def get_state(self):
        """Return the current castling and en passant state flags."""
        return {
            'en_passant_square': self.enPassantSquare,
            'white_king_moved': self.whiteKingMoved,
            'black_king_moved': self.blackKingMoved,
            'white_rook_moved': self.whiteRookMoved,
            'black_rook_moved': self.blackRookMoved
        }

    def switch_turn(self):
        self.turn = PIECEBLACK if self.turn == WHITE else WHITE

    def get_legal_moves(self, square):
        """Get all mathematically legal moves for a piece, considering checks."""
        piece = self.pieces[square]
        if not piece: return []

        pseudo_moves = piece.get_pseudo_legal_moves(self.pieces, square, self.get_state())
        moves = []

        for to in pseudo_moves:
            captured = self.pieces[to]
            self.pieces[to] = piece
            self.pieces[square] = None

            king_check = self.is_king_in_check(piece.color)

            # Revert simulation
            self.pieces[square] = piece
            self.pieces[to] = captured

            if not king_check:
                # Validate castling paths
                if isinstance(piece, King) and abs((to % 8) - (square % 8)) == 2:
                    if self.is_king_in_check(piece.color): continue
                    
                    pass_through_sq = square + (1 if to > square else -1)
                    self.pieces[pass_through_sq] = piece
                    self.pieces[square] = None
                    pass_check = self.is_king_in_check(piece.color)
                    self.pieces[square] = piece
                    self.pieces[pass_through_sq] = None
                    
                    if pass_check: continue
                moves.append(to)

        return moves

    def is_king_in_check(self, color):
        """Check if the king of the specified color is under attack."""
        king_square = None
        for i, p in enumerate(self.pieces):
            if isinstance(p, King) and p.color == color:
                king_square = i
                break

        if king_square is None: return True

        state = self.get_state()
        for i, p in enumerate(self.pieces):
            if p and p.color != color:
                if king_square in p.get_pseudo_legal_moves(self.pieces, i, state):
                    return True
        return False

    def is_checkmate(self, color):
        if not self.is_king_in_check(color): return False
        for i, p in enumerate(self.pieces):
            if p and p.color == color:
                if self.get_legal_moves(i): return False
        return True

    def is_stalemate(self, color):
        if self.is_king_in_check(color): return False
        for i, p in enumerate(self.pieces):
            if p and p.color == color:
                if self.get_legal_moves(i): return False
        return True

    def square_to_algebraic(self, square):
        file = chr(ord('a') + (square % 8))
        rank = str((square // 8) + 1)
        return file + rank

    def format_move(self, move_record):
        piece = move_record['moving_piece']
        fr = move_record['fr']
        to = move_record['to']
        captured = move_record['captured_piece']
        
        if move_record['castling']:
            return "O-O" if to > fr else "O-O-O"
        elif move_record['promotion']:
            piece_type = move_record['promoted_piece'].__class__.__name__[0]
            if captured:
                return self.square_to_algebraic(fr)[0] + "x" + self.square_to_algebraic(to) + "=" + piece_type
            else:
                return self.square_to_algebraic(to) + "=" + piece_type
        else:
            piece_letter = "" if isinstance(piece, Pawn) else piece.__class__.__name__[0]
            capture_symbol = "x" if captured or (isinstance(piece, Pawn) and to == move_record.get('en_passant_square')) else ""
            return piece_letter + capture_symbol + self.square_to_algebraic(to)

    def execute_move(self, fr, to):
        """Mathematically execute a move and return the result data."""
        moving = self.pieces[fr]
        target = self.pieces[to]

        move_record = {
            'fr': fr, 'to': to,
            'moving_piece': moving, 'captured_piece': target,
            'en_passant_square': self.enPassantSquare,
            'castling': False, 'promotion': False, 'promoted_piece': None,
            'white_king_moved': self.whiteKingMoved, 'black_king_moved': self.blackKingMoved,
            'white_rooks_moved': self.whiteRookMoved.copy(), 'black_rooks_moved': self.blackRookMoved.copy(),
            'turn': self.turn
        }

        self.pieces[to] = moving
        self.pieces[fr] = None
        if moving: moving.square = to

        if isinstance(moving, Pawn) and to == self.enPassantSquare:
            captured = to - 8 if moving.color == WHITE else to + 8
            victim = self.pieces[captured]
            if victim:
                self.pieces[captured] = None
                move_record['en_passant_capture'] = captured
                move_record['en_passant_victim'] = victim

        if isinstance(moving, Pawn) and abs((to // 8) - (fr // 8)) == 2:
            self.enPassantSquare = fr + (8 if moving.color == WHITE else -8)
        else:
            self.enPassantSquare = None

        if isinstance(moving, King) and abs((to % 8) - (fr % 8)) == 2:
            move_record['castling'] = True
            rook_from = fr + 3 if to > fr else fr - 4
            rook_to = fr + 1 if to > fr else fr - 1
            rook = self.pieces[rook_from]
            self.pieces[rook_from] = None
            self.pieces[rook_to] = rook
            if rook: rook.square = rook_to
            move_record['rook_from'] = rook_from
            move_record['rook_to'] = rook_to

        if isinstance(moving, King):
            if moving.color == WHITE: self.whiteKingMoved = True
            else: self.blackKingMoved = True

        if isinstance(moving, Rook):
            if fr == 0: self.whiteRookMoved[0] = True
            if fr == 7: self.whiteRookMoved[1] = True
            if fr == 56: self.blackRookMoved[0] = True
            if fr == 63: self.blackRookMoved[1] = True

        self.moveHistory.append(move_record)
        
        is_promotion = isinstance(moving, Pawn) and ((moving.color == WHITE and to // 8 == 7) or (moving.color == PIECEBLACK and to // 8 == 0))
        if not is_promotion:
            notation = self.format_move(move_record)
            self.moveNotation.append(notation)
            
        return move_record

    def complete_promotion(self, square, new_piece):
        pawn = self.pieces[square]
        self.pieces[square] = new_piece
        if self.moveHistory:
            last_move = self.moveHistory[-1]
            last_move['promotion'] = True
            last_move['promoted_piece'] = new_piece
            last_move['original_pawn'] = pawn
            notation = self.format_move(last_move)
            self.moveNotation.append(notation)

    def undo_move(self):
        """Mathematically revert the last move."""
        if not self.moveHistory: return None
        last_move = self.moveHistory.pop()
        
        if 'moving_piece' not in last_move:
            return last_move  # Deserialized moves handled upstream
            
        fr = last_move['fr']
        to = last_move['to']
        moving_piece = last_move['moving_piece']
        captured_piece = last_move['captured_piece']
        
        is_uncompleted_promotion = isinstance(moving_piece, Pawn) and ((moving_piece.color == WHITE and to // 8 == 7) or (moving_piece.color == PIECEBLACK and to // 8 == 0)) and not last_move['promotion']
        if not is_uncompleted_promotion and self.moveNotation:
            self.moveNotation.pop()
        
        self.pieces[fr] = moving_piece
        self.pieces[to] = captured_piece
        if moving_piece: moving_piece.square = fr
        if captured_piece: captured_piece.square = to
        
        if 'en_passant_capture' in last_move:
            captured_sq = last_move['en_passant_capture']
            victim = last_move['en_passant_victim']
            self.pieces[captured_sq] = victim
            if victim: victim.square = captured_sq
            
        if last_move['castling']:
            rook_from = last_move['rook_from']
            rook_to = last_move['rook_to']
            rook = self.pieces[rook_to]
            self.pieces[rook_from] = rook
            self.pieces[rook_to] = None
            if rook: rook.square = rook_from
            
        if last_move['promotion']:
            original_pawn = last_move['original_pawn']
            self.pieces[to] = original_pawn
            if original_pawn: original_pawn.square = to
            
        self.enPassantSquare = last_move['en_passant_square']
        self.whiteKingMoved = last_move['white_king_moved']
        self.blackKingMoved = last_move['black_king_moved']
        self.whiteRookMoved = last_move['white_rooks_moved']
        self.blackRookMoved = last_move['black_rooks_moved']
        self.turn = last_move['turn']
        
        return last_move