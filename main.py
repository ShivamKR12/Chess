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
from panda3d.core import (
    LPoint3, LVector3, BitMask32, CollisionNode, CollisionRay,
    CollisionHandlerQueue, WindowProperties, AmbientLight, DirectionalLight,
    CollisionTraverser, TextNode
)

# Import interval functions for creating animations.
# Includes functions like Sequence, Parallel for combining animations.
from direct.interval.IntervalGlobal import LerpHprInterval

# Import OnscreenText for displaying text overlays on the screen.
# Used to show game information like whose turn it is.
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton

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


class AppState:
    """
    Base class for all application states (Menu, Game, etc.).
    
    Provides common functionality for state management and cleanup.
    """
    
    def __init__(self, app):
        """
        Initialize the state with a reference to the main application.
        
        Parameters:
        - app: Reference to the main ChessApp instance
        """
        self.app = app
    
    def cleanup(self):
        """
        Clean up this state's resources and UI elements.
        Should be overridden by subclasses.
        """
        pass


class MenuState(AppState):
    """
    Main menu state that displays game options and settings.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.selectedColor = 0  # 0 = White, 1 = Black
        self.setupMenu()
    
    def setupMenu(self):
        """Create the main menu UI elements."""
        # Create menu background frame
        self.menuFrame = DirectFrame(
            frameColor=(0.2, 0.4, 0.6, 0.9),  # Semi-transparent blue background
            frameSize=(-0.8, 0.8, -0.6, 0.6),  # Centered, reasonably sized
            pos=(0, 0, 0),
            relief='groove',
            borderWidth=(0.02, 0.02)
        )
        
        # Add menu title
        self.titleLabel = DirectLabel(
            parent=self.menuFrame,
            text="Chess Game",
            text_scale=0.12,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.02, -0.02),
            pos=(0, 0, 0.4)
        )
        
        # Add game mode buttons
        self.pvpButton = DirectButton(
            parent=self.menuFrame,
            text="Player vs Player",
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.3, 0.3, -0.05, 0.05),
            pos=(0, 0, 0.2),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.startPvP
        )
        
        self.pvaiButton = DirectButton(
            parent=self.menuFrame,
            text="Player vs AI",
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.3, 0.3, -0.05, 0.05),
            pos=(0, 0, 0.1),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.startPvAI
        )
        
        # Add color selection buttons
        self.whiteButton = DirectButton(
            parent=self.menuFrame,
            text="Play as White",
            text_scale=0.05,
            text_fg=(0, 0, 0, 1),
            frameColor=(0.9, 0.9, 0.9, 1) if self.selectedColor == 0 else (0.7, 0.7, 0.7, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(-0.3, 0, -0.1),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.selectColor, extraArgs=[0]
        )
        
        self.blackButton = DirectButton(
            parent=self.menuFrame,
            text="Play as Black",
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.2, 1) if self.selectedColor == 1 else (0.4, 0.4, 0.4, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(0.3, 0, -0.1),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.selectColor, extraArgs=[1]
        )
        
        # Add settings button
        self.settingsButton = DirectButton(
            parent=self.menuFrame,
            text="Settings",
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.5, 0.5, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(0, 0, -0.3),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.showSettings
        )
        
        # Add exit button
        self.exitButton = DirectButton(
            parent=self.menuFrame,
            text="Exit",
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0, 0, -0.45),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=sys.exit
        )
    
    def selectColor(self, color):
        """Update the selected color and button appearances."""
        self.selectedColor = color
        
        # Update button colors to show selection
        if color == 0:  # White selected
            self.whiteButton['frameColor'] = (0.9, 0.9, 0.9, 1)
            self.blackButton['frameColor'] = (0.4, 0.4, 0.4, 1)
        else:  # Black selected
            self.whiteButton['frameColor'] = (0.7, 0.7, 0.7, 1)
            self.blackButton['frameColor'] = (0.2, 0.2, 0.2, 1)
    
    def startPvP(self):
        """Start a Player vs Player game."""
        self.app.startGame(mode="pvp", playerColor=self.selectedColor)
    
    def startPvAI(self):
        """Start a Player vs AI game."""
        self.app.startGame(mode="pvai", playerColor=self.selectedColor, difficulty=1)
    
    def showSettings(self):
        """Show settings menu (placeholder for now)."""
        print("Settings menu not implemented yet")
    
    def cleanup(self):
        """Clean up menu UI elements."""
        if hasattr(self, 'menuFrame'):
            self.menuFrame.destroy()
        if hasattr(self, 'titleLabel'):
            self.titleLabel.destroy()
        if hasattr(self, 'pvpButton'):
            self.pvpButton.destroy()
        if hasattr(self, 'pvaiButton'):
            self.pvaiButton.destroy()
        if hasattr(self, 'whiteButton'):
            self.whiteButton.destroy()
        if hasattr(self, 'blackButton'):
            self.blackButton.destroy()
        if hasattr(self, 'settingsButton'):
            self.settingsButton.destroy()
        if hasattr(self, 'exitButton'):
            self.exitButton.destroy()


class ChessGame(AppState):
    """
    Chess game state that handles the actual gameplay.
    Renamed from Chess class for clarity.
    """
    
    def __init__(self, app, mode="pvp", playerColor=0, difficulty=1):
        super().__init__(app)
        self.mode = mode
        self.playerColor = playerColor
        self.difficulty = difficulty
        
        # Initialize the game
        self.initializeGame()
    
    def initializeGame(self):
        """Initialize the chess game (copied from original Chess.__init__)."""
        # Note: We don't call ShowBase.__init__ here since we're using the app's ShowBase instance
        
        # Create a WindowProperties object to configure window settings
        props = WindowProperties()
        # Set the window title to "Chess"
        props.setTitle("Chess")
        # Set the window icon filename
        props.setIconFilename("panda3d-logo.ico")
        # Apply the window properties to the window
        base.win.requestProperties(props) # type: ignore

        # Set a nicer light sky background color
        self.app.setBackgroundColor(0.53, 0.81, 0.92, 1)

        # Disable Panda3D's default mouse camera controls.
        self.app.disableMouse()

        # Create a pivot node for camera rotation during turn changes.
        self.camPivot = self.app.render.attachNewNode("camPivot") # type: ignore
        self.camPivot.setPos(0, 0, 0)

        # Position the camera above and behind the board, looking at the center.
        self.app.camera.reparentTo(self.camPivot) # type: ignore
        self.app.camera.setPos(0, -12, 8) # type: ignore
        self.app.camera.lookAt(0, 0, 0) # type: ignore

        # Start the game with the selected player's color
        self.turn = WHITE if self.playerColor == 0 else PIECEBLACK

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
            scale=0.06,       # Text size
            fg=(1, 1, 1, 1),  # White text color
            shadow=(0, 0, 0, 0.8),
            mayChange=1
        )
        self.turnText.hide()  # We're using statusLabel for consolidated status display

        # Load game sound effects
        self.captureSound = loader.loadSfx("sounds/capture.mp3") # type: ignore
        self.castleSound = loader.loadSfx("sounds/castle.mp3") # type: ignore
        self.moveCheckSound = loader.loadSfx("sounds/move-check.mp3") # type: ignore
        self.moveSelfSound = loader.loadSfx("sounds/move-self.mp3") # type: ignore
        self.notifySound = loader.loadSfx("sounds/notify.mp3") # type: ignore
        self.promoteSound = loader.loadSfx("sounds/promote.mp3") # type: ignore

        # Bind the escape key to return to menu
        self.app.accept('escape', self.returnToMenu)

        # Set up lighting for the 3D scene.
        self.setupLights()

        # Set up the skydome background
        self.setupSkydome()

        # Configure collision detection for mouse picking.
        self.setupPicking()

        # Create the chessboard squares and place initial pieces.
        self.setupBoard()

        # Build UI elements for status and controls.
        self.gameOver = False
        self.setupUI()

        self.hiSq = False  # Square currently under mouse (False if none)
        self.dragging = False  # Square of piece being dragged (False if none)

        # Add a task that runs every frame to handle mouse interaction.
        taskMgr.add(self.mouseTask, "mouseTask") # type: ignore

        # Bind left mouse button press to grab a piece.
        self.app.accept("mouse1", self.grabPiece)
        self.app.accept("r", self.onNewGame)

        # Bind left mouse button release to release/drop a piece.
        self.app.accept("mouse1-up", self.releasePiece)
    
    def returnToMenu(self):
        """Return to the main menu."""
        self.app.showMenu()
    
    def cleanup(self):
        """Clean up game resources."""
        # Remove all pieces
        if hasattr(self, 'pieces'):
            for p in self.pieces:
                if p and hasattr(p, 'obj'):
                    p.obj.removeNode()
        
        # Remove squares
        if hasattr(self, 'squareRoot'):
            self.squareRoot.removeNode()
        
        # Remove UI elements
        if hasattr(self, 'statusFrame'):
            self.statusFrame.destroy()
        if hasattr(self, 'statusLabel'):
            self.statusLabel.destroy()
        if hasattr(self, 'restartButton'):
            self.restartButton.destroy()
        if hasattr(self, 'menuButton'):
            self.menuButton.destroy()
        if hasattr(self, 'turnText'):
            self.turnText.destroy()
        
        # Stop tasks
        taskMgr.remove("mouseTask") # type: ignore
        
        # Clear event handlers
        self.app.ignoreAll()

    # Copy all the existing game methods from the original Chess class
    def setupBoard(self):
        """
        Set up the chessboard and initial piece positions.

        Creates 64 square models, colors them in checkerboard pattern,
        and places the starting chess pieces according to standard rules.
        """
        
        # Create a root node to hold all square models.
        self.squareRoot = render.attachNewNode("squareRoot") # type: ignore

        self.squares = [None] * 64  # List of square NodePaths
        self.pieces = [None] * 64   # List of Piece objects (or None)

        for i in range(64):
            # Create and position each square
            # Load the square model from disk.
            sq = loader.loadModel("models/square") # type: ignore

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
        self.pickerNP = camera.attachNewNode(self.pickerNode) # type: ignore

        # Set the ray to only collide with objects in mask bit 1 (squares).
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))

        # Create the collision ray.
        self.pickerRay = CollisionRay()

        # Add the ray to the collision node.
        self.pickerNode.addSolid(self.pickerRay)

        # Add the collider to the traverser with the queue handler.
        self.picker.addCollider(self.pickerNP, self.pq)

    def setupUI(self):
        """Create on-screen controls and status text using DirectGUI."""
        self.statusFrame = DirectFrame(
            frameColor=(0.75, 0.95, 0.75, 0.75),
            frameSize=(-0.75, 0.75, -0.09, 0.09),
            pos=(0, 0, 0.93),
            relief='groove',
            borderWidth=(0.01, 0.01)
        )
        self.statusLabel = DirectLabel(
            parent=self.statusFrame,
            text="Turn: WHITE",
            text_fg=(0.1, 0.2, 0.1, 1),
            text_scale=0.045,
            text_align=TextNode.ACenter,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.02, -0.02),
            text_wordwrap=20,
            textMayChange=1,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0)
        )
        self.restartButton = DirectButton(
            text="New Game",
            scale=0.04,
            pos=(1.1, 0, 0.92),
            command=self.onNewGame
        )
        
        # Add back to menu button
        self.menuButton = DirectButton(
            text="Menu",
            scale=0.04,
            pos=(1.1, 0, 0.85),
            command=self.returnToMenu
        )

    def setStatus(self, text):
        """Update the status text and keep the main turn text in sync."""
        if hasattr(self, 'statusLabel'):
            self.statusLabel['text'] = text
        if text.startswith("Turn:"):
            self.turnText.setText(text)

    def onNewGame(self):
        """Reset the board and gameplay state for a new game."""
        # Remove old pieces
        for p in self.pieces:
            if p and hasattr(p, 'obj'):
                p.obj.removeNode()

        self.squares = [None] * 64
        self.pieces = [None] * 64
        self.squareRoot.removeNode()

        # Reset camera/orientation to initial starting view
        self.camPivot.setHpr(0, 0, 0)
        camera.reparentTo(self.camPivot) # type: ignore
        camera.setPos(0, -12, 8) # type: ignore
        camera.lookAt(0, 0, 0) # type: ignore

        self.enPassantSquare = None
        self.whiteKingMoved = False
        self.blackKingMoved = False
        self.whiteRookMoved = [False, False]
        self.blackRookMoved = [False, False]
        self.validMoves = []
        self.gameOver = False
        self.turn = WHITE if self.playerColor == 0 else PIECEBLACK

        self.setupBoard()
        self.clearHighlights()
        self.setStatus("Turn: WHITE" if self.turn == WHITE else "Turn: BLACK")

    # Include all the other game methods (movePiece, isValidMove, etc.)
    # For brevity, I'll copy the key methods here
    
    def movePiece(self, fr, to):
        """
        Move a piece from one square to another, handling all game logic.
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
        self.lastMove = (fr, to)

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
        isPromotion = False
        if isinstance(piece, Pawn):
            row = to // 8  # Get the row (rank) of the destination
            if (piece.color == WHITE and row == 7) or (piece.color == PIECEBLACK and row == 0):
                # If pawn reached the opposite end of the board
                piece.obj.removeNode()  # Remove the pawn
                self.pieces[to] = Queen(to, piece.color)  # Replace with queen
                isPromotion = True

        # Play sound effect by move type
        isCapture = target is not None or (isinstance(moving, Pawn) and to == self.enPassantSquare)
        isCastle = isinstance(moving, King) and abs((to % 8) - (fr % 8)) == 2
        enemy = PIECEBLACK if moving.color == WHITE else WHITE
        inCheck = self.isKingInCheck(enemy)

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
        """
        # Find the king's position
        kingSquare = None
        for i, p in enumerate(self.pieces):
            if isinstance(p, King) and p.color == color:
                kingSquare = i
                break

        # If there is no king, treat as checkmated for that color (game over scenario)
        if kingSquare is None:
            self.checkedKingSquare = None
            return True

        self.checkedKingSquare = kingSquare

        # Check if any enemy piece can move to the king's square
        for i, p in enumerate(self.pieces):
            if p and p.color != color:
                # If enemy piece can move to king's square, king is in check
                if self.isValidMove(i, kingSquare):
                    return True

        self.checkedKingSquare = None
        return False

    def isCheckmate(self, color):
        """
        Check if the specified color is in checkmate.
        """
        if not self.isKingInCheck(color):
            return False  # Not in check, so not checkmate

        # Check if any piece of this color has a legal move
        for i, p in enumerate(self.pieces):
            if p and p.color == color:
                if self.getLegalMoves(i):
                    return False  # Has legal moves, not checkmate

        return True  # In check with no legal moves = checkmate

    def isStalemate(self, color):
        """Check if the specified color is in stalemate (no legal moves, not in check)."""
        if self.isKingInCheck(color):
            return False

        for i, p in enumerate(self.pieces):
            if p and p.color == color:
                if self.getLegalMoves(i):
                    return False

        return True

    def mouseTask(self, task):
        """
        Task that runs every frame to handle mouse interaction.
        """
        
        # Get mouse position in screen coordinates (-1 to 1)
        if self.app.mouseWatcherNode.hasMouse():
            mpos = self.app.mouseWatcherNode.getMouse()

            # Update the collision ray from camera through mouse position
            self.pickerRay.setFromLens(self.app.camNode, mpos.getX(), mpos.getY()) # type: ignore

            # If dragging a piece, update its position to follow mouse
            if self.dragging is not False:
                nearPoint = self.app.render.getRelativePoint(self.app.camera, self.pickerRay.getOrigin()) # type: ignore
                nearVec = self.app.render.getRelativeVector(self.app.camera, self.pickerRay.getDirection()) # type: ignore
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
        """
        if self.dragging is False or self.gameOver:
            self.dragging = False
            self.validMoves = []
            self.hiSq = False
            self.highlightMoves()
            return

        piece = self.pieces[self.dragging]

        # If dropped on a valid move square
        if self.hiSq is not False and self.hiSq in self.validMoves:
            # Prevent direct king capture (legal move logic should avoid this scenario in real chess).
            if isinstance(self.pieces[self.hiSq], King):
                self.setStatus("Illegal move: cannot capture king")
                piece.obj.setPos(SquarePos(self.dragging))
            else:
                self.movePiece(self.dragging, self.hiSq)

                enemy = PIECEBLACK if self.turn == WHITE else WHITE
                enemy_in_check = self.isKingInCheck(enemy)
                black_in_checkmate = self.isCheckmate(PIECEBLACK)
                white_in_checkmate = self.isCheckmate(WHITE)
                black_stalemate = self.isStalemate(PIECEBLACK)
                white_stalemate = self.isStalemate(WHITE)

            if black_in_checkmate or white_in_checkmate:
                self.gameOver = True
                winner = "WHITE" if black_in_checkmate else "BLACK"
                self.setStatus(f"CHECKMATE! {winner} wins")
            elif black_stalemate or white_stalemate:
                self.gameOver = True
                self.setStatus("STALEMATE. Draw")
            else:
                self.switchTurn()
                if enemy_in_check:
                    self.setStatus(f"Check to {'BLACK' if enemy == PIECEBLACK else 'WHITE'}")
                else:
                    self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")

        else:
            # Invalid drop - return piece to original position
            self.setStatus("Invalid move")
            piece.obj.setPos(SquarePos(self.dragging))

        self.dragging = False  # Stop dragging
        self.validMoves = []   # Clear valid moves
        self.hiSq = False      # Clear highlighted square
        self.highlightMoves()  # This will clear highlights since validMoves is empty

    def highlightMoves(self):
        """
        Highlight all valid move destinations for the current piece.
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

        # Highlight checked king square
        if hasattr(self, 'checkedKingSquare') and self.checkedKingSquare is not None:
            self.squares[self.checkedKingSquare].setColor((1, 0, 0, 1))

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
        """
        # Create ambient light (soft, even lighting from all directions)
        ambient = AmbientLight("ambient")
        ambient.setColor((.8, .8, .8, 1))

        # Create directional light (like sunlight from a specific direction)
        directional = DirectionalLight("dir")
        directional.setDirection(LVector3(0, 45, -45))
        directional.setColor((0.2, 0.2, 0.2, 1))

        # Add ambient light to the scene
        self.app.render.setLight(self.app.render.attachNewNode(ambient)) # type: ignore

        # Add directional light to the scene
        self.app.render.setLight(self.app.render.attachNewNode(directional)) # type: ignore

    def setupSkydome(self):
        """
        Set up the skydome background for the 3D scene.
        """
        # Load the skydome model
        self.skydome = loader.loadModel("models/skydome.glb") # type: ignore
        
        # Scale it up significantly (user mentioned default scale is only 1)
        self.skydome.setScale(50)  # Much larger scale for background
        
        # Position it at the center of the scene
        self.skydome.setPos(0, 0, 0)
        
        # Make sure it's behind everything else (negative Z or far away)
        self.skydome.setBin("background", 1)  # Render as background
        self.skydome.setDepthWrite(False)     # Don't write to depth buffer
        self.skydome.setDepthTest(False)      # Don't test depth
        
        # Reparent to render
        self.skydome.reparentTo(self.app.render) # type: ignore


