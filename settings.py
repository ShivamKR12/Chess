import json
import os
from panda3d.core import loadPrcFileData, WindowProperties, AudioManager
from direct.showbase.ShowBase import ShowBase  # For type hints
from direct.filter.CommonFilters import CommonFilters

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
            'board_theme': 'classic',
            'bloom': False,
            'blur': False,
            'hdr': False
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
        
        # Update the live-preview board floating in the menu background
        if app and hasattr(app, 'updateMenuBoardTheme'):
            app.updateMenuBoardTheme()
        
        # Apply advanced shaders via CommonFilters
        if app and app.win:
            if not hasattr(self, 'filters'):
                self.filters = CommonFilters(app.win, app.cam)
            
            # Clear existing filters to prevent stacking when toggling options
            self.filters.delBloom()
            self.filters.delBlurSharpen()
            self.filters.delHighDynamicRange()
            # Force a complete rebuild of the post-processing pipeline
            # to avoid stacking custom passes and ensure clean state
            self.filters.cleanup()
            self.filters.configuration.clear()
            
            # Apply MSAA directly to the post-processing render buffer
            if msaa > 0:
                self.filters.setMSAA(msaa)
            else:
                self.filters.delMSAA()
            
            if self.get('bloom', False):
                # Standard blend, triggering only on bright pixels (mintrigger=0.6), mild desaturation
                self.filters.setBloom(blend=(0.3, 0.4, 0.3, 0.0), desat=0.5, intensity=0.8, mintrigger=0.6, maxtrigger=1.0, size="medium")
            if self.get('blur', False):
                # amount=1.0 is no effect. >1.0 sharpens. <1.0 blurs. 
                # We use 1.2 to slightly sharpen the image rather than making the whole screen blurry.
                self.filters.setBlurSharpen(amount=2.0)
            if self.get('hdr', False):
                self.filters.setHighDynamicRange()
