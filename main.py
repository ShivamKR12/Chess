from direct.showbase.ShowBase import ShowBase
from panda3d.core import AntialiasAttrib, WindowProperties, load_prc_file_data

from settings import SettingsManager
from states.menu import MenuState
from states.game import ChessGame
from states.settings import SettingsState


class ChessApp(ShowBase):
    """
    Main application class that manages the overall game flow and state transitions.
    """
    
    def __init__(self):
        """
        Initialize the chess application.
        """
        # Enable MSAA anti-aliasing for smoother edges (default 4x)
        load_prc_file_data('', 'framebuffer-multisample true\nmultisamples 4\n')

        ShowBase.__init__(self)
        self.render.setAntialias(AntialiasAttrib.MMultisample)

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
        
        # Initialize settings manager
        self.settings_mgr = SettingsManager()
        self.settings_mgr.apply(self)
        
        # Initialize state management
        self.currentState = None
        
        # Start with the menu
        self.showMenu()
    
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
        self.currentState = MenuState(self)
    
    def showSettings(self):
        """
        Switch to the settings state.
        """
        if self.currentState:
            self.currentState.cleanup()
        self.currentState = SettingsState(self)
    
    def startGame(self, mode="pvp", playerColor=0, difficulty=None):
        """
        Start a new chess game.
        
        Parameters:
        - mode: Game mode ("pvp" or "pvai")
        - playerColor: Player's color (0 = white, 1 = black)
        - difficulty: AI difficulty level (1-5) from settings
        """
        if difficulty is None:
            difficulty = self.settings_mgr.get('difficulty', 1)
        if self.currentState:
            self.currentState.cleanup()
        self.currentState = ChessGame(self, mode, playerColor, difficulty)


# Create and run the chess application
if __name__ == "__main__":
    app = ChessApp()
    app.run()
