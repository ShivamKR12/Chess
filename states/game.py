from direct.task.Task import Task

from states.base_state import AppState
from constants import WHITE, PIECEBLACK, SquarePos
from pieces import Pawn, Rook, Knight, Bishop, Queen, King
from ai import get_best_move
from states.game_ui import GameUI
from chess_logic import ChessLogic
from input_handler import InputHandler
from save_manager import SaveManager
from game_renderer import GameRenderer


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
        self.logic = ChessLogic()

        self.rotateCameraEnabled = (self.mode != 'pvai')
        
        self.sfx_volume = self.app.settings_mgr.get('sfx_volume', 1.0)
        
        self.click_sound = self.app.loader.loadSfx("sounds/clicksoundeffect.mp3")
        self.click_sound.setVolume(self.sfx_volume)

        self.renderer = GameRenderer(self)
        self.input_handler = InputHandler(self)
        self.save_manager = SaveManager(self)

        self.gameOver = False
        self.ui = GameUI(self)
        self.ui.setStatus(f"Turn: {'WHITE' if self.logic.turn == WHITE else 'BLACK'}")

        # Bind the escape key to prompt quit dialog
        self.accept('escape', self.ui.showQuitDialog)

        self.accept("r", self.onNewGame)

        # If Player vs AI mode and AI starts, schedule the first AI move
        if self.mode == 'pvai' and ((self.playerColor == 0 and self.logic.turn == PIECEBLACK) or (self.playerColor == 1 and self.logic.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

        # Safely restrict the main window's DisplayRegion (avoiding CommonFilters off-screen buffer conflicts)
        self.dr = self.app.main_3d_dr
        self.dr.setDimensions(0, 1, 0, 0.85)  # Restrict 3D to the bottom 85% of screen
        # Force UI elements to scale to the correct window aspect ratio immediately
        self.renderer.update_camera_for_aspect()

    def returnToMenu(self):
        """Return to the main menu."""
        self.app.showMenu()
    
    def cleanup(self):
        """Clean up game resources."""
        if hasattr(self, 'ui'):
            self.ui.cleanup()
        
        if hasattr(self, 'input_handler'):
            self.input_handler.cleanup()
            
        if hasattr(self, 'renderer'):
            self.renderer.cleanup()
            
        # Restore full window DisplayRegion for menus
        if hasattr(self, 'dr'):
            self.dr.setDimensions(0, 1, 0, 1)
        
        self.app.taskMgr.remove('aiMoveTask')
        
        # Call base class cleanup to clear event handlers
        super().cleanup()

    def saveGame(self):
        """Wrapper to save the current game state using the SaveManager."""
        self.save_manager.save_game()

    def loadGame(self):
        """Wrapper to load a saved game state using the SaveManager."""
        self.save_manager.load_game()

    def loadGameState(self, game_state):
        """Public wrapper to load game state data sent from the menu."""
        self.save_manager.deserialize_game_state(game_state)

    def resignGame(self):
        """End the game with resignation - opponent wins."""
        if self.gameOver:
            return
        
        self.gameOver = True
        winner = "BLACK" if self.logic.turn == WHITE else "WHITE"
        self.ui.setStatus(f"RESIGNATION! {winner} wins")
        self.clearHighlights()

    def _undoLastMove(self):
        """Undo a single move visually and mathematically."""
        if not self.logic.moveHistory:
            return

        # If the move is loaded from a saved file, it has no 3D object refs
        if 'moving_piece' not in self.logic.moveHistory[-1]:
            move = self.logic.moveHistory.pop()
            
            is_uncompleted_promotion = move.get('moving_piece_type') == 'Pawn' and ((move.get('moving_piece_color') == 'WHITE' and move['to'] // 8 == 7) or (move.get('moving_piece_color') == 'BLACK' and move['to'] // 8 == 0)) and not move.get('promotion', False)
            if not is_uncompleted_promotion and self.logic.moveNotation:
                self.logic.moveNotation.pop()
                
            self._undoSerializedMove(move)
            self.renderer.rotate_camera(instant=True)
            return

        last_move = self.logic.undo_move()
        
        # Sync visuals
        fr = last_move['fr']
        to = last_move['to']
        moving_piece = last_move['moving_piece']
        captured_piece = last_move['captured_piece']

        if hasattr(moving_piece, 'obj') and moving_piece.obj:
            moving_piece.obj.setPos(SquarePos(fr))
        else:
            moving_piece.obj = self.app.loader.loadModel(moving_piece.model)
            moving_piece.obj.reparentTo(self.renderer.piecesNode)
            moving_piece.obj.setColor(moving_piece.color)
            self.renderer.apply_piece_material(moving_piece)
            moving_piece.obj.setPos(SquarePos(fr))

        # Restore captured piece if any
        if captured_piece:
            if hasattr(captured_piece, 'obj') and captured_piece.obj:
                captured_piece.obj.setPos(SquarePos(to))
            else:
                captured_piece.obj = self.app.loader.loadModel(captured_piece.model)
                captured_piece.obj.reparentTo(self.renderer.piecesNode)
                captured_piece.obj.setColor(captured_piece.color)
                self.renderer.apply_piece_material(captured_piece)
                captured_piece.obj.setPos(SquarePos(to))

        # Handle en passant undo
        if 'en_passant_capture' in last_move:
            captured_sq = last_move['en_passant_capture']
            victim = last_move['en_passant_victim']
            if hasattr(victim, 'obj') and victim.obj:
                victim.obj.setPos(SquarePos(captured_sq))
            else:
                victim.obj = self.app.loader.loadModel(victim.model)
                victim.obj.reparentTo(self.renderer.piecesNode)
                victim.obj.setColor(victim.color)
                self.renderer.apply_piece_material(victim)
                victim.obj.setPos(SquarePos(captured_sq))

        # Handle castling undo
        if last_move['castling']:
            rook_from = last_move['rook_from']
            rook_to = last_move['rook_to']
            rook = self.logic.pieces[rook_from]
            if hasattr(rook, 'obj') and rook.obj:
                rook.obj.setPos(SquarePos(rook_from))

        # Handle promotion undo
        if last_move['promotion']:
            promoted_piece = last_move['promoted_piece']
            original_pawn = last_move['original_pawn']
            if hasattr(original_pawn, 'obj') and original_pawn.obj:
                original_pawn.obj.setPos(SquarePos(to))
            else:
                original_pawn.obj = self.app.loader.loadModel(original_pawn.model)
                original_pawn.obj.reparentTo(self.renderer.piecesNode)
                original_pawn.obj.setColor(original_pawn.color)
                self.renderer.apply_piece_material(original_pawn)
                original_pawn.obj.setPos(SquarePos(to))
            if hasattr(promoted_piece, 'obj') and promoted_piece.obj:
                promoted_piece.obj.removeNode()

        self.renderer.rotate_camera(instant=True)

    def undoMove(self):
        """Undo the last move if possible."""
        # Cancel any pending AI moves immediately to prevent turn-stealing
        self.app.taskMgr.remove('aiMoveTask')

        if not self.logic.moveHistory or self.gameOver:
            return

        move_count = 2 if self.mode == 'pvai' else 1
        for _ in range(move_count):
            if not self.logic.moveHistory:
                break
            self._undoLastMove()

        # Update status after all undone moves
        self.ui.setStatus(f"Turn: {'WHITE' if self.logic.turn == WHITE else 'BLACK'}")
        self.input_handler.selectedSquare = None
        self.input_handler.validMoves = []
        self.renderer.clear_highlights()
        self.ui.updateMoveHistoryDisplay(self.logic.moveNotation)

        # If PvAI and it becomes AI's turn, schedule AI move
        if self.mode == 'pvai':
            ai_color = PIECEBLACK if self.playerColor == 0 else WHITE
            if self.logic.turn == ai_color and not self.gameOver:
                self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def _undoSerializedMove(self, move):
        """Undo a serialized move record loaded from a save file."""
        fr = move['fr']
        to = move['to']
        promotion = move.get('promotion', False)
        en_passant_capture = move.get('en_passant_capture')
        castling = move.get('castling', False)

        # The moved piece should be at the destination square currently.
        moving_piece = self.logic.pieces[to] if to is not None else None
        if not moving_piece and promotion:
            # promotion may have removed original pawn; assume piece at to is the promoted piece
            moving_piece = self.logic.pieces[to]

        # Build captured piece object if it existed
        captured_piece = None
        if en_passant_capture is not None:
            captured_piece_type = 'Pawn'
            captured_piece_color = move.get('en_passant_victim_color', 'BLACK')
            captured_piece = self.save_manager.create_piece_from_type(captured_piece_type, captured_piece_color, en_passant_capture)
            self.logic.pieces[en_passant_capture] = captured_piece
            # captured pawn is not on 'to' in en passant
            self.logic.pieces[to] = None
        elif move.get('captured_piece_type'):
            captured_piece_type = move['captured_piece_type']
            captured_piece_color = move.get('captured_piece_color', 'BLACK')
            captured_piece = self.save_manager.create_piece_from_type(captured_piece_type, captured_piece_color, to)
            self.logic.pieces[to] = captured_piece

        if promotion:
            # Remove promoted piece from destination and restore pawn to source.
            if moving_piece and hasattr(moving_piece, 'obj') and moving_piece.obj:
                moving_piece.obj.removeNode()
            pawn_color = 'WHITE' if move.get('moving_piece_color', 'WHITE') == 'WHITE' else 'BLACK'
            pawn = self.save_manager.create_piece_from_type('Pawn', pawn_color, fr)
            self.logic.pieces[fr] = pawn
            pawn.square = fr
            # keep the destination capture or empty square
            if captured_piece:
                self.logic.pieces[to] = captured_piece
            else:
                self.logic.pieces[to] = None
        else:
            # Non-promotion revert
            if moving_piece:
                self.logic.pieces[fr] = moving_piece
                self.logic.pieces[to] = captured_piece
                moving_piece.square = fr
                if hasattr(moving_piece, 'obj') and moving_piece.obj:
                    moving_piece.obj.reparentTo(self.renderer.piecesNode)
                    moving_piece.obj.setPos(SquarePos(fr))
                else:
                    moving_piece.obj = self.app.loader.loadModel(moving_piece.model)
                    moving_piece.obj.reparentTo(self.renderer.piecesNode)
                    moving_piece.obj.setColor(moving_piece.color)
                    self.renderer.apply_piece_material(moving_piece)
                    moving_piece.obj.setPos(SquarePos(fr))

        if castling:
            rook_from = move.get('rook_from')
            rook_to = move.get('rook_to')
            rook = self.logic.pieces[rook_to]
            if rook:
                self.logic.pieces[rook_from] = rook
                self.logic.pieces[rook_to] = None
                rook.square = rook_from
                if hasattr(rook, 'obj') and rook.obj:
                    rook.obj.setPos(SquarePos(rook_from))

        # Restore state flags
        self.logic.enPassantSquare = move.get('en_passant_square')
        self.logic.whiteKingMoved = move.get('white_king_moved', False)
        self.logic.blackKingMoved = move.get('black_king_moved', False)
        self.logic.whiteRookMoved = move.get('white_rooks_moved', [False, False])
        self.logic.blackRookMoved = move.get('black_rooks_moved', [False, False])
        self.logic.turn = WHITE if move.get('turn') == 'WHITE' else PIECEBLACK

    def onNewGame(self):
        """Reset the board and gameplay state for a new game."""
        # Remove old pieces
        for p in self.logic.pieces:
            if p and hasattr(p, 'obj'):
                p.obj.removeNode()

        self.renderer.cleanup()
        self.logic = ChessLogic()
        self.renderer = GameRenderer(self)

        self.gameOver = False
        self.input_handler.reset()

        # Keep PvAI camera rotation rule consistent after reset
        self.rotateCameraEnabled = (self.mode != 'pvai')

        self.renderer.clear_highlights()
        self.ui.updateMoveHistoryDisplay(self.logic.moveNotation)
        self.renderer.update_camera_for_aspect()
        self.ui.setStatus("Turn: WHITE" if self.logic.turn == WHITE else "Turn: BLACK")
        
        # If Player vs AI mode and AI starts, schedule the first AI move
        self.app.taskMgr.remove('aiMoveTask')
        if self.mode == 'pvai' and ((self.playerColor == 0 and self.logic.turn == PIECEBLACK) or (self.playerColor == 1 and self.logic.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def movePiece(self, fr, to):
        """Visually animate a piece move while logic runs underneath."""
        move_record = self.logic.execute_move(fr, to)
        
        moving = move_record['moving_piece']
        target = move_record['captured_piece']

        if target:
            target.obj.removeNode()

        moving.obj.setPos(SquarePos(to))
        self.lastMove = (fr, to)

        if 'en_passant_capture' in move_record:
            victim = move_record['en_passant_victim']
            victim.obj.removeNode()
            
        if move_record['castling']:
            rook_to = move_record['rook_to']
            rook = self.logic.pieces[rook_to]
            rook.obj.setPos(SquarePos(rook_to))
            
        is_promotion = isinstance(moving, Pawn) and ((moving.color == WHITE and to // 8 == 7) or (moving.color == PIECEBLACK and to // 8 == 0))
        
        if not is_promotion:
            self.ui.updateMoveHistoryDisplay(self.logic.moveNotation)

            isCapture = target is not None or 'en_passant_capture' in move_record
            isCastle = move_record['castling']
            enemy = PIECEBLACK if moving.color == WHITE else WHITE
            inCheck = self.logic.is_king_in_check(enemy)

            self.renderer.play_move_sound(move_record, isCapture, isCastle, inCheck)

    def moveAndProcessTurn(self, fr, to):
        """Execute a move, handle promotion, checkmate, stalemate, and switch turns."""
        # Prevent direct king capture (legal move logic should avoid this scenario in real chess).
        if isinstance(self.logic.pieces[to], King):
            self.ui.setStatus("Illegal move: cannot capture king")
            self.renderer.illegalSound.play()
            return False

        self.movePiece(fr, to)

        # Check for pawn promotion
        piece = self.logic.pieces[to]
        if isinstance(piece, Pawn) and ((piece.color == WHITE and to // 8 == 7) or (piece.color == PIECEBLACK and to // 8 == 0)):
            self.ui.showPromotionDialog(to)
            return True

        self.postMoveChecks()
        return True

    def makeAIMove(self, task):
        """AI: uses Minimax algorithm to find the best move."""
        if self.gameOver:
            return Task.done

        # Map difficulty slider (1-5) to Minimax search depth (1-3 or 4)
        # Depth > 3 can be very slow in pure Python, so we clamp it to prevent freezing
        depth = min(4, max(1, int(self.difficulty)))
        
        best_move = get_best_move(self.logic, depth)
        
        if not best_move:
            # No moves available for AI; checkmate or stalemate
            ai_color = PIECEBLACK if self.playerColor == 0 else WHITE
            if self.logic.is_king_in_check(ai_color):
                self.ui.setStatus(f"CHECKMATE! {'WHITE' if self.playerColor == 1 else 'BLACK'} wins")
                self.gameOver = True
            else:
                self.ui.setStatus("STALEMATE. Draw")
                self.gameOver = True
            return Task.done

        fr, to = best_move
        self.movePiece(fr, to)

        piece = self.logic.pieces[to]
        if isinstance(piece, Pawn) and ((piece.color == WHITE and to // 8 == 7) or (piece.color == PIECEBLACK and to // 8 == 0)):
            self.executePromotion("Queen", to)
            return Task.done

        self.postMoveChecks()
        return Task.done

    def executePromotion(self, piece_type, square):
        """Execute the pawn promotion logic after user selects a piece."""
        if self.gameOver:
            return
            
        pawn = self.logic.pieces[square]
        if not isinstance(pawn, Pawn):
            return
            
        if piece_type == "Queen":
            new_piece = Queen(square, pawn.color, parent=self.renderer.piecesNode)
        elif piece_type == "Rook":
            new_piece = Rook(square, pawn.color, parent=self.renderer.piecesNode)
        elif piece_type == "Bishop":
            new_piece = Bishop(square, pawn.color, parent=self.renderer.piecesNode)
        elif piece_type == "Knight":
            new_piece = Knight(square, pawn.color, parent=self.renderer.piecesNode)
        else:
            return
            
        pawn.obj.removeNode()
        self.logic.complete_promotion(square, new_piece)
        self.ui.updateMoveHistoryDisplay(self.logic.moveNotation)
        self.renderer.promoteSound.play()
        self.postMoveChecks()

    def postMoveChecks(self):
        """Perform checks for checkmate/stalemate and switch turns."""
        enemy = PIECEBLACK if self.logic.turn == WHITE else WHITE
        enemy_in_check = self.logic.is_king_in_check(enemy)
        black_in_checkmate = self.logic.is_checkmate(PIECEBLACK)
        white_in_checkmate = self.logic.is_checkmate(WHITE)
        black_stalemate = self.logic.is_stalemate(PIECEBLACK)
        white_stalemate = self.logic.is_stalemate(WHITE)

        if black_in_checkmate or white_in_checkmate:
            self.gameOver = True
            winner = "WHITE" if black_in_checkmate else "BLACK"
            self.ui.setStatus(f"CHECKMATE! {winner} wins")
            self.renderer.clear_highlights()
        elif black_stalemate or white_stalemate:
            self.gameOver = True
            self.ui.setStatus("STALEMATE. Draw")
            self.renderer.clear_highlights()
        else:
            self.switchTurn()
            if enemy_in_check:
                self.ui.setStatus(f"Check to {'BLACK' if enemy == PIECEBLACK else 'WHITE'}")
            else:
                self.ui.setStatus(f"Turn: {'WHITE' if self.logic.turn == WHITE else 'BLACK'}")

            # AI should move immediately after promotion if it is AI's turn
            if self.mode == 'pvai' and ((self.playerColor == 0 and self.logic.turn == PIECEBLACK) or (self.playerColor == 1 and self.logic.turn == WHITE)):
                self.app.taskMgr.doMethodLater(0.5, self.makeAIMove, 'aiMoveTask')

    def switchTurn(self):
        """
        Switch to the other player's turn and rotate the camera.
        """
        self.logic.switch_turn()
        self.renderer.rotate_camera()
