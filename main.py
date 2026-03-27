# Import the ShowBase class from Panda3D.
# ShowBase is the main application class that sets up:
#     • the window
#     • the rendering engine
#     • the camera
#     • the scene graph
#     • input handling
# By inheriting from ShowBase, the program becomes a Panda3D app.
from direct.showbase.ShowBase import ShowBase

# Import all core Panda3D modules.
# This includes essential classes like NodePath, Vec3, CollisionRay, BitMask32, etc.
# Used for 3D graphics, collision detection, and scene management.
from panda3d.core import *

# Import interval functions for creating animations.
# Includes functions like Sequence, Parallel for combining animations.
from direct.interval.IntervalGlobal import *

# Import OnscreenText for displaying text overlays on the screen.
# Used to show game information like whose turn it is.
from direct.gui.OnscreenText import OnscreenText

# Import specific interval classes for smooth position and rotation animations.
# LerpPosInterval for moving objects, LerpPosHprInterval for moving and rotating.
from direct.interval.LerpInterval import LerpPosInterval, LerpPosHprInterval

# Import Task for managing game loops and periodic updates.
# Used for the mouse task that runs every frame.
from direct.task.Task import Task

# Import sys for system-level functions.
# Used here for exiting the program with sys.exit.
import sys

# Define color constants used throughout the chess game.
# Colors are defined as RGBA tuples (red, green, blue, alpha).
BLACK = (0, 0, 0, 1)  # Solid black for dark squares
WHITE = (1, 1, 1, 1)  # Solid white for light squares
HIGHLIGHT = (0, 1, 1, 1)  # Cyan color for highlighting squares
PIECEBLACK = (.15, .15, .15, 1)  # Dark gray for black chess pieces


def PointAtZ(z, point, vec):
    """
    Calculate the intersection point at a specific Z height along a vector.

    This function is used for 3D picking and placing objects at a certain height.
    It finds where a ray (defined by point and direction vector) intersects
    a horizontal plane at height z.

    Parameters:
    - z: The target Z coordinate (height)
    - point: Starting point of the ray (LPoint3)
    - vec: Direction vector of the ray (LVector3)

    Returns:
    - LPoint3: The intersection point at the specified Z height
    """
    return point + vec * ((z - point.getZ()) / vec.getZ())


