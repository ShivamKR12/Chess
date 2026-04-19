from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectSlider, DirectScrolledFrame
)
from states.base_state import AppState

class SettingsState(AppState):
    def __init__(self, app):
        super().__init__(app)
        self.settings_mgr = app.settings_mgr
        self.setup_ui()
    
    def setup_ui(self):
        self.click_sound = self.app.loader.loadSfx("sounds/clicksoundeffect.mp3")

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
        
        # Tab Buttons row
        tab_y = 0.32
        self.tab_audio = DirectButton(
            parent=self.frame, 
            text="Audio", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(-0.45, 0, tab_y), 
            relief='raised', 
            clickSound=self.click_sound,
            command=self.switch_tab, 
            extraArgs=['audio']
        )
        self.tab_visual = DirectButton(
            parent=self.frame, 
            text="Visual", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(-0.15, 0, tab_y), 
            relief='raised', 
            clickSound=self.click_sound,
            command=self.switch_tab, 
            extraArgs=['visual']
        )
        self.tab_gameplay = DirectButton(
            parent=self.frame, 
            text="Gameplay", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(0.15, 0, tab_y), 
            relief='raised', 
            clickSound=self.click_sound,
            command=self.switch_tab, 
            extraArgs=['gameplay']
        )
        self.tab_theme = DirectButton(
            parent=self.frame, 
            text="Theme", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(0.45, 0, tab_y), 
            relief='raised', 
            clickSound=self.click_sound,
            command=self.switch_tab, 
            extraArgs=['theme']
        )
        
        self.tabs = {
            'audio': DirectFrame(
                parent=self.frame, 
                frameColor=(0,0,0,0), 
                pos=(0,0,0)
            ),
            'visual': DirectFrame(
                parent=self.frame, 
                frameColor=(0,0,0,0), 
                pos=(0,0,0)
            ),
            'gameplay': DirectFrame(
                parent=self.frame, 
                frameColor=(0,0,0,0), 
                pos=(0,0,0)
            ),
            'theme': DirectFrame(
                parent=self.frame, 
                frameColor=(0,0,0,0), 
                pos=(0,0,0)
            ),
        }
        
        self.vars = {}  # Track UI values
        
        self.sfx_label = DirectLabel(
            parent=self.tabs['audio'], 
            text="SFX Volume :", 
            text_scale=0.06, 
            text_fg=(0.4, 0.8, 1, 1),
            text_shadow=(0,0,0,0.8), 
            text_shadowOffset=(0.02, -0.02), 
            frameColor=(0, 0, 0, 0), 
            pos=(-0.4,0,0.1)
        )
        self.vars['sfx_volume'] = DirectSlider(
            parent=self.tabs['audio'], 
            value=self.settings_mgr.get('sfx_volume', 1.0), 
            range=(0,1),
            scale=0.4, pos=(0.2,0,0.1), 
            frameColor=(0.1, 0.1, 0.1, 1), 
            thumb_frameColor=(0.2, 0.6, 0.8, 1),
            thumb_relief='raised', 
            command=self.on_slider_change, 
            extraArgs=['sfx_volume']
        )
        
        self.test_btn = DirectButton(
            parent=self.tabs['audio'], 
            text="Test SFX", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            text_shadow=(0,0,0,0.8),
            frameColor=(0.3, 0.6, 0.3, 1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(0,0,-0.1), 
            relief='raised',
            clickSound=self.click_sound,
            command=self.test_sfx
        )
        
        self.graphics_label = DirectLabel(
            parent=self.tabs['visual'], 
            text="Graphics :", 
            text_scale=0.06, 
            text_fg=(0.8, 0.6, 0.2, 1),
            text_shadow=(0,0,0,0.8), 
            text_shadowOffset=(0.02, -0.02), 
            frameColor=(0, 0, 0, 0), 
            pos=(-0.4,0,0.15)
        )
        
        self.graphics_buttons = {}
        graphics_levels = ['off', 'low', 'high']
        current_graphics = self.settings_mgr.get('graphics', 'high')
        
        for i, level in enumerate(graphics_levels):
            is_selected = (level == current_graphics)
            btn_color = (0.8, 0.6, 0.2, 1) if is_selected else (0.3, 0.4, 0.5, 1)
            
            btn = DirectButton(
                parent=self.tabs['visual'], 
                text=level.upper(),
                text_pos=(0, -0.01),
                text_scale=0.05, 
                text_fg=(1, 1, 1, 1), 
                text_shadow=(0, 0, 0, 0.8), 
                frameColor=btn_color,
                frameSize=(-0.1, 0.1, -0.04, 0.04), 
                pos=(-0.1 + i * 0.25, 0, 0.15), 
                relief='raised', 
                borderWidth=(0.01, 0.01),
            clickSound=self.click_sound,
                command=self.select_graphics,
                extraArgs=[level]
            )
            self.graphics_buttons[level] = btn
            
        self.fov_label = DirectLabel(
            parent=self.tabs['visual'], 
            text="Camera FOV :", 
            text_scale=0.06, 
            text_fg=(0.6, 1, 0.6, 1),
            text_shadow=(0,0,0,0.8), 
            text_shadowOffset=(0.02, -0.02), 
            frameColor=(0, 0, 0, 0), 
            pos=(-0.4,0,0.0)
        )
        self.vars['fov'] = DirectSlider(
            parent=self.tabs['visual'], 
            value=self.settings_mgr.get('fov', 45), 
            range=(30,60), 
            scale=0.4,
            pos=(0.2,0,0.0), 
            frameColor=(0.1, 0.1, 0.1, 1), 
            thumb_frameColor=(0.3, 0.6, 0.3, 1),
            thumb_relief='raised', 
            command=self.on_slider_change, 
            extraArgs=['fov']
        )
        
        # Advanced shader toggles
        self.bloom_btn = DirectButton(
            parent=self.tabs['visual'], 
            text=f"Bloom: {'ON' if self.settings_mgr.get('bloom', False) else 'OFF'}",
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1, 1, 1, 1), 
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04), 
            pos=(-0.40, 0, -0.20), 
            relief='raised',
            clickSound=self.click_sound,
            command=self.toggle_boolean, 
            extraArgs=['bloom', 'bloom_btn', 'Bloom']
        )
        self.blur_btn = DirectButton(
            parent=self.tabs['visual'], 
            text=f"Blur: {'ON' if self.settings_mgr.get('blur', False) else 'OFF'}",
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1, 1, 1, 1), 
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04), 
            pos=(0, 0, -0.20), 
            relief='raised',
            clickSound=self.click_sound,
            command=self.toggle_boolean, 
            extraArgs=['blur', 'blur_btn', 'Blur']
        )
        self.hdr_btn = DirectButton(
            parent=self.tabs['visual'], 
            text=f"HDR: {'ON' if self.settings_mgr.get('hdr', False) else 'OFF'}",
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1, 1, 1, 1), 
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04), 
            pos=(0.40, 0, -0.20), 
            relief='raised',
            clickSound=self.click_sound,
            command=self.toggle_boolean, 
            extraArgs=['hdr', 'hdr_btn', 'HDR']
        )

        self.difficulty_label = DirectLabel(
            parent=self.tabs['gameplay'], 
            text="AI Difficulty :", 
            text_scale=0.06, 
            text_fg=(1, 0.6, 0.6, 1),
            text_shadow=(0,0,0,0.8), 
            text_shadowOffset=(0.02, -0.02), 
            frameColor=(0, 0, 0, 0), 
            pos=(-0.4,0,0.1)
        )
        self.vars['difficulty'] = DirectSlider(
            parent=self.tabs['gameplay'], 
            value=self.settings_mgr.get('difficulty', 1), 
            range=(1,5), scale=0.4,
            pos=(0.2,0,0.1), 
            frameColor=(0.1, 0.1, 0.1, 1), 
            thumb_frameColor=(0.6, 0.3, 0.3, 1),
            thumb_relief='raised', 
            command=self.on_slider_change, 
            extraArgs=['difficulty']
        )
        
        self.theme_scroll = DirectScrolledFrame(
            parent=self.tabs['theme'],
            canvasSize=(-0.35, 0.35, -0.45, 0.1),
            frameSize=(-0.4, 0.4, -0.2, 0.2),
            pos=(0, 0, 0.0),
            frameColor=(0.1, 0.1, 0.1, 0.6),
            verticalScroll_thumb_frameColor=(0.4, 0.4, 0.4, 1),
            horizontalScroll_frameSize=(0, 0, 0, 0) # Hide horizontal scrollbar
        )
        
        self.theme_buttons = {}
        themes = ['classic', 'wood', 'marble', 'dark']
        current_theme = self.settings_mgr.get('board_theme', 'classic')
        
        for i, theme in enumerate(themes):
            is_selected = (theme == current_theme)
            btn_color = (0.6, 0.8, 0.4, 1) if is_selected else (0.3, 0.4, 0.5, 1)
            
            btn = DirectButton(
                parent=self.theme_scroll.getCanvas(), 
                text=theme.capitalize(),
                text_pos=(0, -0.01),
                text_scale=0.06, 
                text_fg=(1, 1, 1, 1), 
                text_shadow=(0, 0, 0, 0.8), 
                frameColor=btn_color,
                frameSize=(-0.3, 0.3, -0.05, 0.05), 
                pos=(0, 0, 0.0 - i * 0.12), 
                relief='raised', 
                borderWidth=(0.01, 0.01),
            clickSound=self.click_sound,
                command=self.select_theme,
                extraArgs=[theme]
            )
            self.theme_buttons[theme] = btn
        
        # Bottom Buttons
        self.defaults_btn = DirectButton(
            parent=self.frame, 
            text="Defaults", 
            text_pos=(0, -0.01),
            text_scale=0.05, 
            text_fg=(1,1,1,1), 
            text_shadow=(0,0,0,0.8),
            frameColor=(0.5, 0.5, 0.8, 1), 
            frameSize=(-0.15, 0.15, -0.04, 0.04), 
            pos=(-0.2,0,-0.4), 
            relief='raised',
            clickSound=self.click_sound,
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
            pos=(0.2,0,-0.4), 
            relief='raised',
            clickSound=self.click_sound,
            command=self.back_to_menu
        )
        
        # Initialize with audio tab active
        self.switch_tab('audio')
        
        # Bind scroll wheel
        self.accept('wheel_up', self.scroll_up)
        self.accept('wheel_down', self.scroll_down)
        
    def scroll_up(self):
        if getattr(self, 'active_tab', None) == 'theme' and hasattr(self, 'theme_scroll'):
            val = self.theme_scroll.verticalScroll['value']
            self.theme_scroll.verticalScroll['value'] = max(0.0, val - 0.2)
            
    def scroll_down(self):
        if getattr(self, 'active_tab', None) == 'theme' and hasattr(self, 'theme_scroll'):
            val = self.theme_scroll.verticalScroll['value']
            self.theme_scroll.verticalScroll['value'] = min(1.0, val + 0.2)

    def switch_tab(self, tab_name):
        """Switch between settings tabs and update UI state."""
        self.active_tab = tab_name
        
        # Update tab button colors
        buttons = {
            'audio': self.tab_audio,
            'visual': self.tab_visual,
            'gameplay': self.tab_gameplay,
            'theme': self.tab_theme
        }
        
        for name, btn in buttons.items():
            if name == tab_name:
                btn['frameColor'] = (0.2, 0.6, 0.8, 1)  # Highlighted blue
            else:
                btn['frameColor'] = (0.4, 0.4, 0.4, 1)  # Normal gray
                
        # Show/Hide frames
        for name, frame in self.tabs.items():
            if name == tab_name:
                frame.show()
            else:
                frame.hide()
    
    def on_slider_change(self, key):
        value = self.vars[key]['value']
        self.settings_mgr.update(key, value)
        self.settings_mgr.apply(self.app)
    
    def toggle_boolean(self, key, btn_attr, label):
        current = self.settings_mgr.get(key, False)
        new_val = not current
        self.settings_mgr.update(key, new_val)
        getattr(self, btn_attr)['text'] = f"{label}: {'ON' if new_val else 'OFF'}"
        self.settings_mgr.apply(self.app)

    def select_graphics(self, level):
        self.settings_mgr.update('graphics', level)
        
        for l, btn in self.graphics_buttons.items():
            if l == level:
                btn['frameColor'] = (0.8, 0.6, 0.2, 1)  # Highlighted
            else:
                btn['frameColor'] = (0.3, 0.4, 0.5, 1)  # Unselected
                
        self.settings_mgr.apply(self.app)
    
    def select_theme(self, theme):
        self.settings_mgr.update('board_theme', theme)
        
        for t, btn in self.theme_buttons.items():
            if t == theme:
                btn['frameColor'] = (0.6, 0.8, 0.4, 1)  # Highlighted (light green)
            else:
                btn['frameColor'] = (0.3, 0.4, 0.5, 1)  # Unselected (blueish gray)
                
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
        for l, btn in self.graphics_buttons.items():
            if l == graphics_default:
                btn['frameColor'] = (0.8, 0.6, 0.2, 1)
            else:
                btn['frameColor'] = (0.3, 0.4, 0.5, 1)

        theme_default = self.settings_mgr.defaults.get('board_theme', 'classic')
        for t, btn in self.theme_buttons.items():
            if t == theme_default:
                btn['frameColor'] = (0.6, 0.8, 0.4, 1)
            else:
                btn['frameColor'] = (0.3, 0.4, 0.5, 1)

        self.bloom_btn['text'] = f"Bloom: {'ON' if self.settings_mgr.defaults.get('bloom') else 'OFF'}"
        self.blur_btn['text'] = f"Blur: {'ON' if self.settings_mgr.defaults.get('blur') else 'OFF'}"
        self.hdr_btn['text'] = f"HDR: {'ON' if self.settings_mgr.defaults.get('hdr') else 'OFF'}"

        self.settings_mgr.save()
        self.settings_mgr.apply(self.app)
    
    def back_to_menu(self):
        self.settings_mgr.save()
        self.cleanup()
        self.app.showMenu()
    
    def cleanup(self):
        super().cleanup()
        
        # Explicitly destroy all direct GUI references to prevent memory leaks
        if hasattr(self, 'titleLabel'): self.titleLabel.destroy()
        
        if hasattr(self, 'sfx_label'): self.sfx_label.destroy()
        if hasattr(self, 'graphics_label'): self.graphics_label.destroy()
        if hasattr(self, 'fov_label'): self.fov_label.destroy()
        if hasattr(self, 'difficulty_label'): self.difficulty_label.destroy()
        
        if hasattr(self, 'tab_audio'): self.tab_audio.destroy()
        if hasattr(self, 'tab_visual'): self.tab_visual.destroy()
        if hasattr(self, 'tab_gameplay'): self.tab_gameplay.destroy()
        if hasattr(self, 'tab_theme'): self.tab_theme.destroy()
        
        if hasattr(self, 'test_btn'): self.test_btn.destroy()
        if hasattr(self, 'graphics_buttons'):
            for btn in self.graphics_buttons.values():
                btn.destroy()
        if hasattr(self, 'bloom_btn'): self.bloom_btn.destroy()
        if hasattr(self, 'blur_btn'): self.blur_btn.destroy()
        if hasattr(self, 'hdr_btn'): self.hdr_btn.destroy()
        if hasattr(self, 'theme_buttons'):
            for btn in self.theme_buttons.values():
                btn.destroy()
        if hasattr(self, 'defaults_btn'): self.defaults_btn.destroy()
        if hasattr(self, 'back_btn'): self.back_btn.destroy()
        
        if hasattr(self, 'theme_scroll'): self.theme_scroll.destroy()
        
        if hasattr(self, 'vars'):
            for slider in self.vars.values():
                slider.destroy()
                
        if hasattr(self, 'tabs'):
            for tab_frame in self.tabs.values():
                tab_frame.destroy()
                
        if hasattr(self, 'frame'):
            self.frame.destroy()
