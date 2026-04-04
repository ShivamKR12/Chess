import json
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectSlider
)
from states.base_state import AppState

class SettingsState(AppState):
    def __init__(self, app):
        super().__init__(app)
        self.settings_mgr = app.settings_mgr
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame like menu
        self.frame = DirectFrame(
            frameColor=(0.2, 0.4, 0.6, 0.9),  # Semi-transparent blue background
            frameSize=(-0.8, 0.8, -0.6, 0.6),  # Centered, reasonably sized
            pos=(0, 0, 0),
            relief='groove',
            borderWidth=(0.02, 0.02)
        )
        
        # Title
        self.titleLabel = DirectLabel(
            parent=self.frame,
            text="Settings",
            text_scale=0.12,
            text_fg=(1, 0.9, 0.3, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.02, -0.02),
            frameColor=(0, 0, 0, 0),  # Transparent background
            pos=(0, 0, 0.45)
        )
        
        y_pos = 0.30
        self.vars = {}  # Track UI values
        
        # SFX Volume slider
        DirectLabel(
            parent=self.frame,
            text="SFX Volume :",
            text_scale=0.06,
            text_fg=(0.4, 0.8, 1, 1),
            text_shadow=(0,0,0,0.8),
            text_shadowOffset=(0.02, -0.02),
            frameColor=(0, 0, 0, 0),  # Transparent background
            pos=(-0.6,0,y_pos)
        )
        self.vars['sfx_volume'] = DirectSlider(
            parent=self.frame,
            value=self.settings_mgr.get('sfx_volume', 1.0),
            range=(0,1),
            scale=0.4,
            pos=(0,0,y_pos),
            frameColor=(0.1, 0.1, 0.1, 1),
            thumb_frameColor=(0.2, 0.6, 0.8, 1),
            thumb_relief='raised',
            command=self.on_slider_change, extraArgs=['sfx_volume']
        )
        y_pos -= 0.15
        
        # Graphics quality cycle button
        self.graphics_btn = DirectButton(
            parent=self.frame,
            text=f"Graphics: {self.settings_mgr.get('graphics', 'high').upper()}",
            text_pos=(0, -0.01),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            frameColor=(0.8, 0.6, 0.2, 1),
            frameSize=(-0.4, 0.4, -0.05, 0.05),
            pos=(0,0,y_pos),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.cycle_graphics
        )
        y_pos -= 0.15
        
        # AI Difficulty slider
        DirectLabel(
            parent=self.frame,
            text="AI Difficulty :",
            text_scale=0.06,
            text_fg=(1, 0.6, 0.6, 1),
            text_shadow=(0,0,0,0.8),
            text_shadowOffset=(0.02, -0.02),
            frameColor=(0, 0, 0, 0),  # Transparent background
            pos=(-0.6,0,y_pos)
        )
        self.vars['difficulty'] = DirectSlider(
            parent=self.frame,
            value=self.settings_mgr.get('difficulty', 1),
            range=(1,5),
            scale=0.4,
            pos=(0,0,y_pos),
            frameColor=(0.1, 0.1, 0.1, 1),
            thumb_frameColor=(0.6, 0.3, 0.3, 1),
            thumb_relief='raised',
            command=self.on_slider_change, extraArgs=['difficulty']
        )
        y_pos -= 0.15
        
        # FOV slider
        DirectLabel(
            parent=self.frame,
            text="Camera FOV :",
            text_scale=0.06,
            text_fg=(0.6, 1, 0.6, 1),
            text_shadow=(0,0,0,0.8),
            text_shadowOffset=(0.02, -0.02),
            frameColor=(0, 0, 0, 0),  # Transparent background
            pos=(-0.6,0,y_pos)
        )
        self.vars['fov'] = DirectSlider(
            parent=self.frame,
            value=self.settings_mgr.get('fov', 45),
            range=(30,60),
            scale=0.4,
            pos=(0,0,y_pos),
            frameColor=(0.1, 0.1, 0.1, 1),
            thumb_frameColor=(0.3, 0.6, 0.3, 1),
            thumb_relief='raised',
            command=self.on_slider_change, extraArgs=['fov']
        )
        y_pos -= 0.15
        
        # Board Theme (simple toggle classic/dark for now)
        self.theme_btn = DirectButton(
            parent=self.frame,
            text=f"Theme: {self.settings_mgr.get('board_theme', 'classic').upper()}",
            text_pos=(0, -0.01),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            frameColor=(0.6, 0.4, 0.8, 1),
            frameSize=(-0.4, 0.4, -0.05, 0.05),
            pos=(0,0,y_pos),
            relief='raised',
            borderWidth=(0.01, 0.01),
            command=self.cycle_theme
        )
        y_pos -= 0.15
        
        # Buttons row
        self.test_btn = DirectButton(
            parent=self.frame,
            text="Test SFX",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1,1,1,1),
            text_shadow=(0,0,0,0.8),
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(-0.3,0,y_pos),
            relief='raised',
            command=self.test_sfx
        )
        self.defaults_btn = DirectButton(
            parent=self.frame,
            text="Defaults",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1,1,1,1),
            text_shadow=(0,0,0,0.8),
            frameColor=(0.5, 0.5, 0.8, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0,0,y_pos),
            relief='raised',
            command=self.load_defaults
        )
        self.back_btn = DirectButton(
            parent=self.frame,
            text="Back",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1,1,1,1),
            text_shadow=(0,0,0,0.8),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0.3,0,y_pos),
            relief='raised',
            command=self.back_to_menu
        )
    
    def on_slider_change(self, key):
        value = self.vars[key]['value']
        self.settings_mgr.update(key, value)
        self.settings_mgr.apply(self.app)
    
    def cycle_graphics(self):
        levels = ['off', 'low', 'high']
        current = self.settings_mgr.get('graphics', 'high')
        next_level = levels[(levels.index(current) + 1) % 3]
        self.settings_mgr.update('graphics', next_level)
        self.graphics_btn['text'] = f"Graphics: {next_level.upper()}"
        self.settings_mgr.apply(self.app)
    
    def cycle_theme(self):
        themes = ['classic', 'dark']
        current = self.settings_mgr.get('board_theme', 'classic')
        next_theme = themes[(themes.index(current) + 1) % 2]
        self.settings_mgr.update('board_theme', next_theme)
        self.theme_btn['text'] = f"Theme: {next_theme.upper()}"
        self.settings_mgr.apply(self.app)
    
    def test_sfx(self):
        # Play notify sound at the volume currently set on the slider for live preview
        sfx = self.app.loader.loadSfx('sounds/notify.mp3')
        sfx.setVolume(self.vars['sfx_volume']['value'])
        sfx.play()
    
    def load_defaults(self):
        # Update all settings in the manager
        for key, default_value in self.settings_mgr.defaults.items():
            self.settings_mgr.update(key, default_value)

        # Update UI to reflect defaults
        # Sliders
        for key, slider in self.vars.items():
            slider['value'] = self.settings_mgr.defaults.get(key, slider['value'])

        # Buttons
        graphics_default = self.settings_mgr.defaults.get('graphics', 'high')
        self.graphics_btn['text'] = f"Graphics: {graphics_default.upper()}"

        theme_default = self.settings_mgr.defaults.get('board_theme', 'classic')
        self.theme_btn['text'] = f"Theme: {theme_default.upper()}"

        self.settings_mgr.save()
        self.settings_mgr.apply(self.app)
    
    def back_to_menu(self):
        self.settings_mgr.save()
        self.cleanup()
        self.app.showMenu()
    
    def cleanup(self):
        if hasattr(self, 'frame'):
            self.frame.destroy()
        # All other widgets are children of the frame and are destroyed with it.
