from direct.showbase.ShowBase import ShowBase
from panda3d.core import AntialiasAttrib, WindowProperties, load_prc_file_data
from panda3d.core import AmbientLight, DirectionalLight, LVector3, Material

from settings import SettingsManager
from states.menu import MenuState
from states.game import ChessGame
from states.settings import SettingsState
from constants import SquarePos, SquareColor


class ChessApp(ShowBase):
    """
    Main application class that manages the overall game flow and state transitions.
    """
    
    def __init__(self):
        """
        Initialize the chess application.
        """
        # ( NOT FOR NOW ! ) # Enable MSAA anti-aliasing for smoother edges (default 4x)
        # load_prc_file_data('', 'framebuffer-multisample true\nmultisamples 4\n')

        ShowBase.__init__(self)
        
        # Disable Panda3D's default mouse camera controls globally so we can control the camera manually
        self.disableMouse()
        
        # ( NOT FOR NOW ! ) # self.render.setAntialias(AntialiasAttrib.MMultisample)

        # Use a vertical FOV baseline and allow width to show more scene instead of stretching
        self.cam.node().getLens().setFov(45)
        self.cam.node().getLens().setNearFar(0.1, 1000)

        # Cache state for game mode transitions and consistent UI layout
        props = WindowProperties()
        props.setTitle("Chess Game")
        props.setIconFilename("panda3d-logo.ico")
        base.win.requestProperties(props) # type: ignore
        
        # Set up the persistent skydome background for the entire app
        self.setupSkydome()
        self.setupMenuBackground()
        
        # Initialize settings manager
        self.settings_mgr = SettingsManager()
        self.settings_mgr.apply(self)
        
        # Initialize state management
        self.currentState = None
        
        # Start with the menu
        self.showMenu()

    def setupMenuBackground(self):
        """Set up a rotating chessboard for the background of non-game screens."""
        self.menuBgRoot = self.render.attachNewNode("menuBgRoot")
        self.menuBgRoot.setPos(0, 0, 0)
        
        # Lights for menu
        self.menuLightRoot = self.menuBgRoot.attachNewNode("menuLights")
        ambient = AmbientLight("menu_ambient")
        ambient.setColor((0.4, 0.4, 0.4, 1))
        self.menuBgRoot.setLight(self.menuLightRoot.attachNewNode(ambient))
        
        dlight = DirectionalLight("menu_dir")
        dlight.setDirection(LVector3(-1, -1, -1))
        dlight.setColor((0.8, 0.8, 0.8, 1))
        self.menuBgRoot.setLight(self.menuLightRoot.attachNewNode(dlight))
        
        self.menuBgRoot.setShaderAuto()
        
        for i in range(64):
            sq = self.loader.loadModel("models/square")
            sq.reparentTo(self.menuBgRoot)
            sq.setPos(SquarePos(i))
            sq.setColor(SquareColor(i))
            
        piece_models = [
            "models/rook", "models/knight", "models/bishop", "models/queen",
            "models/king", "models/bishop", "models/knight", "models/rook"
        ]
        
        pieces = []
        for i in range(8):
            pieces.append((piece_models[i], i, (1, 1, 1, 1)))           # White back rank
            pieces.append(("models/pawn", i + 8, (1, 1, 1, 1)))         # White pawns
            pieces.append(("models/pawn", i + 48, (.15, .15, .15, 1)))  # Black pawns
            pieces.append((piece_models[i], i + 56, (.15, .15, .15, 1)))# Black back rank
            
        mat = Material()
        mat.setShininess(30.0)
        mat.setSpecular((0.6, 0.6, 0.6, 1))
        
        for model_path, sq_idx, color in pieces:
            p = self.loader.loadModel(model_path)
            p.reparentTo(self.menuBgRoot)
            p.setPos(SquarePos(sq_idx))
            p.setColor(color)
            p.setMaterial(mat, 1)

        self.bgRotation = self.menuBgRoot.hprInterval(40, (360, 0, 0))
        self.bgRotation.loop()
        self.menuBgRoot.hide()
    
    def setupSkydome(self):
        """
        Set up the skydome background for the 3D scene (persistent across states).
        """
        # Load the skydome model
        self.skydome = self.loader.loadModel("models/cloudy_midday_4k_skydome.bam")
        
        # Scale it up significantly (user mentioned default scale is only 1)
        self.skydome.setScale(50)  # Much larger scale for background
        
        # Position it at the center of the scene
        self.skydome.setPos(0, 0, 0)
        
        # Make sure it's behind everything else (negative Z or far away)
        self.skydome.setBin("background", 1)  # Render as background
        self.skydome.setDepthWrite(False)     # Don't write to depth buffer
        self.skydome.setDepthTest(False)      # Don't test depth
        
        # Reparent to render
        self.skydome.reparentTo(self.render)
    
    def showMenu(self):
        """
        Switch to the main menu state.
        """
        if self.currentState:
            self.currentState.cleanup()
        if hasattr(self, 'menuBgRoot'):
            self.menuBgRoot.show()
            # Apply transforms to the parent camera, and reset the inner cam to avoid stacking pitch
            self.camera.reparentTo(self.render)
            self.camera.setPos(0, -14, 10)
            self.camera.lookAt(0, 0, 0)
            self.cam.setPosHpr(0, 0, 0, 0, 0, 0)
        self.currentState = MenuState(self)
    
    def showSettings(self):
        """
        Switch to the settings state.
        """
        if self.currentState:
            self.currentState.cleanup()
        if hasattr(self, 'menuBgRoot'):
            self.menuBgRoot.show()
            self.camera.reparentTo(self.render)
            self.camera.setPos(0, -14, 10)
            self.camera.lookAt(0, 0, 0)
            self.cam.setPosHpr(0, 0, 0, 0, 0, 0)
        self.currentState = SettingsState(self)
    
    def startGame(self, mode="pvp", playerColor=0, difficulty=None):
        """
        Start a new chess game.
        
        Parameters:
        - mode: Game mode ("pvp" or "pvai")
        - playerColor: Player's color (0 = white, 1 = black)
        - difficulty: AI difficulty level (1-5) from settings
        """
        if hasattr(self, 'menuBgRoot'):
            self.menuBgRoot.hide()
        if difficulty is None:
            difficulty = self.settings_mgr.get('difficulty', 1)
        if self.currentState:
            self.currentState.cleanup()
            
        # Reset camera to world root before starting game to avoid inheriting menu pitch
        self.camera.reparentTo(self.render)
        self.camera.setPosHpr(0, 0, 0, 0, 0, 0)
        self.cam.setPosHpr(0, 0, 0, 0, 0, 0)
        
        self.currentState = ChessGame(self, mode, playerColor, difficulty)


# Create and run the chess application
if __name__ == "__main__":
    app = ChessApp()
    app.run()
