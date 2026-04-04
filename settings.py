import json
import os
from panda3d.core import loadPrcFileData, WindowProperties, AudioManager
from direct.showbase.ShowBase import ShowBase  # For type hints

class SettingsManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config_path = 'config.json'
        self.defaults = {
            'sfx_volume': 1.0,
            'graphics': 'high',  # 'off', 'low', 'high'
            'difficulty': 1,  # 1-5
            'fov': 45.0,
            'fullscreen': False,
            'board_theme': 'classic'
        }
        self.settings = self.load()
    
    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults for missing keys
                    for key, default in self.defaults.items():
                        if key not in loaded:
                            loaded[key] = default
                    return loaded
            except (IOError, json.JSONDecodeError):
                pass  # Fallback to defaults
        return self.defaults.copy()
    
    def save(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def update(self, key, value):
        """Updates a setting in memory. Does not save automatically."""
        self.settings[key] = value
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def apply(self, app: ShowBase = None):
        # Audio: Set global SFX volume
        if app and app.sfxManagerList:
            app.sfxManagerList[0].setVolume(self.get('sfx_volume', 1.0))
        
        # Graphics MSAA via PRC (runtime effect on new render targets)
        msaa_map = {'off': 0, 'low': 2, 'high': 4}
        msaa = msaa_map.get(self.get('graphics', 'high'), 4)
        loadPrcFileData('', f'framebuffer-multisample true\nmultisamples {msaa}\n')
        
        # FOV
        if app and app.cam and app.cam.node().getLens():
            app.cam.node().getLens().setFov(self.get('fov', 45.0))
        
        # Fullscreen
        if app and app.win:
            props = WindowProperties()
            props.setFullscreen(self.get('fullscreen', False))
            app.win.requestProperties(props)
        
        # Board theme must be applied in the game state by reloading board colors.
        # The game state would need a method to listen for this setting change.
