from panda3d.core import (
    BitMask32, CollisionNode, CollisionRay, CollisionHandlerQueue, 
    Material, CollisionTraverser, TextNode, LVector3, AmbientLight, 
    DirectionalLight
)
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectDialog
from direct.gui.OnscreenText import OnscreenText
from direct.interval.LerpInterval import LerpHprInterval, LerpPosInterval
from direct.task.Task import Task
from tkinter import Tk, filedialog
from datetime import datetime
import json
import os
import sys
import random

from states.base_state import AppState
from constants import BLACK, WHITE, PIECEBLACK, SquarePos, SquareColor, YELLOW, HIGHLIGHT, PointAtZ
from pieces import Pawn, Rook, Knight, Bishop, Queen, King
from ai import get_best_move


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
        """Initialize the chess game state, including board setup and camera configuration."""
        # Create a pivot node for camera rotation during turn changes.
        self.camPivot = self.app.render.attachNewNode("camPivot")
        self.camPivot.setPos(0, 0, 0)

        # Create a node to hold all pieces for easy cleanup
        self.piecesNode = self.app.render.attachNewNode("piecesNode")

        # Position the camera above and behind the board, looking at the center.
        self.app.camera.reparentTo(self.camPivot)
        self.app.camera.setPos(0, -14, 10)
        self.app.camera.lookAt(0, 0, 0)

        # Set initial camera rotation based on player color
        # If playing as black, rotate camera 180 degrees to face black side
        if self.playerColor == 1:  # Playing as black
            self.camPivot.setH(180)  # Face black side initially

        # White always moves first in chess
        self.turn = WHITE

        # Control rotation behavior: disable for PvAI to keep player view fixed
        self.rotateCameraEnabled = (self.mode != 'pvai')

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

        # Move history for undo functionality
        self.moveHistory = []
        
        # Move notation for display
        self.moveNotation = []

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
        self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")

        self.sfx_volume = self.app.settings_mgr.get('sfx_volume', 1.0)
        
        # Load game sound effects
        self.captureSound = self.app.loader.loadSfx("sounds/capture.mp3")
        self.captureSound.setVolume(self.sfx_volume)
        self.castleSound = self.app.loader.loadSfx("sounds/castle.mp3")
        self.castleSound.setVolume(self.sfx_volume)
        self.moveCheckSound = self.app.loader.loadSfx("sounds/move-check.mp3")
        self.moveCheckSound.setVolume(self.sfx_volume)
        self.moveSelfSound = self.app.loader.loadSfx("sounds/move-self.mp3")
        self.moveSelfSound.setVolume(self.sfx_volume)
        self.notifySound = self.app.loader.loadSfx("sounds/notify.mp3")
        self.notifySound.setVolume(self.sfx_volume)
        self.promoteSound = self.app.loader.loadSfx("sounds/promote.mp3")
        self.promoteSound.setVolume(self.sfx_volume)

        # Bind the escape key to prompt quit dialog
        self.accept('escape', self.showQuitDialog)
        
        # Listen for aspect ratio changes to update UI scaling dynamically
        self.accept('aspectRatioChanged', self.updateCameraForAspect)

        # Set up lighting for the 3D scene.
        self.setupLights()

        # Configure collision detection for mouse picking.
        self.setupPicking()

        # Create the chessboard squares and place initial pieces.
        self.setupBoard()

        # Build UI elements for status and controls.
        self.gameOver = False
        self.setupUI()

        self.hiSq = False  # Square currently under mouse (False if none)
        self.dragging = False  # Square of piece being dragged (False if none)
        self.selectedSquare = None  # Square of clicked piece (for click-to-move)

        # Add a task that runs every frame to handle mouse interaction.
        self.app.taskMgr.add(self.mouseTask, "mouseTask")

        # Bind left mouse button press to grab a piece.
        self.accept("mouse1", self.grabPiece)
        self.accept("r", self.onNewGame)

        # Bind left mouse button release to release/drop a piece.
        self.accept("mouse1-up", self.releasePiece)

        # If Player vs AI mode and AI starts, schedule the first AI move
        if self.mode == 'pvai' and ((self.playerColor == 0 and self.turn == PIECEBLACK) or (self.playerColor == 1 and self.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

        # Safely restrict the main window's DisplayRegion (avoiding CommonFilters off-screen buffer conflicts)
        self.dr = self.app.main_3d_dr
        self.dr.setDimensions(0, 1, 0, 0.85)  # Restrict 3D to the bottom 85% of screen
        # Force UI elements to scale to the correct window aspect ratio immediately
        self.updateCameraForAspect()

    def returnToMenu(self):
        """Return to the main menu."""
        self.app.showMenu()
    
    def cleanup(self):
        """Clean up game resources."""
        # Remove all pieces
        if hasattr(self, 'piecesNode'):
            self.piecesNode.removeNode()
        
        # Remove squares
        if hasattr(self, 'squareRoot'):
            self.squareRoot.removeNode()
        
        # Remove UI elements
        if hasattr(self, 'statusLabel'):
            self.statusLabel.destroy()
        if hasattr(self, 'restartButton'):
            self.restartButton.destroy()
        if hasattr(self, 'resignButton'):
            self.resignButton.destroy()
        if hasattr(self, 'undoButton'):
            self.undoButton.destroy()
        if hasattr(self, 'saveButton'):
            self.saveButton.destroy()
        if hasattr(self, 'quitButton'):
            self.quitButton.destroy()
        if hasattr(self, 'statusFrame'):
            self.statusFrame.destroy()

        if hasattr(self, 'quitDialog'):
            self.quitDialog.cleanup()
            del self.quitDialog
        if hasattr(self, 'moveHistoryLabel'):
            self.moveHistoryLabel.destroy()
        if hasattr(self, 'historyToggleButton'):
            self.historyToggleButton.destroy()
        if hasattr(self, 'moveHistoryFrame'):
            self.moveHistoryFrame.destroy()

        if hasattr(self, 'turnText'):
            self.turnText.destroy()
        if hasattr(self, 'resignDialog'):
            self.resignDialog.cleanup()
            del self.resignDialog
        if hasattr(self, 'promotionDialog'):
            self.promotionDialog.cleanup()
            del self.promotionDialog
        if hasattr(self, 'drawerInterval') and self.drawerInterval.isPlaying():
            self.drawerInterval.pause()
            del self.drawerInterval
        
        # Reset camera to world coordinates and remove pivot
        if hasattr(self, 'camPivot'):
            self.app.camera.reparentTo(self.app.render)
            self.camPivot.removeNode()
            
        # Restore full window DisplayRegion for menus
        if hasattr(self, 'dr'):
            self.dr.setDimensions(0, 1, 0, 1)
        
        # Stop tasks
        self.app.taskMgr.remove("mouseTask")
        
        # Remove lights
        for light_attr in ['ambientLightNode', 'mainDirectionalLightNode', 'fillDirectionalLightNode', 'backDirectionalLightNode', 'directionalLightNode']:
            if hasattr(self, light_attr):
                node = getattr(self, light_attr)
                self.app.render.clearLight(node)
                node.removeNode()

        # Call base class cleanup to clear event handlers
        super().cleanup()

    def getSquareColor(self, i):
        """Return the correct RGB color for a square based on the current theme."""
        theme = self.app.settings_mgr.get('board_theme', 'classic')
        is_dark = (i + ((i // 8) % 2)) % 2 != 0
        if theme == 'wood':
            return (0.34, 0.2, 0.09, 1) if is_dark else (0.82, 0.7, 0.53, 1)
        elif theme == 'marble':
            return (0.25, 0.35, 0.35, 1) if is_dark else (0.85, 0.85, 0.9, 1)
        elif theme == 'dark':
            return (0.15, 0.15, 0.18, 1) if is_dark else (0.45, 0.45, 0.5, 1)
        return SquareColor(i)

    # Copy all the existing game methods from the original Chess class
    def setupBoard(self):
        """
        Set up the chessboard and initial piece positions.

        Creates 64 square models, colors them in checkerboard pattern,
        and places the starting chess pieces according to standard rules.
        """
        
        # Create a root node to hold all square models.
        self.squareRoot = self.app.render.attachNewNode("squareRoot")
        
        # Create a root node to hold all piece models for easy cleanup.
        self.piecesNode = self.app.render.attachNewNode("piecesNode")

        self.squares = [None] * 64  # List of square NodePaths
        self.pieces = [None] * 64   # List of Piece objects (or None)

        for i in range(64):
            # Create and position each square
            # Load the square model from disk.
            sq = self.app.loader.loadModel("models/square")

            # Attach to the square root node.
            sq.reparentTo(self.squareRoot)

            # Position the square in 3D space.
            sq.setPos(SquarePos(i))

            # Color the square based on the user's active theme.
            sq.setColor(self.getSquareColor(i))

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
            self.pieces[i] = Pawn(i, WHITE, parent=self.piecesNode)

        # Place black pawns on rank 7 (indices 48-55)
        for i in range(48, 56):
            self.pieces[i] = Pawn(i, PIECEBLACK, parent=self.piecesNode)

        # Place white pieces on rank 1 (indices 0-7)
        for i in range(8):
            self.pieces[i] = pieceOrder[i](i, WHITE, parent=self.piecesNode)

        # Place black pieces on rank 8 (indices 56-63)
        for i in range(8):
            self.pieces[i + 56] = pieceOrder[i](i + 56, PIECEBLACK, parent=self.piecesNode)

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
        self.pickerNP = self.app.camera.attachNewNode(self.pickerNode)

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
        # Create a larger frame to hold status and buttons
        self.statusFrame = DirectFrame(
            frameColor=(0.2, 0.4, 0.6, 0.9),
            frameSize=(-1.335, 1.335, -0.15, 0.15),
            pos=(0, 0, 0.85),
            relief='groove',
            borderWidth=(0.02, 0.02)
        )
        
        # Status text in the center-top
        self.statusLabel = DirectLabel(
            parent=self.statusFrame,
            text="Turn: WHITE",
            text_fg=(1, 1, 1, 1),
            text_scale=0.06,
            text_align=TextNode.ACenter,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.02, -0.02),
            text_wordwrap=25,
            textMayChange=1,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.05)
        )
        
        # New Game button on the left
        self.restartButton = DirectButton(
            parent=self.statusFrame,
            text="New Game",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(-1.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.onNewGame
        )
        
        # Resign button in the middle
        self.resignButton = DirectButton(
            parent=self.statusFrame,
            text="Resign",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(-0.5, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.showResignDialog
        )
        
        # Undo button
        self.undoButton = DirectButton(
            parent=self.statusFrame,
            text="Undo",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.5, 0.5, 0.8, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.undoMove
        )
        
        # Save button
        self.saveButton = DirectButton(
            parent=self.statusFrame,
            text="Save",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.2, 0.6, 0.8, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0.5, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.saveGame
        )
        
        # Quit button on the right
        self.quitButton = DirectButton(
            parent=self.statusFrame,
            text="Quit",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.5, 0.5, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(1.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.showQuitDialog
        )
        
        # Move history display on the right side (optional, hidden by default)
        self.moveHistoryFrame = DirectFrame(
            frameColor=(0.05, 0.05, 0.06, 0.8),
            frameSize=(-0.23, 0.23, -0.85, 0.85),
            pos=(1.1, 0, -0.15),
            relief='flat',
            borderWidth=(0.01, 0.01)
        )
        
        self.historyDrawerOpen = False
        
        self.historyToggleButton = DirectButton(
            parent=self.moveHistoryFrame,
            text="<",
            text_pos=(0, -0.015),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.4, 0.6, 0.9),
            frameSize=(-0.05, 0.05, -0.1, 0.1),
            pos=(-0.28, 0, 0),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.toggleHistoryDrawer
        )

        self.moveHistoryLabel = DirectLabel(
            parent=self.moveHistoryFrame,
            text="",
            text_fg=(1, 1, 1, 1),
            text_scale=0.05,
            text_align=TextNode.ALeft,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            text_wordwrap=15,
            textMayChange=1,
            frameColor=(0, 0, 0, 0),
            pos=(-0.2, 0, 0.7)
        )

    def setStatus(self, text):
        """Update the status text and keep the main turn text in sync."""
        if hasattr(self, 'statusLabel'):
            self.statusLabel['text'] = text
        if text.startswith("Turn:"):
            self.turnText.setText(text)

    def _applyPieceMaterial(self, piece):
        """Apply material and shader settings for piece objects created during state changes."""
        if not piece or not hasattr(piece, 'obj') or not piece.obj:
            return
        mat = Material()
        mat.setShininess(30.0)
        mat.setSpecular((0.6, 0.6, 0.6, 1))
        piece.obj.setMaterial(mat, 1)
        piece.obj.setShaderAuto()

    def saveGame(self):
        """Save the current game state to a JSON file."""
        if self.gameOver:
            self.setStatus("Cannot save - game is over")
            return
        
        # Create saves directory if it doesn't exist
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir)
        
        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = os.path.join(saves_dir, f"chess_{self.mode}_{timestamp}.json")
        
        # Ask user for file location
        try:
            root = Tk()
            root.withdraw()  # Hide the root window
            filepath = filedialog.asksaveasfilename(
                initialdir=saves_dir,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"chess_{self.mode}_{timestamp}.json"
            )
            root.destroy()
        except Exception as e:
            self.setStatus(f"Save error: {str(e)}")
            return
        
        if not filepath:
            return  # User cancelled
        
        # Serialize game state
        game_state = self._serializeGameState()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(game_state, f, indent=2)
            self.setStatus(f"Game saved to {os.path.basename(filepath)}")
        except Exception as e:
            self.setStatus(f"Failed to save: {str(e)}")

    def loadGame(self):
        """Load a saved game state from a JSON file."""
        # Ask user for file location
        try:
            root = Tk()
            root.withdraw()  # Hide the root window
            filepath = filedialog.askopenfilename(
                initialdir="saves",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            self.setStatus(f"Load error: {str(e)}")
            return
        
        if not filepath:
            return  # User cancelled
        
        try:
            with open(filepath, 'r') as f:
                game_state = json.load(f)
            
            # Prevent loading a save from a different game mode
            saved_mode = game_state.get('mode', 'pvp')
            if saved_mode != self.mode:
                self.setStatus(f"Error: Cannot load {saved_mode.upper()} save in {self.mode.upper()} mode")
                return
            
            self._deserializeGameState(game_state)
            self.setStatus(f"Game loaded from {os.path.basename(filepath)}")
        except Exception as e:
            self.setStatus(f"Failed to load: {str(e)}")

    def loadGameState(self, game_state):
        """Public wrapper to load game state data."""
        self._deserializeGameState(game_state)

    def _serializeGameState(self):
        """Serialize the current game state to a JSON-compatible dictionary."""
        # Serialize piece positions
        board_state = []
        for i, piece in enumerate(self.pieces):
            if piece:
                piece_data = {
                    'square': i,
                    'type': piece.__class__.__name__,
                    'color': 'WHITE' if piece.color == WHITE else 'BLACK'
                }
                board_state.append(piece_data)
        
        game_state = {
            'board': board_state,
            'turn': 'WHITE' if self.turn == WHITE else 'BLACK',
            'enPassantSquare': self.enPassantSquare,
            'whiteKingMoved': self.whiteKingMoved,
            'blackKingMoved': self.blackKingMoved,
            'whiteRookMoved': self.whiteRookMoved,
            'blackRookMoved': self.blackRookMoved,
            'moveHistory': self._serializeMoveHistory(),
            'moveNotation': self.moveNotation,
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode,
            'playerColor': self.playerColor,
            'difficulty': self.difficulty
        }
        return game_state

    def _serializeMoveHistory(self):
        """Serialize move history for saving."""
        serialized = []
        for move in self.moveHistory:
            move_data = {
                'fr': move['fr'],
                'to': move['to'],
                'en_passant_square': move.get('en_passant_square'),
                'en_passant_capture': move.get('en_passant_capture'),
                'castling': move.get('castling', False),
                'promotion': move.get('promotion', False),
                'white_king_moved': move.get('white_king_moved', False),
                'black_king_moved': move.get('black_king_moved', False),
                'white_rooks_moved': move.get('white_rooks_moved', [False, False]),
                'black_rooks_moved': move.get('black_rooks_moved', [False, False]),
                'turn': 'WHITE' if move['turn'] == WHITE else 'BLACK',
                'moving_piece_type': move['moving_piece'].__class__.__name__ if 'moving_piece' in move and move['moving_piece'] else None,
                'moving_piece_color': 'WHITE' if 'moving_piece' in move and move['moving_piece'] and move['moving_piece'].color == WHITE else 'BLACK',
                'captured_piece_type': move['captured_piece'].__class__.__name__ if 'captured_piece' in move and move['captured_piece'] else None,
                'captured_piece_color': 'WHITE' if 'captured_piece' in move and move['captured_piece'] and move['captured_piece'].color == WHITE else ('BLACK' if 'captured_piece' in move and move['captured_piece'] else None)
            }
            if move.get('castling'):
                move_data['rook_from'] = move.get('rook_from')
                move_data['rook_to'] = move.get('rook_to')
            if move.get('promotion'):
                move_data['promotion_piece_type'] = move.get('promoted_piece').__class__.__name__ if move.get('promoted_piece') else None
                move_data['promotion_original_pawn_type'] = move.get('original_pawn').__class__.__name__ if move.get('original_pawn') else 'Pawn'

            serialized.append(move_data)
        return serialized

    def _deserializeMoveHistory(self, serialized_history):
        """Restore move history from saved data."""
        # Keep the raw serialized move history so undo can resolve state references as needed.
        return [dict(entry) for entry in serialized_history] if serialized_history else []

    def _createPieceFromType(self, piece_type, color, square):
        piece_classes = {
            'Pawn': Pawn, 'Knight': Knight, 'Bishop': Bishop,
            'Rook': Rook, 'Queen': Queen, 'King': King
        }
        cls = piece_classes.get(piece_type, Pawn)
        color_value = WHITE if color == 'WHITE' else PIECEBLACK
        return cls(square, color_value, parent=self.piecesNode)

    def _deserializeGameState(self, game_state):
        """Restore game state from a serialized dictionary."""
        # Clear current game
        for p in self.pieces:
            if p and hasattr(p, 'obj'):
                p.obj.removeNode()
        
        self.pieces = [None] * 64
        self.squareRoot.removeNode()
        self.piecesNode.removeNode()
        self.squareRoot = self.app.render.attachNewNode("squareRoot")
        self.piecesNode = self.app.render.attachNewNode("piecesNode")
        
        # Restore board state
        piece_classes = {
            'Pawn': Pawn, 'Knight': Knight, 'Bishop': Bishop,
            'Rook': Rook, 'Queen': Queen, 'King': King
        }
        
        for piece_data in game_state['board']:
            square = piece_data['square']
            piece_type = piece_classes[piece_data['type']]
            color = WHITE if piece_data['color'] == 'WHITE' else PIECEBLACK
            self.pieces[square] = piece_type(square, color, parent=self.piecesNode)
        
        # Restore game state
        self.turn = WHITE if game_state['turn'] == 'WHITE' else PIECEBLACK
        self.enPassantSquare = game_state['enPassantSquare']
        self.whiteKingMoved = game_state['whiteKingMoved']
        self.blackKingMoved = game_state['blackKingMoved']
        self.whiteRookMoved = game_state['whiteRookMoved']
        self.blackRookMoved = game_state['blackRookMoved']
        self.moveNotation = game_state.get('moveNotation', [])
        self.gameOver = False

        # Restore game configuration properties
        if 'mode' in game_state:
            self.mode = game_state['mode']
        if 'playerColor' in game_state:
            self.playerColor = game_state['playerColor']
        if 'difficulty' in game_state:
            self.difficulty = game_state['difficulty']
        self.rotateCameraEnabled = (self.mode != 'pvai')

        # Restore move history
        self.moveHistory = self._deserializeMoveHistory(game_state.get('moveHistory', []))

        # Restore board squares
        for i in range(64):
            sq = self.app.loader.loadModel("models/square")
            sq.reparentTo(self.squareRoot)
            sq.setPos(SquarePos(i))
            sq.setColor(self.getSquareColor(i))
            sq.find("**/polygon").node().setIntoCollideMask(BitMask32.bit(1))
            sq.find("**/polygon").node().setTag('square', str(i))
            self.squares[i] = sq
        
        # Update display
        self.updateMoveHistoryDisplay()
        self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")
        self.clearHighlights()

        # Stop any ongoing camera rotation
        if hasattr(self, 'orbit') and self.orbit.isPlaying():
            self.orbit.pause()
            
        # Reset camera orientation to face the correct side
        if self.turn == WHITE:
            self.camPivot.setHpr(0, 0, 0)
        else:
            self.camPivot.setHpr(180, 0, 0)

        # If PvAI mode is active and it is AI's turn, queue an AI move
        self.app.taskMgr.remove('aiMoveTask')
        if self.mode == 'pvai' and ((self.playerColor == 0 and self.turn == PIECEBLACK) or (self.playerColor == 1 and self.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def showResignDialog(self):
        """Show a confirmation dialog for resigning the game."""
        if self.gameOver:
            return
        
        # Create the resign confirmation dialog
        self.resignDialog = DirectDialog(
            dialogName="resignDialog",
            text="Are you sure you want to resign?",
            buttonTextList=["Yes", "No"],
            buttonValueList=[1, 0],
            command=self.onResignConfirm,
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01)
        )
        self.resignDialog.buttonList[0]['frameColor'] = (0.3, 0.6, 0.3, 1)  # Yes (Green)
        self.resignDialog.buttonList[1]['frameColor'] = (0.6, 0.3, 0.3, 1)  # No (Red)

    def onResignConfirm(self, value):
        """Handle the resign confirmation dialog response."""
        if value == 1:  # Yes, resign
            self.resignGame()
        
        # Clean up the dialog
        if hasattr(self, 'resignDialog'):
            self.resignDialog.cleanup()
            del self.resignDialog

    def resignGame(self):
        """End the game with resignation - opponent wins."""
        if self.gameOver:
            return
        
        self.gameOver = True
        winner = "BLACK" if self.turn == WHITE else "WHITE"
        self.setStatus(f"RESIGNATION! {winner} wins")
        self.clearHighlights()

    def showQuitDialog(self):
        """Show a confirmation dialog for quitting to the main menu."""
        if hasattr(self, 'quitDialog'):
            return
            
        self.quitDialog = DirectDialog(
            dialogName="quitDialog",
            text="Are you sure you want to quit to menu?",
            buttonTextList=["Yes", "No"],
            buttonValueList=[1, 0],
            command=self.onQuitConfirm,
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01)
        )
        self.quitDialog.buttonList[0]['frameColor'] = (0.3, 0.6, 0.3, 1)  # Yes (Green)
        self.quitDialog.buttonList[1]['frameColor'] = (0.6, 0.3, 0.3, 1)  # No (Red)

    def onQuitConfirm(self, value):
        """Handle the quit confirmation dialog response."""
        if value == 1:
            self.returnToMenu()
            
        if hasattr(self, 'quitDialog'):
            self.quitDialog.cleanup()
            del self.quitDialog

    def _undoLastMove(self):
        """Undo a single move and restore game state for that move."""
        if not self.moveHistory:
            return

        last_move = self.moveHistory.pop()
        if self.moveNotation:
            self.moveNotation.pop()

        # If the move is loaded from a saved file, it may be serialized with no object refs.
        if 'moving_piece' not in last_move:
            self._undoSerializedMove(last_move)
            self.rotateCamera(instant=True)
            return

        # Remove promoted piece if any
        if last_move.get('promotion', False):
            last_move['promoted_piece'].obj.removeNode()

        # Restore the board state
        fr = last_move['fr']
        to = last_move['to']
        moving_piece = last_move['moving_piece']
        captured_piece = last_move['captured_piece']

        # Move piece back
        self.pieces[fr] = moving_piece
        self.pieces[to] = captured_piece
        moving_piece.square = fr
        if hasattr(moving_piece, 'obj') and moving_piece.obj:
            moving_piece.obj.setPos(SquarePos(fr))
        else:
            moving_piece.obj = self.app.loader.loadModel(moving_piece.model)
            moving_piece.obj.reparentTo(self.piecesNode)
            moving_piece.obj.setColor(moving_piece.color)
            self._applyPieceMaterial(moving_piece)
            moving_piece.obj.setPos(SquarePos(fr))

        # Restore captured piece if any
        if captured_piece:
            captured_piece.square = to
            if hasattr(captured_piece, 'obj') and captured_piece.obj:
                captured_piece.obj.setPos(SquarePos(to))
            else:
                captured_piece.obj = self.app.loader.loadModel(captured_piece.model)
                captured_piece.obj.reparentTo(self.piecesNode)
                captured_piece.obj.setColor(captured_piece.color)
                self._applyPieceMaterial(captured_piece)
                captured_piece.obj.setPos(SquarePos(to))

        # Handle en passant undo
        if 'en_passant_capture' in last_move:
            captured_sq = last_move['en_passant_capture']
            victim = last_move['en_passant_victim']
            self.pieces[captured_sq] = victim
            victim.square = captured_sq
            if hasattr(victim, 'obj') and victim.obj:
                victim.obj.setPos(SquarePos(captured_sq))
            else:
                victim.obj = self.app.loader.loadModel(victim.model)
                victim.obj.reparentTo(self.piecesNode)
                victim.obj.setColor(victim.color)
                self._applyPieceMaterial(victim)
                victim.obj.setPos(SquarePos(captured_sq))

        # Handle castling undo
        if last_move['castling']:
            rook_from = last_move['rook_from']
            rook_to = last_move['rook_to']
            rook = self.pieces[rook_to]
            self.pieces[rook_from] = rook
            self.pieces[rook_to] = None
            if hasattr(rook, 'obj') and rook.obj:
                rook.obj.setPos(SquarePos(rook_from))
            rook.square = rook_from

        # Handle promotion undo
        if last_move['promotion']:
            promoted_piece = last_move['promoted_piece']
            original_pawn = last_move['original_pawn']
            self.pieces[to] = original_pawn
            original_pawn.square = to
            if hasattr(original_pawn, 'obj') and original_pawn.obj:
                original_pawn.obj.setPos(SquarePos(to))
            else:
                original_pawn.obj = self.app.loader.loadModel(original_pawn.model)
                original_pawn.obj.reparentTo(self.piecesNode)
                original_pawn.obj.setColor(original_pawn.color)
                self._applyPieceMaterial(original_pawn)
                original_pawn.obj.setPos(SquarePos(to))
            if hasattr(promoted_piece, 'obj') and promoted_piece.obj:
                promoted_piece.obj.removeNode()

        # Restore game state flags
        self.enPassantSquare = last_move['en_passant_square']
        self.whiteKingMoved = last_move['white_king_moved']
        self.blackKingMoved = last_move['black_king_moved']
        self.whiteRookMoved = last_move['white_rooks_moved']
        self.blackRookMoved = last_move['black_rooks_moved']
        self.turn = last_move['turn']

        self.rotateCamera(instant=True)

    def undoMove(self):
        """Undo the last move if possible."""
        if not self.moveHistory or self.gameOver:
            return

        move_count = 2 if self.mode == 'pvai' else 1
        for _ in range(move_count):
            if not self.moveHistory:
                break
            self._undoLastMove()

        # Update status after all undone moves
        self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")
        self.selectedSquare = None
        self.validMoves = []
        self.clearHighlights()
        self.updateMoveHistoryDisplay()

        # If PvAI and it becomes AI's turn, schedule AI move
        if self.mode == 'pvai':
            ai_color = PIECEBLACK if self.playerColor == 0 else WHITE
            if self.turn == ai_color and not self.gameOver:
                self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def _undoSerializedMove(self, move):
        """Undo a serialized move record loaded from a save file."""
        fr = move['fr']
        to = move['to']
        promotion = move.get('promotion', False)
        en_passant_capture = move.get('en_passant_capture')
        castling = move.get('castling', False)

        # The moved piece should be at the destination square currently.
        moving_piece = self.pieces[to] if to is not None else None
        if not moving_piece and promotion:
            # promotion may have removed original pawn; assume piece at to is the promoted piece
            moving_piece = self.pieces[to]

        # Build captured piece object if it existed
        captured_piece = None
        if en_passant_capture is not None:
            captured_piece_type = move.get('captured_piece_type', 'Pawn')
            captured_piece_color = move.get('captured_piece_color', 'BLACK')
            captured_piece = self._createPieceFromType(captured_piece_type, captured_piece_color, en_passant_capture)
            self.pieces[en_passant_capture] = captured_piece
            # captured pawn is not on 'to' in en passant
            self.pieces[to] = None
        elif move.get('captured_piece_type'):
            captured_piece_type = move['captured_piece_type']
            captured_piece_color = move.get('captured_piece_color', 'BLACK')
            captured_piece = self._createPieceFromType(captured_piece_type, captured_piece_color, to)
            self.pieces[to] = captured_piece

        if promotion:
            # Remove promoted piece from destination and restore pawn to source.
            if moving_piece and hasattr(moving_piece, 'obj') and moving_piece.obj:
                moving_piece.obj.removeNode()
            pawn_color = 'WHITE' if move.get('moving_piece_color', 'WHITE') == 'WHITE' else 'BLACK'
            pawn = self._createPieceFromType('Pawn', pawn_color, fr)
            self.pieces[fr] = pawn
            pawn.square = fr
            # keep the destination capture or empty square
            if captured_piece:
                self.pieces[to] = captured_piece
            else:
                self.pieces[to] = None
        else:
            # Non-promotion revert
            if moving_piece:
                self.pieces[fr] = moving_piece
                self.pieces[to] = captured_piece
                moving_piece.square = fr
                if hasattr(moving_piece, 'obj') and moving_piece.obj:
                    moving_piece.obj.reparentTo(self.piecesNode)
                    moving_piece.obj.setPos(SquarePos(fr))
                else:
                    moving_piece.obj = self.app.loader.loadModel(moving_piece.model)
                    moving_piece.obj.reparentTo(self.piecesNode)
                    moving_piece.obj.setColor(moving_piece.color)
                    self._applyPieceMaterial(moving_piece)
                    moving_piece.obj.setPos(SquarePos(fr))

        if castling:
            rook_from = move.get('rook_from')
            rook_to = move.get('rook_to')
            rook = self.pieces[rook_to]
            if rook:
                self.pieces[rook_from] = rook
                self.pieces[rook_to] = None
                rook.square = rook_from
                if hasattr(rook, 'obj') and rook.obj:
                    rook.obj.setPos(SquarePos(rook_from))

        # Restore state flags
        self.enPassantSquare = move.get('en_passant_square')
        self.whiteKingMoved = move.get('white_king_moved', False)
        self.blackKingMoved = move.get('black_king_moved', False)
        self.whiteRookMoved = move.get('white_rooks_moved', [False, False])
        self.blackRookMoved = move.get('black_rooks_moved', [False, False])
        self.turn = WHITE if move.get('turn') == 'WHITE' else PIECEBLACK

    def squareToAlgebraic(self, square):
        """Convert square index to algebraic notation (e.g., 0 -> 'a1')."""
        file = chr(ord('a') + (square % 8))
        rank = str((square // 8) + 1)
        return file + rank

    def formatMove(self, move_record):
        """Format a move record into algebraic notation."""
        piece = move_record['moving_piece']
        fr = move_record['fr']
        to = move_record['to']
        captured = move_record['captured_piece']
        
        if move_record['castling']:
            if to > fr:
                return "O-O"
            else:
                return "O-O-O"
        elif move_record['promotion']:
            piece_type = move_record['promoted_piece'].__class__.__name__[0]
            if captured:
                return self.squareToAlgebraic(fr)[0] + "x" + self.squareToAlgebraic(to) + "=" + piece_type
            else:
                return self.squareToAlgebraic(to) + "=" + piece_type
        else:
            piece_letter = "" if isinstance(piece, Pawn) else piece.__class__.__name__[0]
            capture_symbol = "x" if captured or (isinstance(piece, Pawn) and to == move_record.get('en_passant_square')) else ""
            return piece_letter + capture_symbol + self.squareToAlgebraic(to)

    def addMoveToHistory(self, move_record):
        """Add a formatted move to the history and update display."""
        notation = self.formatMove(move_record)
        self.moveNotation.append(notation)
        self.updateMoveHistoryDisplay()

    def updateMoveHistoryDisplay(self):
        """Update the move history display with current moves."""
        # Format as numbered moves: 1. e4 e5  2. Nf3 Nc6 etc.
        text_lines = []
        for i in range(0, len(self.moveNotation), 2):
            move_num = (i // 2) + 1
            white_move = self.moveNotation[i] if i < len(self.moveNotation) else ""
            black_move = self.moveNotation[i+1] if i+1 < len(self.moveNotation) else ""
            text_lines.append(f"{move_num}. {white_move} {black_move}")
        
        text = "\n".join(text_lines)
        if hasattr(self, 'moveHistoryLabel'):
            self.moveHistoryLabel['text'] = text
            
    def toggleHistoryDrawer(self):
        """Toggle the move history drawer sliding in and out."""
        w = self.app.win.getXSize()
        h = self.app.win.getYSize()
        window_aspect = w / float(h) if h > 0 else 1.33
        
        on_x = window_aspect - 0.25
        off_x = window_aspect + 0.25
        
        if hasattr(self, 'drawerInterval') and self.drawerInterval.isPlaying():
            self.drawerInterval.pause()
            
        if self.historyDrawerOpen:
            self.drawerInterval = LerpPosInterval(
                self.moveHistoryFrame,
                0.3,
                (off_x, 0, -0.15),
                blendType='easeInOut'
            )
            self.historyToggleButton['text'] = "<"
            self.historyDrawerOpen = False
        else:
            self.drawerInterval = LerpPosInterval(
                self.moveHistoryFrame,
                0.3,
                (on_x, 0, -0.15),
                blendType='easeInOut'
            )
            self.historyToggleButton['text'] = ">"
            self.historyDrawerOpen = True
            
        self.drawerInterval.start()

    def showPromotionDialog(self, square):
        """Show a dialog for pawn promotion choice."""
        if self.gameOver:
            return
        
        # Create the promotion dialog
        self.promotionDialog = DirectDialog(
            dialogName="promotionDialog",
            text="Choose promotion piece:",
            buttonTextList=["Queen", "Rook", "Bishop", "Knight"],
            buttonValueList=["Queen", "Rook", "Bishop", "Knight"],
            command=self.onPromotionChoice,
            extraArgs=[square],
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01)
        )
        
        self.promotionDialog.buttonList[0]['frameColor'] = (0.6, 0.4, 0.8, 1)  # Queen (Purple)
        self.promotionDialog.buttonList[1]['frameColor'] = (0.8, 0.4, 0.4, 1)  # Rook (Red)
        self.promotionDialog.buttonList[2]['frameColor'] = (0.4, 0.8, 0.4, 1)  # Bishop (Green)
        self.promotionDialog.buttonList[3]['frameColor'] = (0.2, 0.6, 0.8, 1)  # Knight (Blue)

    def onPromotionChoice(self, piece_type, square):
        """Handle the promotion piece selection."""
        if self.gameOver:
            return
        
        # Get the pawn to promote
        pawn = self.pieces[square]
        if not isinstance(pawn, Pawn):
            return
        
        # Create the new piece
        if piece_type == "Queen":
            new_piece = Queen(square, pawn.color, parent=self.piecesNode)
        elif piece_type == "Rook":
            new_piece = Rook(square, pawn.color, parent=self.piecesNode)
        elif piece_type == "Bishop":
            new_piece = Bishop(square, pawn.color, parent=self.piecesNode)
        elif piece_type == "Knight":
            new_piece = Knight(square, pawn.color, parent=self.piecesNode)
        else:
            return
        
        # Replace the pawn
        pawn.obj.removeNode()
        self.pieces[square] = new_piece
        
        # Update the last move record for undo
        if self.moveHistory:
            last_move = self.moveHistory[-1]
            last_move['promotion'] = True
            last_move['promoted_piece'] = new_piece
            last_move['original_pawn'] = pawn
        
        # Clean up the dialog
        if hasattr(self, 'promotionDialog'):
            self.promotionDialog.cleanup()
            del self.promotionDialog
        
        # Now continue with post-move logic
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
            self.clearHighlights()  # Clear all highlights when game ends
        elif black_stalemate or white_stalemate:
            self.gameOver = True
            self.setStatus("STALEMATE. Draw")
            self.clearHighlights()  # Clear all highlights when game ends
        else:
            self.switchTurn()
            if enemy_in_check:
                self.setStatus(f"Check to {'BLACK' if enemy == PIECEBLACK else 'WHITE'}")
            else:
                self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")

            # AI should move immediately after promotion if it is AI's turn
            if self.mode == 'pvai' and ((self.playerColor == 0 and self.turn == PIECEBLACK) or (self.playerColor == 1 and self.turn == WHITE)):
                self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def onNewGame(self):
        """Reset the board and gameplay state for a new game."""
        # Remove old pieces
        for p in self.pieces:
            if p and hasattr(p, 'obj'):
                p.obj.removeNode()

        self.squares = [None] * 64
        self.pieces = [None] * 64
        self.squareRoot.removeNode()
        self.piecesNode.removeNode()
        self.piecesNode = self.app.render.attachNewNode("piecesNode")

        # Reset camera/orientation to initial starting view
        self.camPivot.setHpr(0, 0, 0)
        
        # Set initial camera rotation based on player color (same as initializeGame)
        if self.playerColor == 1:  # Playing as black
            self.camPivot.setH(180)  # Face black side initially
            
        self.app.camera.reparentTo(self.camPivot)
        self.app.camera.setPos(0, -14, 10)
        self.app.camera.lookAt(0, 0, 0)

        self.enPassantSquare = None
        self.whiteKingMoved = False
        self.blackKingMoved = False
        self.whiteRookMoved = [False, False]
        self.blackRookMoved = [False, False]
        self.validMoves = []
        self.moveHistory = []
        self.moveNotation = []
        self.selectedSquare = None
        self.dragging = False
        self.gameOver = False
        self.turn = WHITE

        # Keep PvAI camera rotation rule consistent after reset
        self.rotateCameraEnabled = (self.mode != 'pvai')

        self.setupBoard()
        self.clearHighlights()
        self.updateMoveHistoryDisplay()
        self.updateCameraForAspect()
        self.setStatus("Turn: WHITE" if self.turn == WHITE else "Turn: BLACK")
        
        # If Player vs AI mode and AI starts, schedule the first AI move
        self.app.taskMgr.remove('aiMoveTask')
        if self.mode == 'pvai' and ((self.playerColor == 0 and self.turn == PIECEBLACK) or (self.playerColor == 1 and self.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    # Include all the other game methods (movePiece, isValidMove, etc.)
    # For brevity, I'll copy the key methods here
    
    def movePiece(self, fr, to):
        """
        Move a piece from one square to another, handling all game logic.
        """
        moving = self.pieces[fr]  # The piece being moved
        target = self.pieces[to]  # Piece at destination (if any)

        # Record the move for undo functionality
        move_record = {
            'fr': fr,
            'to': to,
            'moving_piece': moving,
            'captured_piece': target,
            'en_passant_square': self.enPassantSquare,
            'castling': False,
            'promotion': False,
            'promoted_piece': None,
            'white_king_moved': self.whiteKingMoved,
            'black_king_moved': self.blackKingMoved,
            'white_rooks_moved': self.whiteRookMoved.copy(),
            'black_rooks_moved': self.blackRookMoved.copy(),
            'turn': self.turn
        }

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
        en_passant_capture = False
        if isinstance(moving, Pawn) and to == self.enPassantSquare:
            # If this is an en passant capture
            # Calculate the square of the captured pawn.
            captured = to - 8 if moving.color == WHITE else to + 8

            victim = self.pieces[captured]
            if victim:
                victim.obj.removeNode()  # Remove captured pawn
                self.pieces[captured] = None  # Clear the square
                move_record['en_passant_capture'] = captured
                move_record['en_passant_victim'] = victim

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
            move_record['castling'] = True
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
            move_record['rook_from'] = rookFrom
            move_record['rook_to'] = rookTo

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

        # Add the move to history
        self.moveHistory.append(move_record)
        self.addMoveToHistory(move_record)

        # Play sound effect by move type
        isCapture = target is not None or (isinstance(moving, Pawn) and to == self.enPassantSquare)
        isCastle = isinstance(moving, King) and abs((to % 8) - (fr % 8)) == 2
        enemy = PIECEBLACK if moving.color == WHITE else WHITE
        inCheck = self.isKingInCheck(enemy)

        if move_record['promotion']:
            self.promoteSound.play()
        elif isCastle:
            self.castleSound.play()
        elif isCapture:
            self.captureSound.play()
        elif inCheck:
            self.moveCheckSound.play()
        else:
            self.moveSelfSound.play()

    def isValidMove(self, fr, to):
        """
        Check if a move from one square to another is valid according to chess rules.
        """
        if fr == to:
            return False

        piece = self.pieces[fr]
        if not piece:
            return False

        state = {
            'en_passant_square': self.enPassantSquare,
            'white_king_moved': self.whiteKingMoved,
            'black_king_moved': self.blackKingMoved,
            'white_rook_moved': self.whiteRookMoved,
            'black_rook_moved': self.blackRookMoved
        }
        
        return to in piece.get_pseudo_legal_moves(self.pieces, fr, state)

    def getLegalMoves(self, square):
        """
        Get all legal moves for a piece, considering check.
        """
        piece = self.pieces[square]
        if not piece:
            return []
            
        state = {
            'en_passant_square': self.enPassantSquare,
            'white_king_moved': self.whiteKingMoved,
            'black_king_moved': self.blackKingMoved,
            'white_rook_moved': self.whiteRookMoved,
            'black_rook_moved': self.blackRookMoved
        }

        pseudo_moves = piece.get_pseudo_legal_moves(self.pieces, square, state)
        moves = []

        for to in pseudo_moves:
            # Simulate the move
            captured = self.pieces[to]
            self.pieces[to] = piece
            self.pieces[square] = None

            # Check if this move would leave own king in check
            kingCheck = self.isKingInCheck(piece.color)

            # Revert the simulation
            self.pieces[square] = piece
            self.pieces[to] = captured

            # Move is legal if it doesn't leave king in check
            if not kingCheck:
                # Extra check for castling: can't castle out of or through check
                if isinstance(piece, King) and abs((to % 8) - (square % 8)) == 2:
                    if self.isKingInCheck(piece.color):
                        continue
                    
                    pass_through_sq = square + (1 if to > square else -1)
                    self.pieces[pass_through_sq] = piece
                    self.pieces[square] = None
                    passCheck = self.isKingInCheck(piece.color)
                    self.pieces[square] = piece
                    self.pieces[pass_through_sq] = None
                    
                    if passCheck:
                        continue
                        
                moves.append(to)

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

        state = {
            'en_passant_square': self.enPassantSquare,
            'white_king_moved': self.whiteKingMoved,
            'black_king_moved': self.blackKingMoved,
            'white_rook_moved': self.whiteRookMoved,
            'black_rook_moved': self.blackRookMoved
        }

        # Check if any enemy piece can move to the king's square
        for i, p in enumerate(self.pieces):
            if p and p.color != color:
                # We only need pseudo-legal moves to see if the king is attacked
                if kingSquare in p.get_pseudo_legal_moves(self.pieces, i, state):
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

            # Convert standard window mouse coordinates to our custom DisplayRegion coordinates
            if hasattr(self, 'dr'):
                l, r, b, t = self.dr.getDimensions()
            else:
                l, r, b, t = 0.0, 1.0, 0.0, 1.0
                
            # Mouse position normalized from 0 to 1 relative to the whole window
            win_x = (mpos.getX() + 1.0) / 2.0
            win_y = (mpos.getY() + 1.0) / 2.0
            
            # Only process 3D picking if the mouse is actually inside the 3D DisplayRegion
            if l <= win_x <= r and b <= win_y <= t:
                # Map mouse into the DisplayRegion's internal -1 to 1 coordinate space
                dr_x = ((win_x - l) / (r - l)) * 2.0 - 1.0
                dr_y = ((win_y - b) / (t - b)) * 2.0 - 1.0
                
                # Update the collision ray from camera through the mapped mouse position
                self.pickerRay.setFromLens(self.app.camNode, dr_x, dr_y)
    
                # If dragging a piece, update its position to follow mouse
                if self.dragging is not False:
                    nearPoint = self.app.render.getRelativePoint(self.app.camera, self.pickerRay.getOrigin())
                    nearVec = self.app.render.getRelativeVector(self.app.camera, self.pickerRay.getDirection())
                    self.pieces[self.dragging].obj.setPos(PointAtZ(.5, nearPoint, nearVec))
    
                # Perform collision detection on the squares
                self.picker.traverse(self.squareRoot)
    
                # If collision detected, get the closest one
                if self.pq.getNumEntries() > 0:
                    self.pq.sortEntries()
                    self.hiSq = int(self.pq.getEntry(0).getIntoNode().getTag('square'))
                else:
                    self.hiSq = False
            else:
                # Mouse is outside the 3D DisplayRegion (over the top UI)
                # Mouse is over the top UI
                self.hiSq = False

        # If not dragging and mouse over a square, highlight it (only if game is not over)
        if self.dragging is False and not self.gameOver:
            self.clearHighlights()
            
            # Re-apply selection highlight and valid moves for click-to-move
            if self.selectedSquare is not None:
                self.squares[self.selectedSquare].setColor(YELLOW)
                self.highlightMoves()
                
            # Highlight the square under the mouse
            if self.hiSq is not False:
                self.squares[self.hiSq].setColor(HIGHLIGHT)

        return Task.cont  # Continue the task

    def grabPiece(self):
        """
        Handle mouse button press - attempt to grab a piece or execute a click-to-move.
        """
        if self.gameOver:
            return

        # In PvAI, only the local player can interact with pieces on their turn
        if self.mode == 'pvai':
            local_player_color = WHITE if self.playerColor == 0 else PIECEBLACK
            if self.turn != local_player_color:
                return

        # Check if we clicked a valid move for the currently selected piece (click-to-move)
        if self.selectedSquare is not None and self.hiSq is not False and self.hiSq in self.validMoves:
            success = self.moveAndProcessTurn(self.selectedSquare, self.hiSq)
            if not success:
                if self.pieces[self.selectedSquare] and self.pieces[self.selectedSquare].obj:
                    self.pieces[self.selectedSquare].obj.setPos(SquarePos(self.selectedSquare))
            
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.clearHighlights()
            return

        # Otherwise, check if we clicked a piece to select/drag
        if self.hiSq is not False and self.pieces[self.hiSq]:
            piece = self.pieces[self.hiSq]
            if piece.color == self.turn:
                self.clearHighlights()
                self.selectedSquare = self.hiSq
                self.dragging = self.hiSq
                self.validMoves = self.getLegalMoves(self.hiSq)
                self.squares[self.selectedSquare].setColor(YELLOW)
                self.highlightMoves()
                return

        # Clicked an empty square or enemy piece that is not a valid move
        if self.selectedSquare is not None:
            if self.pieces[self.selectedSquare] and self.pieces[self.selectedSquare].obj:
                self.pieces[self.selectedSquare].obj.setPos(SquarePos(self.selectedSquare))
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.clearHighlights()

    def moveAndProcessTurn(self, fr, to):
        """Execute a move, handle promotion, checkmate, stalemate, and switch turns."""
        # Prevent direct king capture (legal move logic should avoid this scenario in real chess).
        if isinstance(self.pieces[to], King):
            self.setStatus("Illegal move: cannot capture king")
            return False

        self.movePiece(fr, to)

        # Check for pawn promotion
        piece = self.pieces[to]
        if isinstance(piece, Pawn) and ((piece.color == WHITE and to // 8 == 7) or (piece.color == PIECEBLACK and to // 8 == 0)):
            self.showPromotionDialog(to)
            return True

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
            self.clearHighlights()  # Clear all highlights when game ends
        elif black_stalemate or white_stalemate:
            self.gameOver = True
            self.setStatus("STALEMATE. Draw")
            self.clearHighlights()  # Clear all highlights when game ends
        else:
            self.switchTurn()
            if enemy_in_check:
                self.setStatus(f"Check to {'BLACK' if enemy == PIECEBLACK else 'WHITE'}")
            else:
                self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")

            # If PvAI mode is active and it is AI's turn, queue an AI move.
            if self.mode == 'pvai' and ((self.playerColor == 0 and self.turn == PIECEBLACK) or (self.playerColor == 1 and self.turn == WHITE)):
                self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')
                
        return True

    def releasePiece(self):
        """
        Handle mouse button release - attempt to drop the piece.
        """
        if self.dragging is False or self.gameOver:
            self.dragging = False
            return

        piece = self.pieces[self.dragging]

        # If dropped back on the original square (or just a simple click)
        if self.hiSq == self.dragging:
            piece.obj.setPos(SquarePos(self.dragging))
            self.dragging = False
            # KEEP self.selectedSquare and validMoves intact so click-to-move works
            return

        # If dropped on a valid move square
        if self.hiSq is not False and self.hiSq in self.validMoves:
            success = self.moveAndProcessTurn(self.dragging, self.hiSq)
            if not success:
                piece.obj.setPos(SquarePos(self.dragging))
            
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.clearHighlights()
            return

        # Invalid drop - return piece to original position and clear selection
        self.setStatus("Invalid move")
        piece.obj.setPos(SquarePos(self.dragging))
        self.selectedSquare = None
        self.dragging = False
        self.validMoves = []
        self.clearHighlights()

    def makeAIMove(self, task):
        """AI: uses Minimax algorithm to find the best move."""
        if self.gameOver:
            return Task.done

        # Map difficulty slider (1-5) to Minimax search depth (1-3 or 4)
        # Depth > 3 can be very slow in pure Python, so we clamp it to prevent freezing
        depth = min(4, max(1, int(self.difficulty)))
        
        best_move = get_best_move(self, depth)
        
        if not best_move:
            # No moves available for AI; checkmate or stalemate
            ai_color = PIECEBLACK if self.playerColor == 0 else WHITE
            if self.isKingInCheck(ai_color):
                self.setStatus(f"CHECKMATE! {'WHITE' if self.playerColor == 1 else 'BLACK'} wins")
                self.gameOver = True
            else:
                self.setStatus("STALEMATE. Draw")
                self.gameOver = True
            return Task.done

        fr, to = best_move
        self.movePiece(fr, to)

        piece = self.pieces[to]
        if isinstance(piece, Pawn) and ((piece.color == WHITE and to // 8 == 7) or (piece.color == PIECEBLACK and to // 8 == 0)):
            self.showPromotionDialog(to)
            return Task.done

        enemy = PIECEBLACK if self.turn == WHITE else WHITE
        enemy_in_check = self.isKingInCheck(enemy)

        if self.isCheckmate(enemy):
            self.gameOver = True
            winner = 'WHITE' if enemy == PIECEBLACK else 'BLACK'
            self.setStatus(f"CHECKMATE! {winner} wins")
            self.clearHighlights()
            return Task.done
        if self.isStalemate(enemy):
            self.gameOver = True
            self.setStatus("STALEMATE. Draw")
            self.clearHighlights()
            return Task.done

        self.switchTurn()
        self.setStatus(f"Turn: {'WHITE' if self.turn == WHITE else 'BLACK'}")
        if enemy_in_check:
            self.setStatus(f"Check to {'WHITE' if enemy == WHITE else 'BLACK'}")

        return Task.done

    def highlightMoves(self):
        """
        Highlight all valid move destinations for the current piece.
        """
        if self.selectedSquare is None:
            return

        for m in self.validMoves:
            piece = self.pieces[self.selectedSquare]

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
            self.squares[i].setColor(self.getSquareColor(i))

        # Highlight checked king square (only if game is not over)
        if hasattr(self, 'checkedKingSquare') and self.checkedKingSquare is not None and not self.gameOver:
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

    def rotateCamera(self, instant=False):
        """
        Animate the camera rotating 180 degrees around the board.
        
        Parameters:
        - instant: If True, rotate instantly without animation
        """
        if not getattr(self, 'rotateCameraEnabled', False):
            return

        if instant:
            currentH = self.camPivot.getH()
            self.camPivot.setH(currentH - 180)
        else:
            # Finish any ongoing rotation
            if hasattr(self, 'orbit') and self.orbit.isPlaying():
                self.orbit.finish()
            
            startH = self.camPivot.getH()  # Current heading
            endH = startH - 180            # Rotate 180 degrees (clockwise)

            self.orbit = LerpHprInterval(
                self.camPivot,  # Node to rotate
                1.2,            # Duration in seconds
                (endH, 0, 0),   # Target HPR (heading, pitch, roll)
                blendType="easeInOut"  # Smooth easing
            )
            self.orbit.start()  # Start the animation

    def updateCameraForAspect(self):
        """Keep vertical FOV fixed and adapt horizontal FOV to avoid stretching."""
        if not self.app or not self.app.win:
            return

        w = self.app.win.getXSize()
        h = self.app.win.getYSize()
        if h <= 0:
            return
            
        # Window aspect ratio for 2D UI elements
        window_aspect = w / float(h)
        
        # Update the top UI frame to dynamically expand across the entire window width
        if hasattr(self, 'statusFrame'):
            self.statusFrame['frameSize'] = (-window_aspect, window_aspect, -0.15, 0.15)
            
            # Spread buttons symmetrically, keeping them at least 1.0 unit from center
            spread = max(1.0, window_aspect - 0.335)
            if hasattr(self, 'restartButton'): self.restartButton.setPos(-spread, 0, -0.09)
            if hasattr(self, 'resignButton'):  self.resignButton.setPos(-spread/2, 0, -0.09)
            if hasattr(self, 'undoButton'):    self.undoButton.setPos(0, 0, -0.09)
            if hasattr(self, 'saveButton'):    self.saveButton.setPos(spread/2, 0, -0.09)
            if hasattr(self, 'quitButton'):    self.quitButton.setPos(spread, 0, -0.09)
            
        # Update move history frame position
        if hasattr(self, 'moveHistoryFrame'):
            on_x = window_aspect - 0.25
            off_x = window_aspect + 0.25
            is_animating = hasattr(self, 'drawerInterval') and self.drawerInterval.isPlaying()
            if not is_animating:
                if getattr(self, 'historyDrawerOpen', False):
                    self.moveHistoryFrame.setPos(on_x, 0, -0.15)
                else:
                    self.moveHistoryFrame.setPos(off_x, 0, -0.15)
            
        # Adjust dimensions if we are using a custom DisplayRegion
        if hasattr(self, 'dr'):
            l, r, b, t = self.dr.getDimensions()
            w = w * (r - l)
            h = h * (t - b)

        cam_aspect = w / float(h)

        lens = self.app.cam.node().getLens()

        # Keep vertical FOV steady; adjust aspect ratio instead.
        v_fov = self.app.settings_mgr.get('fov', 45.0)
        lens.setFov(v_fov)

        lens.setAspectRatio(cam_aspect)

    def setupLights(self):
        """
        Set up improved lighting for the 3D scene.
        """
        graphics = self.app.settings_mgr.get('graphics', 'high')
        
        # Enable auto-shaders based on graphics quality
        if graphics != 'off':
            self.app.render.setShaderAuto()
            if hasattr(self, 'piecesNode'):
                self.piecesNode.setShaderAuto()
            if hasattr(self, 'squareRoot'):
                self.squareRoot.setShaderAuto()
        
        # Ambient light (always)
        ambient = AmbientLight("ambient")
        ambient.setColor((0.35, 0.35, 0.35, 1))
        self.ambientLightNode = self.app.render.attachNewNode(ambient)
        self.app.render.setLight(self.ambientLightNode)
        
        if graphics == 'high':
            # Full lights + shadows
            main_dir = DirectionalLight("main_dir")
            main_dir.setDirection(LVector3(-1, -1, -2))
            main_dir.setColor((0.9, 0.9, 0.9, 1))
            main_dir.setShadowCaster(True, 2048, 2048)
            main_dir.getLens().setNearFar(5, 100)
            self.mainDirectionalLightNode = self.app.render.attachNewNode(main_dir)
            self.app.render.setLight(self.mainDirectionalLightNode)
            
            # Fill lights
            fill_dir = DirectionalLight("fill_dir")
            fill_dir.setDirection(LVector3(1, 2, -0.5))
            fill_dir.setColor((0.35, 0.35, 0.45, 1))
            self.fillDirectionalLightNode = self.app.render.attachNewNode(fill_dir)
            self.app.render.setLight(self.fillDirectionalLightNode)
            
            back_dir = DirectionalLight("back_dir")
            back_dir.setDirection(LVector3(0, 0, -1))
            back_dir.setColor((0.2, 0.2, 0.25, 1))
            self.backDirectionalLightNode = self.app.render.attachNewNode(back_dir)
            self.app.render.setLight(self.backDirectionalLightNode)
        elif graphics == 'low':
            # Basic directional
            dir_light = DirectionalLight("dir")
            dir_light.setDirection(LVector3(-1, -1, -1))
            dir_light.setColor((0.8, 0.8, 0.8, 1))
            self.mainDirectionalLightNode = self.app.render.attachNewNode(dir_light)
            self.app.render.setLight(self.mainDirectionalLightNode)
        
        self.app.setBackgroundColor(0.08, 0.1, 0.12, 1)