class ChessApp(ShowBase):
    """
    Main application class that manages the overall game flow and state transitions.
    """
    
    def __init__(self):
        """
        Initialize the chess application.
        """
        ShowBase.__init__(self)
        
        # Set window properties
        props = WindowProperties()
        props.setTitle("Chess Game")
        props.setIconFilename("panda3d-logo.ico")
        base.win.requestProperties(props) # type: ignore
        
        # Set background color
        self.setBackgroundColor(0.53, 0.81, 0.92, 1)
        
        # Initialize state management
        self.currentState = None
        
        # Start with the menu
        self.showMenu()
    
    def showMenu(self):
        """
        Switch to the main menu state.
        """
        if self.currentState:
            self.currentState.cleanup()
        self.currentState = MenuState(self)
    
    def startGame(self, mode="pvp", playerColor=0, difficulty=1):
        """
        Start a new chess game.
        
        Parameters:
        - mode: Game mode ("pvp" or "pvai")
        - playerColor: Player's color (0 = white, 1 = black)
        - difficulty: AI difficulty level (1-5)
        """
        if self.currentState:
            self.currentState.cleanup()
        self.currentState = ChessGame(self, mode, playerColor, difficulty)


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
        self.obj = loader.loadModel(self.model) # type: ignore

        # Add to the 3D scene
        self.obj.reparentTo(render) # type: ignore

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


# Create and run the chess application
if __name__ == "__main__":
    app = ChessApp()
    app.run()
