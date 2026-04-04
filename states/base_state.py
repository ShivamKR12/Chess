from direct.showbase.DirectObject import DirectObject


class AppState(DirectObject):
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
        super().__init__()
        self.app = app
    
    def cleanup(self):
        """
        Clean up this state's resources and UI elements.
        Should be overridden by subclasses.
        """
        self.ignoreAll()
        pass
