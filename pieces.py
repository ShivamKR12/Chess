from panda3d.core import Material
from constants import SquarePos, WHITE, PIECEBLACK


class Piece:
    """
    Base class for all chess pieces.

    Each piece has a square position, color, and 3D model.
    Subclasses define the specific model file to load.
    """

    def __init__(self, square, color, parent=None):
        """
        Constructor for Piece.

        Parameters:
        - square: Initial square index (0-63)
        - color: Piece color (WHITE or PIECEBLACK)
        - parent: Parent node to attach the model to (defaults to render)
        """
        self.square = square  # Current square
        self.color = color    # Piece color

        # Load the 3D model for this piece type
        self.obj = loader.loadModel(self.model) # type: ignore

        # Add to the 3D scene
        if parent:
            self.obj.reparentTo(parent)
        else:
            self.obj.reparentTo(render) # type: ignore

        # Apply a basic material for improved shading depth
        mat = Material()
        mat.setShininess(30.0)
        mat.setSpecular((0.6, 0.6, 0.6, 1))
        self.obj.setMaterial(mat, 1)
        self.obj.setColor(color)
        self.obj.setShaderAuto()

        # Position at the correct square
        self.obj.setPos(SquarePos(square))

    def get_pseudo_legal_moves(self, board, current_square, state=None):
        """
        Returns a list of squares (0-63) this piece can logically reach, 
        ignoring whether it puts the king in check.
        `state` is a dictionary containing extra game state like en_passant_square.
        """
        return []


# Define piece subclasses with their model files
class Pawn(Piece):
    model = "models/pawn"

    def get_pseudo_legal_moves(self, board, current_square, state=None):
        moves = []
        direction = 1 if self.color == WHITE else -1
        start_row = 1 if self.color == WHITE else 6
        x, y = current_square % 8, current_square // 8
        
        # Forward 1
        if 0 <= y + direction < 8:
            sq = (y + direction) * 8 + x
            if board[sq] is None:
                moves.append(sq)
                # Forward 2
                if y == start_row:
                    sq2 = (y + 2 * direction) * 8 + x
                    if board[sq2] is None:
                        moves.append(sq2)
                        
        # Captures
        for dx in [-1, 1]:
            if 0 <= x + dx < 8 and 0 <= y + direction < 8:
                sq = (y + direction) * 8 + (x + dx)
                target = board[sq]
                if target is not None and target.color != self.color:
                    moves.append(sq)
                # En passant
                elif state and state.get('en_passant_square') == sq:
                    moves.append(sq)
        return moves

class King(Piece):
    model = "models/king"

    def get_pseudo_legal_moves(self, board, current_square, state=None):
        moves = []
        x, y = current_square % 8, current_square // 8
        directions = [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8:
                sq = ny * 8 + nx
                target = board[sq]
                if target is None or target.color != self.color:
                    moves.append(sq)
        
        # Castling
        if state:
            if self.color == WHITE and not state.get('white_king_moved'):
                # Kingside
                if not state.get('white_rook_moved', [False, False])[1]:
                    if board[current_square + 1] is None and board[current_square + 2] is None:
                        moves.append(current_square + 2)
                # Queenside
                if not state.get('white_rook_moved', [False, False])[0]:
                    if board[current_square - 1] is None and board[current_square - 2] is None and board[current_square - 3] is None:
                        moves.append(current_square - 2)
            elif self.color == PIECEBLACK and not state.get('black_king_moved'):
                # Kingside
                if not state.get('black_rook_moved', [False, False])[1]:
                    if board[current_square + 1] is None and board[current_square + 2] is None:
                        moves.append(current_square + 2)
                # Queenside
                if not state.get('black_rook_moved', [False, False])[0]:
                    if board[current_square - 1] is None and board[current_square - 2] is None and board[current_square - 3] is None:
                        moves.append(current_square - 2)
                        
        return moves

class Knight(Piece):
    model = "models/knight"

    def get_pseudo_legal_moves(self, board, current_square, state=None):
        moves = []
        x, y = current_square % 8, current_square // 8
        knight_jumps = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
        for dx, dy in knight_jumps:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8:
                sq = ny * 8 + nx
                target = board[sq]
                if target is None or target.color != self.color:
                    moves.append(sq)
        return moves

class SlidingPiece(Piece):
    def _get_sliding_moves(self, board, current_square, directions):
        moves = []
        for dx, dy in directions:
            x, y = current_square % 8, current_square // 8
            while True:
                x += dx
                y += dy
                if not (0 <= x < 8 and 0 <= y < 8):
                    break
                sq = y * 8 + x
                target = board[sq]
                if target is None:
                    moves.append(sq)
                elif target.color != self.color:
                    moves.append(sq)
                    break
                else:
                    break
        return moves

class Bishop(SlidingPiece):
    model = "models/bishop"
    def get_pseudo_legal_moves(self, board, current_square, state=None):
        return self._get_sliding_moves(board, current_square, [(1,1), (1,-1), (-1,1), (-1,-1)])

class Rook(SlidingPiece):
    model = "models/rook"
    def get_pseudo_legal_moves(self, board, current_square, state=None):
        return self._get_sliding_moves(board, current_square, [(1,0), (-1,0), (0,1), (0,-1)])

class Queen(SlidingPiece):
    model = "models/queen"
    def get_pseudo_legal_moves(self, board, current_square, state=None):
        return self._get_sliding_moves(board, current_square, [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)])