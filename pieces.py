from panda3d.core import Material
from constants import SquarePos


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


# Define piece subclasses with their model files
class Pawn(Piece):
    model = "models/pawn"

class King(Piece):
    model = "models/king"

class Queen(Piece):
    model = "models/queen"

class Bishop(Piece):
    model = "models/bishop"

class Knight(Piece):
    model = "models/knight"

class Rook(Piece):
    model = "models/rook"