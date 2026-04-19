import sys
import os
import json
from tkinter import Tk, filedialog
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel

from states.base_state import AppState


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
            frameColor=(0, 0, 0, 0),  # Transparent background
            pos=(0, 0, 0.4)
        )
        
        # Add game mode buttons
        self.pvpButton = DirectButton(
            parent=self.menuFrame,
            text="Player vs Player",
            text_pos=(0, -0.01),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.3, 0.3, -0.05, 0.05),
            pos=(0, 0, 0.25),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.startPvP
        )
        
        self.pvaiButton = DirectButton(
            parent=self.menuFrame,
            text="Player vs AI",
            text_pos=(0, -0.01),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.3, 0.3, -0.05, 0.05),
            pos=(0, 0, 0.1),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.startPvAI
        )
        
        # Add load game button
        self.loadButton = DirectButton(
            parent=self.menuFrame,
            text="Load Game",
            text_pos=(0, -0.01),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.6, 0.8, 1),
            frameSize=(-0.3, 0.3, -0.05, 0.05),
            pos=(0, 0, -0.05),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.loadGame
        )
        
        # Add color selection buttons
        self.whiteButton = DirectButton(
            parent=self.menuFrame,
            text="Play as White",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(0, 0, 0, 1),
            frameColor=(0.9, 0.9, 0.9, 1) if self.selectedColor == 0 else (0.7, 0.7, 0.7, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(-0.3, 0, -0.2),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.selectColor, extraArgs=[0]
        )
        
        self.blackButton = DirectButton(
            parent=self.menuFrame,
            text="Play as Black",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.2, 1) if self.selectedColor == 1 else (0.4, 0.4, 0.4, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(0.3, 0, -0.2),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.selectColor, extraArgs=[1]
        )
        
        # Add settings button
        self.settingsButton = DirectButton(
            parent=self.menuFrame,
            text="Settings",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.5, 0.5, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(0, 0, -0.35),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.showSettings
        )
        
        # Add exit button
        self.exitButton = DirectButton(
            parent=self.menuFrame,
            text="Exit",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0, 0, -0.48),
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
        self.app.startGame(mode="pvai", playerColor=self.selectedColor)
        
    def loadGame(self):
        """Prompt user for a save file and load it directly from the menu."""
        try:
            root = Tk()
            root.withdraw()
            filepath = filedialog.askopenfilename(
                initialdir="saves",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            print(f"Load error: {str(e)}")
            return
            
        if not filepath:
            return
            
        try:
            with open(filepath, 'r') as f:
                game_state = json.load(f)
                
            # Initialize the corresponding game state
            self.app.startGame(mode=game_state.get('mode', 'pvp'), playerColor=game_state.get('playerColor', 0), difficulty=game_state.get('difficulty', 1))
            
            self.app.currentState.loadGameState(game_state)
            self.app.currentState.setStatus(f"Game loaded from {os.path.basename(filepath)}")
        except Exception as e:
            print(f"Failed to load game: {str(e)}")
    
    def showSettings(self):
        """Show settings menu."""
        self.app.showSettings()
    
    def cleanup(self):
        """Clean up menu UI elements."""
        super().cleanup()
        if hasattr(self, 'titleLabel'):
            self.titleLabel.destroy()
        if hasattr(self, 'pvpButton'):
            self.pvpButton.destroy()
        if hasattr(self, 'pvaiButton'):
            self.pvaiButton.destroy()
        if hasattr(self, 'loadButton'):
            self.loadButton.destroy()
        if hasattr(self, 'whiteButton'):
            self.whiteButton.destroy()
        if hasattr(self, 'blackButton'):
            self.blackButton.destroy()
        if hasattr(self, 'settingsButton'):
            self.settingsButton.destroy()
        if hasattr(self, 'exitButton'):
            self.exitButton.destroy()
        if hasattr(self, 'menuFrame'):
            self.menuFrame.destroy()
