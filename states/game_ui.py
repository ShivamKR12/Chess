from panda3d.core import TextNode, OmniBoundingVolume
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectDialog, DirectScrolledFrame
from direct.gui.OnscreenText import OnscreenText
from direct.interval.LerpInterval import LerpPosInterval

class GameUI:
    """
    Handles all 2D user interface elements for the active game state.
    Separated from the core chess logic for maintainability.
    """
    def __init__(self, game):
        self.game = game
        self.app = game.app
        
        self.historyDrawerOpen = False
        self.drawerInterval = None
        
        self.setupUI()
        
    def setupUI(self):
        """Create on-screen controls and status text using DirectGUI."""
        self.statusFrame = DirectFrame(
            frameColor=(0.2, 0.4, 0.6, 0.9),
            frameSize=(-1.335, 1.335, -0.15, 0.15),
            pos=(0, 0, 0.85),
            relief='groove',
            borderWidth=(0.02, 0.02)
        )
        
        self.statusLabel = DirectLabel(
            parent=self.statusFrame,
            text="Turn: WHITE",
            text_fg=(1, 1, 1, 1),
            text_scale=0.06,
            text_align=TextNode.ACenter,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.02, -0.02),
            text_wordwrap=25,
            textMayChange=1,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.05)
        )
        
        self.restartButton = DirectButton(
            parent=self.statusFrame,
            text="New Game",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.25, 0.25, -0.04, 0.04),
            pos=(-1.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.game.onNewGame
        )
        
        self.resignButton = DirectButton(
            parent=self.statusFrame,
            text="Resign",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(-0.5, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.showResignDialog
        )
        
        self.undoButton = DirectButton(
            parent=self.statusFrame,
            text="Undo",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.5, 0.5, 0.8, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.game.undoMove
        )
        
        self.saveButton = DirectButton(
            parent=self.statusFrame,
            text="Save",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.2, 0.6, 0.8, 1),
            frameSize=(-0.15, 0.15, -0.04, 0.04),
            pos=(0.5, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.game.saveGame
        )
        
        self.quitButton = DirectButton(
            parent=self.statusFrame,
            text="Quit",
            text_pos=(0, -0.01),
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0.5, 0.5, 0.5, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(1.0, 0, -0.09),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.showQuitDialog
        )
        
        self.moveHistoryFrame = DirectFrame(
            frameColor=(0.2, 0.4, 0.6, 0.9),
            frameSize=(-0.32, 0.32, -0.85, 0.85),
            pos=(1.1, 0, -0.15),
            relief='groove',
            borderWidth=(0.02, 0.02)
        )
        
        self.historyToggleButton = DirectButton(
            parent=self.moveHistoryFrame,
            text="<",
            text_pos=(0, -0.015),
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.4, 0.8, 1),
            frameSize=(-0.05, 0.05, -0.1, 0.1),
            pos=(-0.37, 0, 0),
            relief='raised',
            borderWidth=(0.01, 0.01),
            clickSound=self.game.click_sound,
            command=self.toggleHistoryDrawer
        )

        self.historyHeader = DirectLabel(
            parent=self.moveHistoryFrame,
            text="White         Black",
            text_fg=(1, 0.9, 0.3, 1),
            text_scale=0.06,
            text_shadow=(0, 0, 0, 0.8),
            frameColor=(0, 0, 0, 0),
            pos=(-0.05, 0, 0.75)
        )
        
        self.historyScroll = DirectScrolledFrame(
            parent=self.moveHistoryFrame,
            frameSize=(-0.3, 0.3, -0.8, 0.7),
            canvasSize=(-0.28, 0.28, -0.8, 0.7),
            frameColor=(0.1, 0.1, 0.15, 0.6),
            verticalScroll_thumb_frameColor=(0.2, 0.6, 0.8, 1),
            horizontalScroll_frameSize=(0, 0, 0, 0),
            relief='sunken',
            borderWidth=(0.01, 0.01)
        )
        
        self.moveHistoryWhiteLabel = DirectLabel(
            parent=self.historyScroll.getCanvas(),
            text="",
            text_fg=(1, 1, 1, 1),
            text_scale=0.05,
            text_align=TextNode.ALeft,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0, 0, 0, 0),
            pos=(-0.26, 0, 0.65)
        )
        self.moveHistoryWhiteLabel.node().setBounds(OmniBoundingVolume())
        self.moveHistoryWhiteLabel.node().setFinal(True)
        
        self.moveHistoryBlackLabel = DirectLabel(
            parent=self.historyScroll.getCanvas(),
            text="",
            text_fg=(0.7, 0.9, 1.0, 1),
            text_scale=0.05,
            text_align=TextNode.ALeft,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.01, -0.01),
            frameColor=(0, 0, 0, 0),
            pos=(0.04, 0, 0.65)
        )
        self.moveHistoryBlackLabel.node().setBounds(OmniBoundingVolume())
        self.moveHistoryBlackLabel.node().setFinal(True)

        self.turnText = OnscreenText(
            text="Turn: WHITE",
            pos=(-1.3, 0.9),
            scale=0.06,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.8),
            mayChange=1
        )
        self.turnText.hide()

    def setStatus(self, text):
        """Update the status text and keep the main turn text in sync."""
        if hasattr(self, 'statusLabel'):
            self.statusLabel['text'] = text
        if text.startswith("Turn:") and hasattr(self, 'turnText'):
            self.turnText.setText(text)

    def updateMoveHistoryDisplay(self, moveNotation):
        """Update the move history display with current moves."""
        white_text_lines = []
        black_text_lines = []
        
        for i in range(0, len(moveNotation), 2):
            move_num = (i // 2) + 1
            white_move = moveNotation[i] if i < len(moveNotation) else ""
            black_move = moveNotation[i+1] if i+1 < len(moveNotation) else ""
            white_text_lines.append(f"{move_num}. {white_move}")
            black_text_lines.append(f"{black_move}")
        
        if hasattr(self, 'moveHistoryWhiteLabel') and hasattr(self, 'moveHistoryBlackLabel'):
            self.moveHistoryWhiteLabel['text'] = "\n".join(white_text_lines)
            self.moveHistoryBlackLabel['text'] = "\n".join(black_text_lines)
            
            num_lines = len(white_text_lines)
            line_height = 0.055
            total_height = num_lines * line_height
            
            if hasattr(self, 'historyScroll'):
                bottom = min(-0.8, 0.7 - total_height - 0.1)
                self.historyScroll['canvasSize'] = (-0.28, 0.28, bottom, 0.7)
                self.historyScroll.verticalScroll['value'] = 1.0

    def toggleHistoryDrawer(self):
        """Toggle the move history drawer sliding in and out."""
        w = self.app.win.getXSize()
        h = self.app.win.getYSize()
        window_aspect = w / float(h) if h > 0 else 1.33
        
        on_x = window_aspect - 0.34
        off_x = window_aspect + 0.32
        
        if self.drawerInterval and self.drawerInterval.isPlaying():
            self.drawerInterval.pause()
            
        if self.historyDrawerOpen:
            self.drawerInterval = LerpPosInterval(
                self.moveHistoryFrame, 0.3, (off_x, 0, -0.15), blendType='easeInOut'
            )
            self.historyToggleButton['text'] = "<"
            self.historyDrawerOpen = False
        else:
            self.drawerInterval = LerpPosInterval(
                self.moveHistoryFrame, 0.3, (on_x, 0, -0.15), blendType='easeInOut'
            )
            self.historyToggleButton['text'] = ">"
            self.historyDrawerOpen = True
            
        self.drawerInterval.start()

    def updateAspect(self, window_aspect):
        """Scale UI dynamically based on aspect ratio."""
        if hasattr(self, 'statusFrame'):
            self.statusFrame['frameSize'] = (-window_aspect, window_aspect, -0.15, 0.15)
            spread = max(1.0, window_aspect - 0.335)
            if hasattr(self, 'restartButton'): self.restartButton.setPos(-spread, 0, -0.09)
            if hasattr(self, 'resignButton'):  self.resignButton.setPos(-spread/2, 0, -0.09)
            if hasattr(self, 'undoButton'):    self.undoButton.setPos(0, 0, -0.09)
            if hasattr(self, 'saveButton'):    self.saveButton.setPos(spread/2, 0, -0.09)
            if hasattr(self, 'quitButton'):    self.quitButton.setPos(spread, 0, -0.09)
            
        if hasattr(self, 'moveHistoryFrame'):
            on_x = window_aspect - 0.34
            off_x = window_aspect + 0.32
            is_animating = self.drawerInterval and self.drawerInterval.isPlaying()
            if not is_animating:
                if self.historyDrawerOpen:
                    self.moveHistoryFrame.setPos(on_x, 0, -0.15)
                else:
                    self.moveHistoryFrame.setPos(off_x, 0, -0.15)

    def showResignDialog(self):
        if self.game.gameOver: return
        self.resignDialog = DirectDialog(
            dialogName="resignDialog",
            text="Are you sure you want to resign?",
            buttonTextList=["Yes", "No"],
            buttonValueList=[1, 0],
            command=self.onResignConfirm,
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01),
            button_clickSound=self.game.click_sound
        )
        self.resignDialog.buttonList[0]['frameColor'] = (0.3, 0.6, 0.3, 1)
        self.resignDialog.buttonList[1]['frameColor'] = (0.6, 0.3, 0.3, 1)

    def onResignConfirm(self, value):
        if value == 1:
            self.game.resignGame()
        if hasattr(self, 'resignDialog'):
            self.resignDialog.cleanup()
            del self.resignDialog

    def showQuitDialog(self):
        if hasattr(self, 'quitDialog'): return
        self.quitDialog = DirectDialog(
            dialogName="quitDialog",
            text="Are you sure you want to quit to menu?",
            buttonTextList=["Yes", "No"],
            buttonValueList=[1, 0],
            command=self.onQuitConfirm,
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01),
            button_clickSound=self.game.click_sound
        )
        self.quitDialog.buttonList[0]['frameColor'] = (0.3, 0.6, 0.3, 1)
        self.quitDialog.buttonList[1]['frameColor'] = (0.6, 0.3, 0.3, 1)

    def onQuitConfirm(self, value):
        if value == 1:
            self.game.returnToMenu()
        if hasattr(self, 'quitDialog'):
            self.quitDialog.cleanup()
            del self.quitDialog

    def showPromotionDialog(self, square):
        if self.game.gameOver: return
        self.promotionDialog = DirectDialog(
            dialogName="promotionDialog",
            text="Choose promotion piece:",
            buttonTextList=["Queen", "Rook", "Bishop", "Knight"],
            buttonValueList=["Queen", "Rook", "Bishop", "Knight"],
            command=self.onPromotionChoice,
            extraArgs=[square],
            frameColor=(0.2, 0.4, 0.6, 0.9),
            relief='groove',
            borderWidth=(0.02, 0.02),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 0.8),
            button_text_fg=(1, 1, 1, 1),
            button_text_shadow=(0, 0, 0, 0.8),
            button_relief='raised',
            button_borderWidth=(0.01, 0.01),
            button_clickSound=self.game.click_sound
        )
        self.promotionDialog.buttonList[0]['frameColor'] = (0.6, 0.4, 0.8, 1)
        self.promotionDialog.buttonList[1]['frameColor'] = (0.8, 0.4, 0.4, 1)
        self.promotionDialog.buttonList[2]['frameColor'] = (0.4, 0.8, 0.4, 1)
        self.promotionDialog.buttonList[3]['frameColor'] = (0.2, 0.6, 0.8, 1)

    def onPromotionChoice(self, piece_type, square):
        if hasattr(self, 'promotionDialog'):
            self.promotionDialog.cleanup()
            del self.promotionDialog
        self.game.executePromotion(piece_type, square)

    def clearDialogs(self):
        """Remove any active dialogs from the screen (used during resets/undos)."""
        for dialog in ['quitDialog', 'resignDialog', 'promotionDialog']:
            if hasattr(self, dialog):
                d = getattr(self, dialog)
                if d:
                    d.cleanup()
                delattr(self, dialog)

    def cleanup(self):
        """Clean up all GUI elements."""
        if hasattr(self, 'statusLabel'): self.statusLabel.destroy()
        if hasattr(self, 'restartButton'): self.restartButton.destroy()
        if hasattr(self, 'resignButton'): self.resignButton.destroy()
        if hasattr(self, 'undoButton'): self.undoButton.destroy()
        if hasattr(self, 'saveButton'): self.saveButton.destroy()
        if hasattr(self, 'quitButton'): self.quitButton.destroy()
        if hasattr(self, 'statusFrame'): self.statusFrame.destroy()
        if hasattr(self, 'quitDialog'):
            self.quitDialog.cleanup()
            del self.quitDialog
        if hasattr(self, 'historyHeader'): self.historyHeader.destroy()
        if hasattr(self, 'moveHistoryWhiteLabel'): self.moveHistoryWhiteLabel.destroy()
        if hasattr(self, 'moveHistoryBlackLabel'): self.moveHistoryBlackLabel.destroy()
        if hasattr(self, 'historyScroll'): self.historyScroll.destroy()
        if hasattr(self, 'historyToggleButton'): self.historyToggleButton.destroy()
        if hasattr(self, 'moveHistoryFrame'): self.moveHistoryFrame.destroy()
        if hasattr(self, 'turnText'): self.turnText.destroy()
        if hasattr(self, 'resignDialog'):
            self.resignDialog.cleanup()
            del self.resignDialog
        if hasattr(self, 'promotionDialog'):
            self.promotionDialog.cleanup()
            del self.promotionDialog
        if self.drawerInterval and self.drawerInterval.isPlaying():
            self.drawerInterval.pause()
            del self.drawerInterval