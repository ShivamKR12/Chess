from panda3d.core import BitMask32, CollisionNode, CollisionRay, CollisionHandlerQueue, CollisionTraverser
from direct.task.Task import Task
from pieces import Pawn
from constants import PointAtZ, SquarePos, WHITE, PIECEBLACK, HIGHLIGHT, YELLOW

class InputHandler:
    def __init__(self, game):
        self.game = game
        self.app = game.app
        
        self.hiSq = False
        self.dragging = False
        self.selectedSquare = None
        self.validMoves = []
        
        self.setupPicking()
        
        self.app.taskMgr.add(self.mouseTask, "mouseTask")
        self.game.accept("mouse1", self.grabPiece)
        self.game.accept("mouse1-up", self.releasePiece)

    def cleanup(self):
        self.app.taskMgr.remove("mouseTask")
        self.game.ignore("mouse1")
        self.game.ignore("mouse1-up")
        if hasattr(self, 'pickerNP'):
            self.pickerNP.removeNode()

    def reset(self):
        self.hiSq = False
        self.dragging = False
        self.selectedSquare = None
        self.validMoves = []

    def setupPicking(self):
        self.picker = CollisionTraverser()
        self.pq = CollisionHandlerQueue()
        self.pickerNode = CollisionNode('mouseRay')
        self.pickerNP = self.app.camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))
        self.pickerRay = CollisionRay()
        self.pickerNode.addSolid(self.pickerRay)
        self.picker.addCollider(self.pickerNP, self.pq)

    def mouseTask(self, task):
        if self.app.mouseWatcherNode.hasMouse():
            mpos = self.app.mouseWatcherNode.getMouse()

            if hasattr(self.game, 'dr'):
                l, r, b, t = self.game.dr.getDimensions()
            else:
                l, r, b, t = 0.0, 1.0, 0.0, 1.0
                
            win_x = (mpos.getX() + 1.0) / 2.0
            win_y = (mpos.getY() + 1.0) / 2.0
            
            if l <= win_x <= r and b <= win_y <= t:
                dr_x = ((win_x - l) / (r - l)) * 2.0 - 1.0
                dr_y = ((win_y - b) / (t - b)) * 2.0 - 1.0
                
                self.pickerRay.setFromLens(self.app.camNode, dr_x, dr_y)
    
                if self.dragging is not False:
                    nearPoint = self.app.render.getRelativePoint(self.app.camera, self.pickerRay.getOrigin())
                    nearVec = self.app.render.getRelativeVector(self.app.camera, self.pickerRay.getDirection())
                    self.game.logic.pieces[self.dragging].obj.setPos(PointAtZ(.5, nearPoint, nearVec))
    
                self.picker.traverse(self.game.renderer.squareRoot)
    
                if self.pq.getNumEntries() > 0:
                    self.pq.sortEntries()
                    self.hiSq = int(self.pq.getEntry(0).getIntoNode().getTag('square'))
                else:
                    self.hiSq = False
            else:
                self.hiSq = False

        if self.dragging is False and not self.game.gameOver:
            self.game.renderer.clear_highlights()
            
            if self.selectedSquare is not None:
                self.game.renderer.squares[self.selectedSquare].setColor(YELLOW)
                self.game.renderer.highlight_moves()
                
            if self.hiSq is not False:
                self.game.renderer.squares[self.hiSq].setColor(HIGHLIGHT)

        return Task.cont

    def grabPiece(self):
        if self.game.gameOver:
            return

        if self.game.mode == 'pvai':
            local_player_color = WHITE if self.game.playerColor == 0 else PIECEBLACK
            if self.game.logic.turn != local_player_color:
                return

        if self.selectedSquare is not None and self.hiSq is not False and self.hiSq in self.validMoves:
            success = self.game.moveAndProcessTurn(self.selectedSquare, self.hiSq)
            if not success:
                if self.game.logic.pieces[self.selectedSquare] and self.game.logic.pieces[self.selectedSquare].obj:
                    self.game.logic.pieces[self.selectedSquare].obj.setPos(SquarePos(self.selectedSquare))
            
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.game.renderer.clear_highlights()
            return

        if self.hiSq is not False and self.game.logic.pieces[self.hiSq]:
            piece = self.game.logic.pieces[self.hiSq]
            if piece.color == self.game.logic.turn:
                self.game.renderer.clear_highlights()
                self.selectedSquare = self.hiSq
                self.dragging = self.hiSq
                self.validMoves = self.game.logic.get_legal_moves(self.hiSq)
                self.game.renderer.squares[self.selectedSquare].setColor(YELLOW)
                self.game.renderer.highlight_moves()
                return

        if self.selectedSquare is not None:
            self.game.ui.setStatus("Invalid move")
            self.game.renderer.illegalSound.play()
            if self.game.logic.pieces[self.selectedSquare] and self.game.logic.pieces[self.selectedSquare].obj:
                self.game.logic.pieces[self.selectedSquare].obj.setPos(SquarePos(self.selectedSquare))
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.game.renderer.clear_highlights()

    def releasePiece(self):
        if self.dragging is False or self.game.gameOver:
            self.dragging = False
            return

        piece = self.game.logic.pieces[self.dragging]

        if self.hiSq == self.dragging:
            piece.obj.setPos(SquarePos(self.dragging))
            self.dragging = False
            return

        if self.hiSq is not False and self.hiSq in self.validMoves:
            success = self.game.moveAndProcessTurn(self.dragging, self.hiSq)
            if not success:
                piece.obj.setPos(SquarePos(self.dragging))
            
            self.selectedSquare = None
            self.dragging = False
            self.validMoves = []
            self.game.renderer.clear_highlights()
            return

        self.game.ui.setStatus("Invalid move")
        self.game.renderer.illegalSound.play()
        piece.obj.setPos(SquarePos(self.dragging))
        self.selectedSquare = None
        self.dragging = False
        self.validMoves = []
        self.game.renderer.clear_highlights()