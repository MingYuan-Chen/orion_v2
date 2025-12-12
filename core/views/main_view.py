import sys
from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit, QTextEdit, QLabel, QFrame
)
from PySide6.QtGui import QKeyEvent, QFont
from core.view_models.device_view_model import DeviceViewModel
from core.views.system_info_view import SystemInfoView
from core.views.hw_config_view import HWConfigView
from core.views.diagnostic_view import DiagnosticView
from core.views.battery_monitor_view import BatteryMonitorView
from core.views.control_panel_view import ControlPanelView
from util.logger import logger

class CommandInputLineEdit(QLineEdit):
    """
    A custom QLineEdit that detects common interrupt signals.
    The supported keys are defined in the INTERRUPT_KEYS dictionary.
    """
    interrupt_signal_pressed = Signal(bytes)

    # Defines the mapping from key combinations to the bytes to be emitted.
    # Format: (Qt.Key, Qt.KeyboardModifier): (bytes_to_emit, needs_no_autorepeat_check)
    INTERRUPT_KEYS = {
        (Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier): (b'\x03', False),
        (Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier): (b'\x04', False),
        (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier): (b'\x1b', True),
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        key_tuple = (event.key(), event.modifiers())

        if key_tuple in self.INTERRUPT_KEYS:
            byte_to_emit, needs_no_autorepeat = self.INTERRUPT_KEYS[key_tuple]

            if needs_no_autorepeat and event.isAutoRepeat():
                # Absorb auto-repeat events for keys that shouldn't have them (e.g., ESC)
                event.accept()
                return

            self.interrupt_signal_pressed.emit(byte_to_emit)
            event.accept()


class CommandInputLineEdit(QLineEdit):
    """
    A custom QLineEdit that detects common interrupt signals.
    The supported keys are defined in the INTERRUPT_KEYS dictionary.
    """
    interrupt_signal_pressed = Signal(bytes)

    # Defines the mapping from key combinations to the bytes to be emitted.
    # Format: (Qt.Key, Qt.KeyboardModifier): (bytes_to_emit, needs_no_autorepeat_check)
    INTERRUPT_KEYS = {
        (Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier): (b'\x03', False),
        (Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier): (b'\x04', False),
        (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier): (b'\x1b', True),
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        key_tuple = (event.key(), event.modifiers())

        if key_tuple in self.INTERRUPT_KEYS:
            byte_to_emit, needs_no_autorepeat = self.INTERRUPT_KEYS[key_tuple]

            if needs_no_autorepeat and event.isAutoRepeat():
                # Absorb auto-repeat events for keys that shouldn't have them (e.g., ESC)
                event.accept()
                return

            self.interrupt_signal_pressed.emit(byte_to_emit)
            event.accept()
        else:
            super().keyPressEvent(event)

class MainView(QWidget):
    """
    The main view (UI) of the application.
    It is a "dumb" view that only displays data from the ViewModel and forwards user actions to it.
    """
    def __init__(self, view_model: DeviceViewModel):
        super().__init__()
        self._vm = view_model
        self.setWindowTitle("PSC Orion")
        self.setGeometry(100, 100, 500, 600)
        
        self._system_info_view = None
        self._hw_config_view = None
        self._diagnostic_view = None
        self._battery_monitor_view = None
        self._control_panel_view = None

        # --- UI Widgets ---
        font_bold = QFont()
        font_bold.setBold(True)

        self.port_label = QLabel("COM:")
        self.port_combo = QComboBox()
        self.baud_label = QLabel("Speed:")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('115200')
        self.refresh_button = QPushButton("Serial Port Scan")
        self.connect_button = QPushButton("Connect")
        self.system_info_button = QPushButton("System Info")
        self.hw_config_button = QPushButton("HW Config")
        self.diagnostic_button = QPushButton("Function Test")
        self.battery_monitor_button = QPushButton("Battery Monitor")
        self.control_panel_button = QPushButton("LED / Backlight")
        self.platform_detection_button = QPushButton("Connected Device Initial")
        self.platform_label = QLabel(f"Platform: {self._vm.platform_name}")
        self.platform_label.setStyleSheet("font-size: 16px;")
        self.platform_label.setFont(font_bold)
        self.cmd_input = CommandInputLineEdit()
        self.send_button = QPushButton("Send")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-size: 14px;")
        self.log_view.document().setMaximumBlockCount(2000) # Limit lines to prevent freeze

        # Set fixed sizes for buttons
        self.refresh_button.setFixedSize(120, 30)
        self.connect_button.setFixedSize(100, 30)
        self.system_info_button.setFixedSize(100, 30)
        self.hw_config_button.setFixedSize(100, 30)
        self.diagnostic_button.setFixedSize(100, 30)
        self.battery_monitor_button.setFixedSize(120, 30)
        self.control_panel_button.setFixedSize(120, 30)
        self.platform_detection_button.setFixedSize(200, 30)

        # --- Layouts ---
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        second_layout = QHBoxLayout()
        
        # Create a frame for the system info section
        self.control_panel_frame = QFrame()
        self.control_panel_frame.setFrameShape(QFrame.StyledPanel)
        self.control_panel_frame.setStyleSheet("border: 1px solid #555; border-radius: 5px; background-color: #2b2b2b;")
        control_panel_layout = QHBoxLayout(self.control_panel_frame)
        control_panel_layout.setContentsMargins(10, 5, 10, 10)
        platform_layout = QHBoxLayout()
        
        cmd_layout = QHBoxLayout()

        top_layout.addWidget(self.port_label)
        top_layout.addWidget(self.port_combo, 1)
        top_layout.addWidget(self.baud_label)
        top_layout.addWidget(self.baud_combo)
        platform_layout.addWidget(self.platform_label)
        platform_layout.addWidget(self.platform_detection_button)
        platform_layout.addStretch()
        second_layout.addWidget(self.refresh_button)
        second_layout.addWidget(self.connect_button)
        second_layout.addStretch()
        control_panel_layout.addWidget(self.system_info_button)
        control_panel_layout.addWidget(self.hw_config_button)
        control_panel_layout.addWidget(self.diagnostic_button)
        control_panel_layout.addWidget(self.battery_monitor_button)
        control_panel_layout.addWidget(self.control_panel_button)
        control_panel_layout.addStretch()

        self.cmd_input.setPlaceholderText("Enter command or press Ctrl+C/D, ESC")
        cmd_layout.addWidget(self.cmd_input, 1)
        cmd_layout.addWidget(self.send_button)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(second_layout)
        main_layout.addLayout(cmd_layout)
        main_layout.addWidget(QLabel("Log & Received Data:"))
        main_layout.addWidget(self.log_view, 1)
        main_layout.addLayout(platform_layout)
        main_layout.addWidget(self.control_panel_frame)

        # --- Data Binding and Event Connections ---
        self._setup_bindings()

        # --- Initial State from ViewModel ---
        self.on_is_connected_changed() # Set initial UI state based on VM

    def _setup_bindings(self):
        """Set up connections between UI widgets and the ViewModel."""
        # --- Bind View actions to ViewModel slots ---
        self.refresh_button.clicked.connect(self._vm.refresh_ports)
        self.connect_button.clicked.connect(
            lambda: self._vm.toggle_connection(self.port_combo.currentText(), self.baud_combo.currentText())
        )
        self.send_button.clicked.connect(self._vm.send_command)
        self.cmd_input.returnPressed.connect(self._vm.send_command)
        self.cmd_input.textChanged.connect(self.on_command_input_changed)
        self.cmd_input.interrupt_signal_pressed.connect(self._vm.send_interrupt_bytes)
        self.system_info_button.clicked.connect(self._vm.open_system_info_view)
        self.hw_config_button.clicked.connect(self._vm.open_hw_config_view)
        self.diagnostic_button.clicked.connect(self.open_diagnostic_view)
        self.battery_monitor_button.clicked.connect(self.open_battery_monitor_view)
        self.control_panel_button.clicked.connect(self.open_control_panel_view)
        self.platform_detection_button.clicked.connect(self.on_platform_detection_button_clicked)
        
        # --- Bind ViewModel property changes to View update slots ---
        self._vm.log_appended.connect(self.on_log_appended)
        self._vm.is_connected_changed.connect(self.on_is_connected_changed)
        self._vm.command_text_changed.connect(self.on_command_text_changed)
        self._vm.platform_name_changed.connect(self.on_platform_name_changed)
        self._vm.login_required.connect(self.on_login_required)
        
        # --- Connect ViewModel signals to View slots (for opening sub-views) ---
        self._vm.open_system_info_requested.connect(self.open_system_info_view)
        self._vm.open_hw_config_requested.connect(self.open_hw_config_view)

        # --- Enable/Disable UI elements based on connection status ---
        self.port_combo.setModel(self._vm.port_list_model)

    @Slot(str)
    def on_command_input_changed(self, text: str):
        """Update the ViewModel's command_text property whenever the input changes."""
        self._vm.command_text = text

    # --- Slots to update the View when ViewModel properties change ---
    @Slot(str)
    def on_log_appended(self, message: str):
        self.log_view.append(message)
        # Auto-scroll is usually handled by append, but we can ensure it
        QTimer.singleShot(20, lambda: self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum()))

    @Slot()
    def on_is_connected_changed(self):
        connected = self._vm.is_connected
        detected = self._vm.platform_detected
        self.port_combo.setEnabled(not connected)
        self.baud_combo.setEnabled(not connected)
        self.refresh_button.setEnabled(not connected)
        self.send_button.setEnabled(connected)
        self.cmd_input.setEnabled(connected)
        self.connect_button.setText("Disconnect" if connected else "Connect")
        self.platform_detection_button.setEnabled(connected and not detected)
        self.platform_detection_button.setText("Connected Device Initial" if not detected else "Device Initialized")

        self.system_info_button.setEnabled(connected and detected)
        self.hw_config_button.setEnabled(connected and detected)
        self.diagnostic_button.setEnabled(connected and detected)
        self.battery_monitor_button.setEnabled(connected and detected)
        self.control_panel_button.setEnabled(connected and detected)

    @Slot()
    def on_platform_name_changed(self):
        """Update the platform name label when the VM notifies of a change."""
        self.platform_label.setText(f"Platform: {self._vm.platform_name}")
        self.on_is_connected_changed()

    @Slot()
    def on_command_text_changed(self):
        """Update the command input field if the VM changes it (e.g., clears it)."""
        if self.cmd_input.text() != self._vm.command_text:
            self.cmd_input.setText(self._vm.command_text)

    @Slot()
    def open_system_info_view(self):
        if self._system_info_view is None:
            self._system_info_view = SystemInfoView(self._vm)
        self._system_info_view.show()

    @Slot()
    def open_hw_config_view(self):
        if self._hw_config_view is None:
            self._hw_config_view = HWConfigView(self._vm)
        self._hw_config_view.show()

    @Slot()
    def open_diagnostic_view(self):
        if self._diagnostic_view is None:
            self._diagnostic_view = DiagnosticView(self._vm)
        self._diagnostic_view.start_diagnostic()
        self._diagnostic_view.show()
        self._vm.run_all_diagnostics()

    @Slot()
    def open_battery_monitor_view(self):
        if self._battery_monitor_view is None:
            self._battery_monitor_view = BatteryMonitorView(self._vm)
        self._battery_monitor_view.show()

    @Slot()
    def open_control_panel_view(self):
        if self._control_panel_view is None:
            self._control_panel_view = ControlPanelView(self._vm)
        self._control_panel_view.show()
    
    @Slot()
    def on_platform_detection_button_clicked(self):
        self.platform_detection_button.setEnabled(False)
        self.platform_detection_button.setText("Initializing...")
        self._vm.start_platform_detection()
    
    @Slot()
    def on_login_required(self):
        self.platform_detection_button.setEnabled(True)
        self.platform_detection_button.setText("Connected Device Initial")

    def closeEvent(self, event):
        """Ensure clean-up is called on window close."""
        if self._system_info_view: self._system_info_view.close()
        if self._hw_config_view: self._hw_config_view.close()
        if self._diagnostic_view: self._diagnostic_view.close()
        if self._battery_monitor_view: self._battery_monitor_view.close()
        if self._control_panel_view: self._control_panel_view.close()
        self._vm.clean_up()
        super().closeEvent(event)
