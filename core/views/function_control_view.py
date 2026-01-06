from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout, QScrollArea, QSlider
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor
from core.view_models.device_view_model import DeviceViewModel
from util.logger import logger

class FunctionControlView(QWidget):
    """
    View to provide functionality controls, such as LED status.
    """
    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Functions")
        self.resize(500, 600) # Increased height for Backlight
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        font_bold = QFont()
        font_bold.setBold(True)
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Functions")
        title_label.setStyleSheet("font-size: 20px;")
        title_label.setFont(font_bold)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # --- LED Control Section ---
        led_group = QFrame()
        led_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        led_group.setStyleSheet("border: 1px solid #555; border-radius: 5px; background-color: #2b2b2b;")
        led_layout = QVBoxLayout(led_group)
        
        led_title = QLabel("LED Control")
        led_title.setStyleSheet("font-size: 16px;")
        led_title.setFont(font_bold)
        led_layout.addWidget(led_title)

        # Status Display
        status_layout = QHBoxLayout()
        self.led_indicator = QLabel()
        self.led_indicator.setFixedSize(30, 30)
        self.led_indicator.setStyleSheet("background-color: gray; border-radius: 10px; border: 1px solid black;")
        
        self.status_label = QLabel("Unknown")
        self.status_label.setFont(QFont("Arial", 10))
        
        status_layout.addWidget(self.led_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        led_layout.addLayout(status_layout)

        # Dynamic Control Buttons
        self.buttons_layout = QGridLayout()
        led_layout.addLayout(self.buttons_layout)
        
        main_layout.addWidget(led_group)

        # --- Backlight Control Section ---
        bl_group = QFrame()
        bl_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        bl_group.setStyleSheet("border: 1px solid #555; border-radius: 5px; background-color: #2b2b2b;")
        bl_layout = QVBoxLayout(bl_group)
        
        bl_title = QLabel("Backlight Control")
        bl_title.setStyleSheet("font-size: 16px;")
        bl_title.setFont(font_bold)
        bl_layout.addWidget(bl_title)

        # Backlight Status
        bl_status_layout = QHBoxLayout()
        self.bl_status_label = QLabel("Unknown")
        self.bl_status_label.setFont(QFont("Arial", 10))
        
        self.bl_on_btn = QPushButton("On")
        self.bl_off_btn = QPushButton("Off")
        
        bl_status_layout.addWidget(self.bl_status_label)
        bl_status_layout.addStretch()
        bl_status_layout.addWidget(self.bl_on_btn)
        bl_status_layout.addWidget(self.bl_off_btn)
        
        bl_layout.addLayout(bl_status_layout)

        # Backlight Brightness
        bl_bright_layout = QHBoxLayout()
        self.bl_slider = QSlider(Qt.Horizontal)
        self.bl_slider.setTickPosition(QSlider.TicksBelow)
        self.bl_slider.setTickInterval(1)
        
        self.bl_value_label = QLabel("Unknown")

        bl_bright_layout.addWidget(QLabel("Brightness:"))
        bl_bright_layout.addWidget(self.bl_slider)
        bl_bright_layout.addWidget(self.bl_value_label)
        
        bl_layout.addLayout(bl_bright_layout)
        
        main_layout.addWidget(bl_group)
        main_layout.addStretch()

    def _setup_bindings(self):
        self._vm.led_status_updated.connect(self.on_led_status_updated)
        self._vm.platform_name_changed.connect(self.refresh_buttons)
        
        # Backlight bindings
        self._vm.backlight_updated.connect(self.on_backlight_updated)
        self.bl_on_btn.clicked.connect(lambda: self._vm.toggle_backlight(True))
        self.bl_off_btn.clicked.connect(lambda: self._vm.toggle_backlight(False))
        self.bl_slider.valueChanged.connect(self._vm.set_backlight_brightness)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_buttons()
        # Auto-fetch status on show
        self._vm.get_led_status()
        self._vm.get_backlight_status()
        self._vm.get_backlight_brightness()
        self._vm.init_screen_for_backlight_control()

    @Slot()
    def refresh_buttons(self):
        """Re-generates buttons based on available commands for the current platform."""
        max_range = 10 if self._vm.platform_name == "Athena" else 7
        self.bl_slider.setRange(0, max_range)

        # Clear existing buttons
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        commands = self._vm.get_available_led_commands()
        
        # Create buttons in a grid
        row, col = 0, 0
        max_cols = 4 if self._vm.platform_name == "Athena" else 3
        
        for cmd in commands:
            btn = QPushButton(cmd.replace("_", " ").title())
            # Use a closure to capture the specific command
            btn.clicked.connect(lambda checked=False, c=cmd: self._vm.set_led_status(c))
            
            self.buttons_layout.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    @Slot(str)
    def on_led_status_updated(self, status_text: str):
        self.status_label.setText(status_text.replace("_", " ").title())
        
        # Update indicator color based on text
        color = "gray"
        lower_text = status_text.lower()
        
        if "green" in lower_text:
            color = "#00FF00" # Bright Green
        elif "red" in lower_text:
            color = "#FF0000" # Red
        elif "blue" in lower_text:
            color = "#0000FF" # Blue
        elif "amber" in lower_text or "yellow" in lower_text:
            color = "#FFBF00" # Amber
        elif "off" in lower_text:
            color = "black"
            
        # Handle blinking (maybe striped or lighter color? For now just same color)
        
        self.led_indicator.setStyleSheet(f"background-color: {color}; border-radius: 10px; border: 1px solid black;")

    @Slot(str)
    def on_backlight_updated(self, status_text: str):
        if "On" in status_text or "Off" in status_text:
            text_background = "#00FF00" if "On" in status_text else "#FF0000"
            status_text = "ON" if "On" in status_text else "OFF"
            self.bl_status_label.setStyleSheet(f"color: black; background-color: {text_background}; border-radius: 10px; border: 1px solid black;")
            self.bl_status_label.setText(status_text)
        elif "%" in status_text:
            self.bl_value_label.setText(status_text)
