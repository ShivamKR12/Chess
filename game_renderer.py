from panda3d.core import BitMask32, Material, LVector3, AmbientLight, DirectionalLight
from direct.interval.LerpInterval import LerpHprInterval
from constants import WHITE, PIECEBLACK, SquarePos, SquareColor
from pieces import Pawn, Rook, Knight, Bishop, Queen, King

class GameRenderer:
    """
    Handles all 3D visuals, lighting, camera animations, and sound effects.
    """
    def __init__(self, game):
        self.game = game
        self.app = game.app
        self.logic = game.logic

        # Create a pivot node for camera rotation during turn changes.
        self.camPivot = self.app.render.attachNewNode("camPivot")
        self.camPivot.setPos(0, 0, 0)
        self.piecesNode = self.app.render.attachNewNode("piecesNode")

        # Position the camera above and behind the board, looking at the center.
        self.app.camera.reparentTo(self.camPivot)
        self.app.camera.setPos(0, -14, 10)
        self.app.camera.lookAt(0, 0, 0)

        if self.game.mode == 'pvp':
            self.camPivot.setH(0)
        elif self.game.playerColor == 1:
            self.camPivot.setH(180)

        self.sfx_volume = self.app.settings_mgr.get('sfx_volume', 1.0)
        self.load_sounds()
        
        self.squares = [None] * 64
        self.setup_lights()
        self.setup_board()
        
        self.game.accept('aspectRatioChanged', self.update_camera_for_aspect)

    def load_sounds(self):
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
        self.illegalSound = self.app.loader.loadSfx("sounds/illegal.mp3")
        self.illegalSound.setVolume(self.sfx_volume)

    def get_square_color(self, i):
        theme = self.app.settings_mgr.get('board_theme', 'classic')
        is_dark = (i + ((i // 8) % 2)) % 2 != 0
        if theme == 'wood':
            return (0.34, 0.2, 0.09, 1) if is_dark else (0.82, 0.7, 0.53, 1)
        elif theme == 'marble':
            return (0.25, 0.35, 0.35, 1) if is_dark else (0.85, 0.85, 0.9, 1)
        elif theme == 'dark':
            return (0.15, 0.15, 0.18, 1) if is_dark else (0.45, 0.45, 0.5, 1)
        return SquareColor(i)

    def setup_board(self):
        self.squareRoot = self.app.render.attachNewNode("squareRoot")
        for i in range(64):
            sq = self.app.loader.loadModel("models/square")
            sq.reparentTo(self.squareRoot)
            sq.setPos(SquarePos(i))
            sq.setColor(self.get_square_color(i))
            sq.find("**/polygon").node().setIntoCollideMask(BitMask32.bit(1))
            sq.find("**/polygon").node().setTag('square', str(i))
            self.squares[i] = sq

        pieceOrder = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)

        for i in range(8, 16):
            self.logic.pieces[i] = Pawn(i, WHITE, parent=self.piecesNode)
        for i in range(48, 56):
            self.logic.pieces[i] = Pawn(i, PIECEBLACK, parent=self.piecesNode)
        for i in range(8):
            self.logic.pieces[i] = pieceOrder[i](i, WHITE, parent=self.piecesNode)
        for i in range(8):
            self.logic.pieces[i + 56] = pieceOrder[i](i + 56, PIECEBLACK, parent=self.piecesNode)

    def apply_piece_material(self, piece):
        if not piece or not hasattr(piece, 'obj') or not piece.obj: return
        mat = Material()
        mat.setShininess(30.0)
        mat.setSpecular((0.6, 0.6, 0.6, 1))
        piece.obj.setMaterial(mat, 1)
        piece.obj.setShaderAuto()

    def highlight_moves(self):
        if self.game.input_handler.selectedSquare is None: return
        for m in self.game.input_handler.validMoves:
            piece = self.logic.pieces[self.game.input_handler.selectedSquare]
            if self.logic.pieces[m]:
                self.squares[m].setColor((1, 0, 0, 1))
            elif isinstance(piece, Pawn) and m == self.logic.enPassantSquare:
                self.squares[m].setColor((1, 0, 0, 1))
            else:
                self.squares[m].setColor((0, 1, 0, 1))

    def clear_highlights(self):
        for i in range(64):
            self.squares[i].setColor(self.get_square_color(i))
        if not self.game.gameOver:
            if self.logic.is_king_in_check(WHITE):
                for i, p in enumerate(self.logic.pieces):
                    if isinstance(p, King) and p.color == WHITE:
                        self.squares[i].setColor((1, 0, 0, 1))
            elif self.logic.is_king_in_check(PIECEBLACK):
                for i, p in enumerate(self.logic.pieces):
                    if isinstance(p, King) and p.color == PIECEBLACK:
                        self.squares[i].setColor((1, 0, 0, 1))

    def rotate_camera(self, instant=False):
        if not getattr(self.game, 'rotateCameraEnabled', False): return
        if instant:
            self.camPivot.setH(self.camPivot.getH() - 180)
        else:
            if hasattr(self, 'orbit') and self.orbit.isPlaying(): self.orbit.finish()
            self.orbit = LerpHprInterval(self.camPivot, 1.2, (self.camPivot.getH() - 180, 0, 0), blendType="easeInOut")
            self.orbit.start()

    def update_camera_for_aspect(self):
        if not self.app or not self.app.win: return
        w, h = self.app.win.getXSize(), self.app.win.getYSize()
        if h <= 0: return
        if hasattr(self.game, 'ui'): self.game.ui.updateAspect(w / float(h))
        if hasattr(self.game, 'dr'):
            l, r, b, t = self.game.dr.getDimensions()
            w, h = w * (r - l), h * (t - b)
        self.app.cam.node().getLens().setFov(self.app.settings_mgr.get('fov', 45.0))
        self.app.cam.node().getLens().setAspectRatio(w / float(h))

    def setup_lights(self):
        graphics = self.app.settings_mgr.get('graphics', 'high')
        if graphics != 'off':
            self.app.render.setShaderAuto()
            if hasattr(self, 'piecesNode'): self.piecesNode.setShaderAuto()
            if hasattr(self, 'squareRoot'): self.squareRoot.setShaderAuto()
        
        ambient = AmbientLight("ambient")
        ambient.setColor((0.35, 0.35, 0.35, 1))
        self.ambientLightNode = self.app.render.attachNewNode(ambient)
        self.app.render.setLight(self.ambientLightNode)
        
        if graphics == 'high':
            dir_light = DirectionalLight("main_dir")
            dir_light.setDirection(LVector3(-1, -1, -2))
            dir_light.setColor((0.9, 0.9, 0.9, 1))
            dir_light.setShadowCaster(True, 2048, 2048)
            dir_light.getLens().setNearFar(5, 100)
            self.mainDirectionalLightNode = self.app.render.attachNewNode(dir_light)
            self.app.render.setLight(self.mainDirectionalLightNode)
            
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
            dir_light = DirectionalLight("dir")
            dir_light.setDirection(LVector3(-1, -1, -1))
            dir_light.setColor((0.8, 0.8, 0.8, 1))
            self.mainDirectionalLightNode = self.app.render.attachNewNode(dir_light)
            self.app.render.setLight(self.mainDirectionalLightNode)
            
        self.app.setBackgroundColor(0.08, 0.1, 0.12, 1)

    def play_move_sound(self, move_record, isCapture, isCastle, inCheck):
        if move_record['promotion']: self.promoteSound.play()
        elif isCastle: self.castleSound.play()
        elif isCapture: self.captureSound.play()
        elif inCheck: self.moveCheckSound.play()
        else: self.moveSelfSound.play()

    def cleanup(self):
        if hasattr(self, 'orbit') and self.orbit.isPlaying():
            self.orbit.pause()

        if hasattr(self, 'piecesNode'): self.piecesNode.removeNode()
        if hasattr(self, 'squareRoot'): self.squareRoot.removeNode()
        if hasattr(self, 'camPivot'):
            self.app.camera.reparentTo(self.app.render)
            self.camPivot.removeNode()
        for light_attr in ['ambientLightNode', 'mainDirectionalLightNode', 'fillDirectionalLightNode', 'backDirectionalLightNode']:
            if hasattr(self, light_attr):
                node = getattr(self, light_attr)
                self.app.render.clearLight(node)
                node.removeNode()