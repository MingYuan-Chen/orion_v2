from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor
from core.view_models.device_view_model import DeviceViewModel

class FunctionalityView(QWidget):
    """
    View to provide device functionality controls, such as LED status.
    """
    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Functionality Control")
        self.resize(500, 400)
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        font_bold = QFont()
        font_bold.setBold(True)
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Device Functionality")
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
        
        status_layout.addWidget(QLabel("Current Status:"))
        status_layout.addWidget(self.led_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.get_status_btn = QPushButton("Get Status")
        status_layout.addWidget(self.get_status_btn)
        
        led_layout.addLayout(status_layout)

        # Dynamic Control Buttons
        self.buttons_layout = QGridLayout()
        led_layout.addLayout(self.buttons_layout)
        
        main_layout.addWidget(led_group)
        main_layout.addStretch()

    def _setup_bindings(self):
        self._vm.led_status_updated.connect(self.on_led_status_updated)
        self._vm.platform_name_changed.connect(self.refresh_buttons)
        self.get_status_btn.clicked.connect(self._vm.get_led_status)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_buttons()
        # Auto-fetch status on show
        self._vm.get_led_status()

    @Slot()
    def refresh_buttons(self):
        """Re-generates buttons based on available commands for the current platform."""
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
        self.status_label.setText(status_text)
        
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