def SquarePos(i):
    """
    Convert a square index (0-63) to its 3D world position on the chessboard.

    The chessboard is an 8x8 grid centered at (0,0,0) in world space.
    Each square is 1 unit wide, so positions range from -3.5 to 3.5 in X and Y.

    Parameters:
    - i: Square index from 0 (a1) to 63 (h8)

    Returns:
    - LPoint3: World position of the square's center
    """
    return LPoint3((i % 8) - 3.5, int(i // 8) - 3.5, 0)


def SquareColor(i):
    """
    Determine the color of a chess square based on its index.

    Creates the classic alternating black and white chessboard pattern.
    The pattern depends on both the file (column) and rank (row) to create
    the correct checkerboard effect.

    Parameters:
    - i: Square index from 0 to 63

    Returns:
    - Color tuple: BLACK or WHITE depending on the square's position
    """
    if (i + ((i // 8) % 2)) % 2:
        return BLACK
    return WHITE


class Chess(ShowBase):
    """
    Main Chess game class that inherits from Panda3D's ShowBase.

    This class manages the entire chess game including:
    - 3D board and piece rendering
    - Game logic (moves, rules, check/checkmate)
    - User input handling (mouse dragging)
    - Turn management
    - Visual feedback (highlights, animations)
    - Camera controls

    The game uses a 64-element array to represent the board state,
    with indices 0-63 corresponding to squares a1-h8.
    """

    def __init__(self):
        """
        Constructor for the Chess class.

        Initializes the Panda3D application, sets up the 3D scene,
        creates the chessboard, places pieces, and configures input handling.
        """

        # Call the parent ShowBase constructor to initialize Panda3D.
        ShowBase.__init__(self)

        # Create a WindowProperties object to configure window settings
        props = WindowProperties()
        # Set the window title to "Chess"
        props.setTitle("Chess")
        # Set the window icon filename
        props.setIconFilename("panda3d-logo.ico")
        # Apply the window properties to the window
        base.win.requestProperties(props)

        # Disable Panda3D's default mouse camera controls.
        self.disableMouse()

        # Create a pivot node for camera rotation during turn changes.
        self.camPivot = render.attachNewNode("camPivot")
        self.camPivot.setPos(0, 0, 0)

        # Position the camera above and behind the board, looking at the center.
        camera.reparentTo(self.camPivot)
        camera.setPos(0, -12, 8)
        camera.lookAt(0, 0, 0)

        # Start the game with white's turn.
        self.turn = WHITE

        # Track the square where en passant capture is possible (or None).
        self.enPassantSquare = None

        # Track if kings have moved (affects castling rights).
        self.whiteKingMoved = False
        self.blackKingMoved = False

        # Track if rooks have moved (affects castling rights).
        self.whiteRookMoved = [False, False]  # [queenside, kingside]
        self.blackRookMoved = [False, False]  # [queenside, kingside]

        # List of valid destination squares for the currently selected piece.
        self.validMoves = []

        # Create on-screen text to display whose turn it is.
        self.turnText = OnscreenText(
            text="Turn: WHITE",
            pos=(-1.3, 0.9),  # Position in screen coordinates (-1 to 1)
            scale=0.07,       # Text size
            fg=(1, 1, 1, 1)   # White text color
        )

        # Load sound effects for game actions
        self.captureSound = loader.loadSfx("sounds/capture.mp3")
        self.castleSound = loader.loadSfx("sounds/castle.mp3")
        self.moveCheckSound = loader.loadSfx("sounds/move-check.mp3")
        self.moveSelfSound = loader.loadSfx("sounds/move-self.mp3")
        self.notifySound = loader.loadSfx("sounds/notify.mp3")
        self.promoteSound = loader.loadSfx("sounds/promote.mp3")

        # Bind the escape key to exit the program.
        self.accept('escape', sys.exit)

        # Set up lighting for the 3D scene.
        self.setupLights()

        # Configure collision detection for mouse picking.
        self.setupPicking()

        # Create the chessboard squares and place initial pieces.
        self.setupBoard()

        self.hiSq = False  # Square currently under mouse (False if none)
        self.dragging = False  # Square of piece being dragged (False if none)

        # Add a task that runs every frame to handle mouse interaction.
        taskMgr.add(self.mouseTask, "mouseTask")

        # Bind left mouse button press to grab a piece.
        self.accept("mouse1", self.grabPiece)

        # Bind left mouse button release to release/drop a piece.
        self.accept("mouse1-up", self.releasePiece)

    def setupBoard(self):
        """
        Set up the chessboard and initial piece positions.

        Creates 64 square models, colors them in checkerboard pattern,
        and places the starting chess pieces according to standard rules.
        """
        
        # Create a root node to hold all square models.
        self.squareRoot = render.attachNewNode("squareRoot")

        self.squares = [None] * 64  # List of square NodePaths
        self.pieces = [None] * 64   # List of Piece objects (or None)

        for i in range(64):
            # Create and position each square
            # Load the square model from disk.
            sq = loader.loadModel("models/square")

            # Attach to the square root node.
            sq.reparentTo(self.squareRoot)

            # Position the square in 3D space.
            sq.setPos(SquarePos(i))

            # Color the square black or white.
            sq.setColor(SquareColor(i))

            # Enable collision detection on the square's geometry.
            sq.find("**/polygon").node().setIntoCollideMask(BitMask32.bit(1))

            # Tag the collision node with the square index for identification.
            sq.find("**/polygon").node().setTag('square', str(i))

            # Store reference to the square.
            self.squares[i] = sq

        # Define the back rank piece order for both sides
        pieceOrder = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)

        # Place white pawns on rank 2 (indices 8-15)
        for i in range(8, 16):
            self.pieces[i] = Pawn(i, WHITE)

        # Place black pawns on rank 7 (indices 48-55)
        for i in range(48, 56):
            self.pieces[i] = Pawn(i, PIECEBLACK)

        # Place white pieces on rank 1 (indices 0-7)
        for i in range(8):
            self.pieces[i] = pieceOrder[i](i, WHITE)

        # Place black pieces on rank 8 (indices 56-63)
        for i in range(8):
            self.pieces[i + 56] = pieceOrder[i](i + 56, PIECEBLACK)

    def setupPicking(self):
        """
        Set up collision detection for mouse picking.

        Creates a collision ray from the camera through the mouse position
        to detect which square the mouse is pointing at.
        """
        self.picker = CollisionTraverser()

        # Create a queue to store collision results.
        self.pq = CollisionHandlerQueue()

        # Create a collision node for the mouse ray.
        self.pickerNode = CollisionNode('mouseRay')

        # Attach the collision node to the camera.
        self.pickerNP = camera.attachNewNode(self.pickerNode)

        # Set the ray to only collide with objects in mask bit 1 (squares).
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))

        # Create the collision ray.
        self.pickerRay = CollisionRay()

        # Add the ray to the collision node.
        self.pickerNode.addSolid(self.pickerRay)

        # Add the collider to the traverser with the queue handler.
        self.picker.addCollider(self.pickerNP, self.pq)

    def movePiece(self, fr, to):
        """
        Move a piece from one square to another, handling all game logic.

        This includes capturing, en passant, castling, pawn promotion,
        and updating castling rights.

        Parameters:
        - fr: Source square index (0-63)
        - to: Destination square index (0-63)
        """
        moving = self.pieces[fr]  # The piece being moved
        target = self.pieces[to]  # Piece at destination (if any)

        if target:
            # If there's a piece at the destination, capture it
            # Animate the captured piece shrinking to nothing.
            target.obj.scaleInterval(1.2, 0).start()

            # Remove the captured piece from the scene.
            target.obj.removeNode()

        self.pieces[to] = moving  # Move piece to new square
        self.pieces[fr] = None    # Clear old square

        moving.square = to  # Update piece's square attribute

        # Move the piece directly to its new position.
        moving.obj.setPos(SquarePos(to))

        # Handle en passant capture
        if isinstance(moving, Pawn) and to == self.enPassantSquare:
            # If this is an en passant capture
            # Calculate the square of the captured pawn.
            captured = to - 8 if moving.color == WHITE else to + 8

            victim = self.pieces[captured]
            if victim:
                victim.obj.removeNode()  # Remove captured pawn
                self.pieces[captured] = None  # Clear the square

        # Set en passant square for next move
        if isinstance(moving, Pawn) and abs((to // 8) - (fr // 8)) == 2:
            # If pawn moved two squares forward
            # Set en passant target square.
            self.enPassantSquare = fr + (8 if moving.color == WHITE else -8)
        else:
            self.enPassantSquare = None  # Clear en passant opportunity

        # Handle castling
        if isinstance(moving, King) and abs((to % 8) - (fr % 8)) == 2:
            # If this is a castling move (king moves 2 squares horizontally)
            if to > fr:
                # Kingside castling
                rookFrom = fr + 3  # Rook's current square
                rookTo = fr + 1    # Rook's destination square
            else:
                # Queenside castling
                rookFrom = fr - 4
                rookTo = fr - 1

            # Move the rook to its castling position (no animation for simplicity)
            rook = self.pieces[rookFrom]
            self.pieces[rookFrom] = None
            self.pieces[rookTo] = rook
            rook.obj.setPos(SquarePos(rookTo))

        # Update castling rights when king moves
        if isinstance(moving, King):
            if moving.color == WHITE:
                self.whiteKingMoved = True
            else:
                self.blackKingMoved = True

        # Update castling rights when rook moves
        if isinstance(moving, Rook):
            if fr == 0: self.whiteRookMoved[0] = True  # Queenside rook
            if fr == 7: self.whiteRookMoved[1] = True  # Kingside rook
            if fr == 56: self.blackRookMoved[0] = True
            if fr == 63: self.blackRookMoved[1] = True

        # Handle pawn promotion
        piece = self.pieces[to]  # The piece that just moved
        if isinstance(piece, Pawn):
            row = to // 8  # Get the row (rank) of the destination
            if (piece.color == WHITE and row == 7) or (piece.color == PIECEBLACK and row == 0):
                # If pawn reached the opposite end of the board
                piece.obj.removeNode()  # Remove the pawn
                self.pieces[to] = Queen(to, piece.color)  # Replace with queen

        # Determine move type for sound effects
        isCapture = target is not None or (isinstance(moving, Pawn) and to == self.enPassantSquare)
        isCastle = isinstance(moving, King) and abs((to % 8) - (fr % 8)) == 2
        isPromotion = isinstance(moving, Pawn) and ((moving.color == WHITE and to // 8 == 7) or (moving.color == PIECEBLACK and to // 8 == 0))

        # Check if move puts opponent in check
        enemy = PIECEBLACK if moving.color == WHITE else WHITE
        inCheck = self.isKingInCheck(enemy)

        # Play appropriate sound effect
        if isPromotion:
            self.promoteSound.play()
        elif isCastle:
            self.castleSound.play()
        elif isCapture:
            self.captureSound.play()
        elif inCheck:
            self.moveCheckSound.play()
        else:
            self.moveSelfSound.play()

    def isPathClear(self, fr, to):
        """
        Check if the path between two squares is clear of pieces.

        Used for sliding pieces (rook, bishop, queen) to ensure no pieces
        block their movement along the path.

        Parameters:
        - fr: Starting square index
        - to: Ending square index

        Returns:
        - bool: True if path is clear, False if blocked
        """
        dx = (to % 8) - (fr % 8)  # Horizontal distance
        dy = (to // 8) - (fr // 8)  # Vertical distance

        stepX = 0 if dx == 0 else int(dx / abs(dx))  # Step direction in X
        stepY = 0 if dy == 0 else int(dy / abs(dy))  # Step direction in Y

        x = fr % 8 + stepX  # Start checking from next square
        y = fr // 8 + stepY

        while (x, y) != (to % 8, to // 8):
            # Check each square along the path
            if self.pieces[y * 8 + x]:
                # If there's a piece on this square, path is blocked
                return False
            x += stepX
            y += stepY

        # Path is clear
        return True

    def isValidMove(self, fr, to):
        """
        Check if a move from one square to another is valid according to chess rules.

        This checks piece-specific movement rules but does NOT check if the move
        would leave the king in check.

        Parameters:
        - fr: Source square
        - to: Destination square

        Returns:
        - bool: True if the move is valid, False otherwise
        """
        if fr == to:
            # Can't move to the same square
            return False

        piece = self.pieces[fr]
        target = self.pieces[to]

        if target and target.color == piece.color:
            # Can't capture own pieces
            return False

        dx = (to % 8) - (fr % 8)  # Horizontal distance
        dy = (to // 8) - (fr // 8)  # Vertical distance

        # Pawn movement rules
        if isinstance(piece, Pawn):
            direction = 1 if piece.color == WHITE else -1  # Forward direction
            startRow = 1 if piece.color == WHITE else 6    # Starting row

            # Single square forward
            if dx == 0 and dy == direction and target is None:
                return True

            # Double square forward from starting position
            if dx == 0 and dy == 2 * direction and fr // 8 == startRow:
                if target is None and self.isPathClear(fr, to):
                    return True

            # Diagonal capture
            if abs(dx) == 1 and dy == direction and target:
                return True

            # En passant capture
            if abs(dx) == 1 and dy == direction and to == self.enPassantSquare:
                return True

            return False

        # Knight movement (L-shape)
        if isinstance(piece, Knight):
            return (abs(dx), abs(dy)) in [(1, 2), (2, 1)]

        # King movement
        if isinstance(piece, King):
            # Normal king move (one square in any direction)
            if abs(dx) <= 1 and abs(dy) <= 1:
                return True

            # Castling
            if dy == 0 and abs(dx) == 2:
                if piece.color == WHITE and not self.whiteKingMoved:
                    if dx == 2 and not self.whiteRookMoved[1]:  # Kingside
                        return self.isPathClear(fr, fr + 3)  # Check path to rook
                    if dx == -2 and not self.whiteRookMoved[0]:  # Queenside
                        return self.isPathClear(fr, fr - 4)
                if piece.color == PIECEBLACK and not self.blackKingMoved:
                    if dx == 2 and not self.blackRookMoved[1]:
                        return self.isPathClear(fr, fr + 3)
                    if dx == -2 and not self.blackRookMoved[0]:
                        return self.isPathClear(fr, fr - 4)

        # Rook movement (horizontal/vertical)
        if isinstance(piece, Rook):
            if dx == 0 or dy == 0:  # Same file or rank
                return self.isPathClear(fr, to)

        # Bishop movement (diagonal)
        if isinstance(piece, Bishop):
            if abs(dx) == abs(dy):  # Equal diagonal distance
                return self.isPathClear(fr, to)

        # Queen movement (rook + bishop)
        if isinstance(piece, Queen):
            if dx == 0 or dy == 0 or abs(dx) == abs(dy):
                return self.isPathClear(fr, to)

        return False  # Invalid move for this piece

    def getLegalMoves(self, square):
        """
        Get all legal moves for a piece, considering check.

        This method simulates each possible move and checks if it would
        leave the king in check. Only moves that don't leave the king
        in check are considered legal.

        Parameters:
        - square: Square index of the piece

        Returns:
        - list: List of legal destination squares
        """
        piece = self.pieces[square]
        moves = []

        for i in range(64):
            # Check each possible destination
            if self.isValidMove(square, i):
                # Simulate the move
                captured = self.pieces[i]
                self.pieces[i] = piece
                self.pieces[square] = None

                # Check if this move would leave own king in check
                kingCheck = self.isKingInCheck(piece.color)

                # Revert the simulation
                self.pieces[square] = piece
                self.pieces[i] = captured

                # Move is legal if it doesn't leave king in check
                if not kingCheck:
                    moves.append(i)

        return moves

    def isKingInCheck(self, color):
        """
        Check if the king of the specified color is in check.

        This checks if any enemy piece can attack the king.

        Parameters:
        - color: Color of the king to check

        Returns:
        - bool: True if king is in check, False otherwise
        """

        # Find the king's position
        kingSquare = None
        for i, p in enumerate(self.pieces):
            if isinstance(p, King) and p.color == color:
                kingSquare = i
                break

        # Check if any enemy piece can move to the king's square
        for i, p in enumerate(self.pieces):
            if p and p.color != color:
                # If enemy piece can move to king's square, king is in check
                if self.isValidMove(i, kingSquare):
                    return True

        return False

    def isCheckmate(self, color):
        """
        Check if the specified color is in checkmate.

        Checkmate occurs when the king is in check and there are no legal
        moves to get out of check.

        Parameters:
        - color: Color to check for checkmate

        Returns:
        - bool: True if checkmate, False otherwise
        """
        if not self.isKingInCheck(color):
            return False  # Not in check, so not checkmate

        # Check if any piece of this color has a legal move
        for i, p in enumerate(self.pieces):
            if p and p.color == color:
                if self.getLegalMoves(i):
                    return False  # Has legal moves, not checkmate

        return True  # In check with no legal moves = checkmate

    def mouseTask(self, task):
        """
        Task that runs every frame to handle mouse interaction.

        Updates the mouse ray, performs collision detection, and highlights
        the square under the mouse.

        Parameters:
        - task: The task object

        Returns:
        - Task.cont: Continue the task
        """
        
        # Get mouse position in screen coordinates (-1 to 1)
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()

            # Update the collision ray from camera through mouse position
            self.pickerRay.setFromLens(self.camNode, mpos.getX(), mpos.getY())

            # If dragging a piece, update its position to follow mouse
            if self.dragging is not False:
                nearPoint = render.getRelativePoint(camera, self.pickerRay.getOrigin())
                nearVec = render.getRelativeVector(camera, self.pickerRay.getDirection())
                # Position piece at Z=0.5 along the mouse ray
                self.pieces[self.dragging].obj.setPos(
                    PointAtZ(.5, nearPoint, nearVec)
                )

            # Perform collision detection on the squares
            self.picker.traverse(self.squareRoot)

            # If collision detected, get the closest one
            if self.pq.getNumEntries() > 0:
                self.pq.sortEntries()
                i = int(self.pq.getEntry(0).getIntoNode().getTag('square'))
                self.hiSq = i  # Square under mouse
            else:
                self.hiSq = False

        # If not dragging and mouse over a square, highlight it
        if self.dragging is False and self.hiSq is not False:
            self.clearHighlights()
            self.squares[self.hiSq].setColor(HIGHLIGHT)

        return Task.cont  # Continue the task

    def grabPiece(self):
        """
        Handle mouse button press - attempt to grab a piece.

        If there's a piece under the mouse that belongs to the current player,
        start dragging it and show its valid moves.
        """
        
        # If mouse is over a square with a piece
        if self.hiSq is not False and self.pieces[self.hiSq]:
            piece = self.pieces[self.hiSq]

            # If it's the current player's piece
            if piece.color == self.turn:
                self.clearHighlights()

                self.dragging = self.hiSq  # Start dragging this piece
                self.validMoves = self.getLegalMoves(self.hiSq)

                # Highlight the selected square in yellow
                self.squares[self.dragging].setColor((1, 1, 0, 1))

                self.highlightMoves()  # Show valid move destinations

    def releasePiece(self):
        """
        Handle mouse button release - attempt to drop the piece.

        If the piece is dropped on a valid square, make the move.
        Otherwise, return it to its original position.
        """
        if self.dragging is not False:
            piece = self.pieces[self.dragging]

            # If dropped on a valid move square
            if self.hiSq is not False and self.hiSq in self.validMoves:
                self.movePiece(self.dragging, self.hiSq)

                enemy = PIECEBLACK if self.turn == WHITE else WHITE
                
                # If the move puts enemy in checkmate
                if self.isCheckmate(enemy):
                    self.turnText.setText("CHECKMATE!")
                    self.notifySound.play()

                self.switchTurn()  # Switch to other player's turn

            else:
                # Invalid drop - return piece to original position
                piece.obj.setPos(SquarePos(self.dragging))

        self.dragging = False  # Stop dragging
        self.validMoves = []   # Clear valid moves
        self.hiSq = False      # Clear highlighted square
        self.highlightMoves()  # This will clear highlights since validMoves is empty

    def highlightMoves(self):
        """
        Highlight all valid move destinations for the current piece.

        Uses different colors: red for captures, green for regular moves.
        """
        for m in self.validMoves:
            piece = self.pieces[self.dragging]

            # Square has enemy piece - red for capture
            if self.pieces[m]:
                self.squares[m].setColor((1, 0, 0, 1))
            
            # Special case: en passant capture
            elif isinstance(piece, Pawn) and m == self.enPassantSquare:
                self.squares[m].setColor((1, 0, 0, 1))
            
            # Empty square - green for move
            else:
                self.squares[m].setColor((0, 1, 0, 1))

    def clearHighlights(self):
        """
        Reset all squares to their normal colors (no highlights).
        """
        for i in range(64):
            self.squares[i].setColor(SquareColor(i))

    def switchTurn(self):
        """
        Switch to the other player's turn and rotate the camera.
        """
        if self.turn == WHITE:
            self.turn = PIECEBLACK
            self.turnText.setText("Turn: BLACK")
        else:
            self.turn = WHITE
            self.turnText.setText("Turn: WHITE")

        self.rotateCamera()  # Rotate camera to show board from other side

    def rotateCamera(self):
        """
        Animate the camera rotating 180 degrees around the board.

        This gives the impression of switching sides between players.
        """
        startH = self.camPivot.getH()  # Current heading
        endH = startH - 180            # Rotate 180 degrees (clockwise)

        orbit = LerpHprInterval(
            self.camPivot,  # Node to rotate
            1.2,            # Duration in seconds
            (endH, 0, 0),   # Target HPR (heading, pitch, roll)
            blendType="easeInOut"  # Smooth easing
        )
        orbit.start()  # Start the animation

    def setupLights(self):
        """
        Set up basic lighting for the 3D scene.

        Uses ambient light for overall illumination and directional light
        for shadows and depth.
        """
        # Create ambient light (soft, even lighting from all directions)
        ambient = AmbientLight("ambient")
        ambient.setColor((.8, .8, .8, 1))

        # Create directional light (like sunlight from a specific direction)
        directional = DirectionalLight("dir")
        directional.setDirection(LVector3(0, 45, -45))
        directional.setColor((0.2, 0.2, 0.2, 1))

        # Add ambient light to the scene
        render.setLight(render.attachNewNode(ambient))

        # Add directional light to the scene
        render.setLight(render.attachNewNode(directional))


class Piece:
    """
    Base class for all chess pieces.

    Each piece has a square position, color, and 3D model.
    Subclasses define the specific model file to load.
    """

    def __init__(self, square, color):
        """
        Constructor for Piece.

        Parameters:
        - square: Initial square index (0-63)
        - color: Piece color (WHITE or PIECEBLACK)
        """
        self.square = square  # Current square
        self.color = color    # Piece color

        # Load the 3D model for this piece type
        self.obj = loader.loadModel(self.model)

        # Add to the 3D scene
        self.obj.reparentTo(render)

        # Color the piece
        self.obj.setColor(color)

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


# Create and run the chess game

# Instantiate the Chess class (starts Panda3D and sets up the game)
demo = Chess()

# Start the Panda3D main loop (handles rendering, input, and updates)
demo.run()
