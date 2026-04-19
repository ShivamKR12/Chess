import json
import os
from datetime import datetime
from tkinter import Tk, filedialog
from panda3d.core import BitMask32

from pieces import Pawn, Knight, Bishop, Rook, Queen, King
from constants import WHITE, PIECEBLACK, SquarePos

class SaveManager:
    def __init__(self, game):
        self.game = game
        self.app = game.app

    def save_game(self):
        """Save the current game state to a JSON file."""
        if self.game.gameOver:
            self.game.ui.setStatus("Cannot save - game is over")
            return
        
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            root = Tk()
            root.withdraw()
            filepath = filedialog.asksaveasfilename(
                initialdir=saves_dir,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"chess_{self.game.mode}_{timestamp}.json"
            )
            root.destroy()
        except Exception as e:
            self.game.ui.setStatus(f"Save error: {str(e)}")
            return
        
        if not filepath:
            return
        
        game_state = self.serialize_game_state()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(game_state, f, indent=2)
            self.game.ui.setStatus(f"Game saved to {os.path.basename(filepath)}")
        except Exception as e:
            self.game.ui.setStatus(f"Failed to save: {str(e)}")

    def load_game(self):
        """Load a saved game state from a JSON file."""
        try:
            root = Tk()
            root.withdraw()
            filepath = filedialog.askopenfilename(
                initialdir="saves",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            self.game.ui.setStatus(f"Load error: {str(e)}")
            return
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r') as f:
                game_state = json.load(f)
            
            saved_mode = game_state.get('mode', 'pvp')
            if saved_mode != self.game.mode:
                self.game.ui.setStatus(f"Error: Cannot load {saved_mode.upper()} save in {self.game.mode.upper()} mode")
                return
            
            self.deserialize_game_state(game_state)
            self.game.ui.setStatus(f"Game loaded from {os.path.basename(filepath)}")
        except Exception as e:
            self.game.ui.setStatus(f"Failed to load: {str(e)}")

    def serialize_game_state(self):
        """Serialize the current game state to a JSON-compatible dictionary."""
        board_state = []
        for i, piece in enumerate(self.game.logic.pieces):
            if piece:
                piece_data = {
                    'square': i,
                    'type': piece.__class__.__name__,
                    'color': 'WHITE' if piece.color == WHITE else 'BLACK'
                }
                board_state.append(piece_data)
        
        game_state = {
            'board': board_state,
            'turn': 'WHITE' if self.game.logic.turn == WHITE else 'BLACK',
            'enPassantSquare': self.game.logic.enPassantSquare,
            'whiteKingMoved': self.game.logic.whiteKingMoved,
            'blackKingMoved': self.game.logic.blackKingMoved,
            'whiteRookMoved': self.game.logic.whiteRookMoved,
            'blackRookMoved': self.game.logic.blackRookMoved,
            'moveHistory': self._serialize_move_history(),
            'moveNotation': self.game.logic.moveNotation,
            'timestamp': datetime.now().isoformat(),
            'mode': self.game.mode,
            'playerColor': self.game.playerColor,
            'difficulty': self.game.difficulty
        }
        return game_state

    def _serialize_move_history(self):
        """Serialize move history for saving."""
        serialized = []
        for move in self.game.logic.moveHistory:
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
            if move.get('en_passant_capture'):
                move_data['en_passant_victim_color'] = 'WHITE' if move['en_passant_victim'].color == WHITE else 'BLACK'

            serialized.append(move_data)
        return serialized

    def create_piece_from_type(self, piece_type, color, square):
        piece_classes = {
            'Pawn': Pawn, 'Knight': Knight, 'Bishop': Bishop,
            'Rook': Rook, 'Queen': Queen, 'King': King
        }
        cls = piece_classes.get(piece_type, Pawn)
        color_value = WHITE if color == 'WHITE' else PIECEBLACK
        return cls(square, color_value, parent=self.game.renderer.piecesNode)

    def deserialize_game_state(self, game_state):
        """Restore game state from a serialized dictionary."""
        for p in self.game.logic.pieces:
            if p and hasattr(p, 'obj'):
                p.obj.removeNode()
        
        self.game.logic.pieces = [None] * 64
        self.game.renderer.squareRoot.removeNode()
        self.game.renderer.piecesNode.removeNode()
        self.game.renderer.squareRoot = self.app.render.attachNewNode("squareRoot")
        self.game.renderer.piecesNode = self.app.render.attachNewNode("piecesNode")
        
        # Re-apply post-processing shaders to the newly built nodes!
        if self.app.settings_mgr.get('graphics', 'high') != 'off':
            self.game.renderer.squareRoot.setShaderAuto()
            self.game.renderer.piecesNode.setShaderAuto()
        
        piece_classes = {
            'Pawn': Pawn, 'Knight': Knight, 'Bishop': Bishop,
            'Rook': Rook, 'Queen': Queen, 'King': King
        }
        
        for piece_data in game_state['board']:
            square = piece_data['square']
            piece_type = piece_classes[piece_data['type']]
            color = WHITE if piece_data['color'] == 'WHITE' else PIECEBLACK
            self.game.logic.pieces[square] = piece_type(square, color, parent=self.game.renderer.piecesNode)
        
        self.game.logic.turn = WHITE if game_state['turn'] == 'WHITE' else PIECEBLACK
        self.game.logic.enPassantSquare = game_state['enPassantSquare']
        self.game.logic.whiteKingMoved = game_state['whiteKingMoved']
        self.game.logic.blackKingMoved = game_state['blackKingMoved']
        self.game.logic.whiteRookMoved = game_state['whiteRookMoved']
        self.game.logic.blackRookMoved = game_state['blackRookMoved']
        self.game.logic.moveNotation = game_state.get('moveNotation', [])
        self.game.gameOver = False

        if 'mode' in game_state:
            self.game.mode = game_state['mode']
        if 'playerColor' in game_state:
            self.game.playerColor = game_state['playerColor']
        if 'difficulty' in game_state:
            self.game.difficulty = game_state['difficulty']
        self.game.rotateCameraEnabled = (self.game.mode != 'pvai')

        # Restore move history (safe to just read directly since it's raw JSON)
        saved_history = game_state.get('moveHistory', [])
        self.game.logic.moveHistory = [dict(entry) for entry in saved_history] if saved_history else []

        for i in range(64):
            sq = self.app.loader.loadModel("models/square")
            sq.reparentTo(self.game.renderer.squareRoot)
            sq.setPos(SquarePos(i))
            sq.setColor(self.game.renderer.get_square_color(i))
            sq.find("**/polygon").node().setIntoCollideMask(BitMask32.bit(1))
            sq.find("**/polygon").node().setTag('square', str(i))
            self.game.renderer.squares[i] = sq
        
        self.game.ui.updateMoveHistoryDisplay(self.game.logic.moveNotation)
        self.game.ui.setStatus(f"Turn: {'WHITE' if self.game.logic.turn == WHITE else 'BLACK'}")
        self.game.renderer.clear_highlights()

        if hasattr(self.game.renderer, 'orbit') and self.game.renderer.orbit.isPlaying():
            self.game.renderer.orbit.pause()
            
        if self.game.mode == 'pvp':
            if self.game.logic.turn == WHITE:
                self.game.renderer.camPivot.setHpr(0, 0, 0)
            else:
                self.game.renderer.camPivot.setHpr(180, 0, 0)
        else:
            if self.game.playerColor == 1:
                self.game.renderer.camPivot.setHpr(180, 0, 0)
            else:
                self.game.renderer.camPivot.setHpr(0, 0, 0)

        self.app.taskMgr.remove('aiMoveTask')
        if self.game.mode == 'pvai' and ((self.game.playerColor == 0 and self.game.logic.turn == PIECEBLACK) or (self.game.playerColor == 1 and self.game.logic.turn == WHITE)):
            self.app.taskMgr.doMethodLater(0.5, self.game.makeAIMove, 'aiMoveTask')