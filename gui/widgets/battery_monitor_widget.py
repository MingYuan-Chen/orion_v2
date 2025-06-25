"""
Battery Monitor Widget Module
A standalone window for real-time battery monitoring
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                              QLabel, QPushButton, QProgressBar, QFrame, 
                              QGroupBox, QSpacerItem, QSizePolicy, QComboBox, QCheckBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QPixmap, QIcon
from typing import Dict, Any, Optional
from util.logger import logger
import datetime

from core.services.battery_monitor_service import BatteryMonitorService
from gui.views.battery_monitor_manager import BatteryMonitorManager


class BatteryMonitorWidget(QWidget):
    """
    Battery Monitor Widget
    A standalone window for real-time battery monitoring
    """
    
    # Define signals
    window_closing = Signal()
    
    def __init__(self, device_id: str, serial_worker, platform_name: str = "hydra", parent=None):
        """
        Initialize Battery Monitor Widget
        
        Args:
            device_id: Device ID
            serial_worker: Serial worker for command execution
            platform_name: Platform name for command set
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.device_id = device_id
        self.platform_name = platform_name
        
        # Create battery service and manager
        self.battery_service = BatteryMonitorService(serial_worker, platform_name)
        self.battery_manager = BatteryMonitorManager(device_id, self.battery_service)
        
        # UI components
        self.ui_components = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.auto_refresh_enabled = True
        self.refresh_interval = 5000  # 5 seconds default
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._setup_battery_manager()
        
        logger.info(f"Battery Monitor Widget initialized for device: {device_id}")
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Set window properties
        self.setWindowTitle(f"Battery Monitor - {self.device_id}")
        self.setFixedSize(450, 520)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        
        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: white;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #333333;
                border-radius: 5px;
                margin: 5px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Battery Monitor")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #4FC3F7; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Device info
        device_label = QLabel(f"Device: {self.device_id} | Platform: {self.platform_name}")
        device_label.setAlignment(Qt.AlignCenter)
        device_label.setStyleSheet("color: #CCCCCC; margin-bottom: 10px;")
        main_layout.addWidget(device_label)
        
        # Status group
        status_group = self._create_status_group()
        main_layout.addWidget(status_group)
        
        # Battery data group
        battery_group = self._create_battery_data_group()
        main_layout.addWidget(battery_group)
        
        # Controls group
        controls_group = self._create_controls_group()
        main_layout.addWidget(controls_group)
        
        # Add spacer
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer)
    
    def _create_status_group(self) -> QGroupBox:
        """Create status display group"""
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)
        
        # Status label
        self.ui_components["status_label"] = QLabel("Ready")
        self.ui_components["status_label"].setAlignment(Qt.AlignCenter)
        self.ui_components["status_label"].setStyleSheet("""
            QLabel {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.ui_components["status_label"])
        
        return group
    
    def _create_battery_data_group(self) -> QGroupBox:
        """Create battery data display group"""
        group = QGroupBox("Battery Information")
        main_layout = QVBoxLayout(group)
        
        # Data frame
        data_frame = QFrame()
        data_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        data_layout = QGridLayout(data_frame)
        data_layout.setSpacing(12)
        
        # Battery level with progress bar
        data_layout.addWidget(QLabel("Battery Level:"), 0, 0)
        self.ui_components["battery_level_value"] = QLabel("--%")
        self.ui_components["battery_level_value"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["battery_level_value"], 0, 1)
        
        self.ui_components["progress_bar"] = QProgressBar()
        self.ui_components["progress_bar"].setRange(0, 100)
        self.ui_components["progress_bar"].setValue(0)
        self.ui_components["progress_bar"].setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #1E1E1E;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4ECDC4;
                border-radius: 2px;
            }
        """)
        data_layout.addWidget(self.ui_components["progress_bar"], 0, 2)
        
        # Charging Voltage
        data_layout.addWidget(QLabel("Charging Voltage:"), 1, 0)
        self.ui_components["voltage_label"] = QLabel("-- V")
        self.ui_components["voltage_label"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["voltage_label"], 1, 1)
        
        # Charging Current
        data_layout.addWidget(QLabel("Charging Current:"), 2, 0)
        self.ui_components["current_label"] = QLabel("-- A")
        self.ui_components["current_label"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["current_label"], 2, 1)
        
        # Temperature
        data_layout.addWidget(QLabel("Temperature:"), 3, 0)
        self.ui_components["temperature_label"] = QLabel("-- °C")
        self.ui_components["temperature_label"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["temperature_label"], 3, 1)
        
        # CPU Usage
        data_layout.addWidget(QLabel("CPU Usage:"), 4, 0)
        self.ui_components["cpu_usage_label"] = QLabel("--%")
        self.ui_components["cpu_usage_label"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["cpu_usage_label"], 4, 1)
        
        # Memory Usage
        data_layout.addWidget(QLabel("Memory Usage:"), 5, 0)
        self.ui_components["memory_usage_label"] = QLabel("--%")
        self.ui_components["memory_usage_label"].setStyleSheet("color: #4ECDC4; font-weight: bold;")
        data_layout.addWidget(self.ui_components["memory_usage_label"], 5, 1)
        
        # Set column stretch
        data_layout.setColumnStretch(2, 1)
        
        main_layout.addWidget(data_frame)
        
        return group
    
    def _create_controls_group(self) -> QGroupBox:
        """Create controls group"""
        group = QGroupBox("Controls")
        layout = QVBoxLayout(group)
        
        # Auto refresh controls
        refresh_layout = QHBoxLayout()
        
        refresh_layout.addWidget(QLabel("Auto Refresh:"))
        
        self.ui_components["interval_combo"] = QComboBox()
        self.ui_components["interval_combo"].addItems([
            "1 second", "2 seconds", "3 seconds", "5 seconds", "10 seconds", "30 seconds"
        ])
        self.ui_components["interval_combo"].setCurrentText("3 seconds")
        self.ui_components["interval_combo"].setStyleSheet("""
            QComboBox {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 3px;
                padding: 5px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                border: none;
            }
        """)
        refresh_layout.addWidget(self.ui_components["interval_combo"])
        
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Refresh once button
        self.ui_components["refresh_once_button"] = QPushButton("Refresh Once")
        self.ui_components["refresh_once_button"].setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        button_layout.addWidget(self.ui_components["refresh_once_button"])
        
        # Monitor button
        self.ui_components["monitor_button"] = QPushButton("Start Monitoring")
        self.ui_components["monitor_button"].setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        button_layout.addWidget(self.ui_components["monitor_button"])
        
        layout.addLayout(button_layout)
        
        # Checkbox layout (separate row for better visibility)
        checkbox_layout = QHBoxLayout()
        
        # Log as File checkbox
        self.ui_components["log_as_file_checkbox"] = QCheckBox("Log as File")
        self.ui_components["log_as_file_checkbox"].setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 12px;
                spacing: 5px;
                margin: 5px 0px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #555555;
                background-color: #2B2B2B;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0078D7;
                background-color: #0078D7;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1C97EA;
            }
        """)
        checkbox_layout.addWidget(self.ui_components["log_as_file_checkbox"])
        checkbox_layout.addStretch()  # Add stretch to left-align the checkbox
        
        layout.addLayout(checkbox_layout)
        
        return group
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Button connections
        self.ui_components["refresh_once_button"].clicked.connect(self._on_refresh_once)
        self.ui_components["monitor_button"].clicked.connect(self._on_toggle_monitoring)
        self.ui_components["interval_combo"].currentTextChanged.connect(self._on_interval_changed)
        
        # Battery manager connections
        self.battery_manager.monitoring_started.connect(self._on_monitoring_started)
        self.battery_manager.monitoring_completed.connect(self._on_monitoring_completed)
        self.battery_manager.monitoring_error.connect(self._on_monitoring_error)
    
    def _setup_battery_manager(self):
        """Setup battery manager with UI components"""
        # Map UI components for battery manager
        ui_mapping = {
            "monitor_button": self.ui_components["monitor_button"],
            "status_label": self.ui_components["status_label"],
            "voltage_label": self.ui_components["voltage_label"],
            "current_label": self.ui_components["current_label"],
            "temperature_label": self.ui_components["temperature_label"],
            "battery_level_label": self.ui_components["battery_level_value"],
            "progress_bar": self.ui_components["progress_bar"],
            "log_as_file_checkbox": self.ui_components["log_as_file_checkbox"]
        }
        
        self.battery_manager.set_ui_components(ui_mapping)
        
        # Set default monitoring interval
        self._on_interval_changed("3 seconds")
    
    def _on_refresh_once(self):
        """Handle refresh once button click"""
        logger.info("Battery Monitor: Refresh once requested")
        
        if self.is_monitoring:
            logger.warning("Cannot refresh once while monitoring is active")
            return
        
        # Get single reading
        self.battery_manager.get_single_reading()
    
    def _on_toggle_monitoring(self):
        """Handle monitor button toggle"""
        if self.is_monitoring:
            logger.info("Battery Monitor: Stopping monitoring")
            self.battery_manager.stop_monitoring()
        else:
            logger.info("Battery Monitor: Starting monitoring")
            self.battery_manager.start_monitoring()
    
    def _on_interval_changed(self, interval_text: str):
        """Handle interval change"""
        # Parse interval from text
        interval_map = {
            "1 second": 1000,
            "2 seconds": 2000,
            "3 seconds": 3000,
            "5 seconds": 5000,
            "10 seconds": 10000,
            "30 seconds": 30000
        }
        
        interval_ms = interval_map.get(interval_text, 3000)  # Default to 3 seconds
        self.refresh_interval = interval_ms
        
        # Update battery manager interval
        self.battery_manager.set_monitoring_interval(interval_ms)
        
        logger.debug(f"Battery Monitor: Interval changed to {interval_ms}ms")
    
    @Slot()
    def _on_monitoring_started(self):
        """Handle monitoring started"""
        self.is_monitoring = True
        
        # Update UI state
        self.ui_components["refresh_once_button"].setEnabled(False)
        self.ui_components["interval_combo"].setEnabled(False)
        
        logger.info("Battery Monitor: Monitoring started")
    
    @Slot()
    def _on_monitoring_completed(self):
        """Handle monitoring completed"""
        self.is_monitoring = False
        
        # Update UI state
        self.ui_components["refresh_once_button"].setEnabled(True)
        self.ui_components["interval_combo"].setEnabled(True)
        
        logger.info("Battery Monitor: Monitoring completed")
    
    @Slot(str)
    def _on_monitoring_error(self, error_message: str):
        """Handle monitoring error"""
        logger.error(f"Battery Monitor: Error - {error_message}")
        
        # Update status
        self.ui_components["status_label"].setText(f"Error: {error_message}")
        self.ui_components["status_label"].setStyleSheet("""
            QLabel {
                background-color: #4A1515;
                border: 1px solid #661111;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
                color: #FF6B6B;
            }
        """)
    
    def get_current_battery_data(self) -> Dict[str, Any]:
        """Get current battery data"""
        return self.battery_manager.get_current_battery_data()
    
    def get_battery_history(self) -> list:
        """Get battery history data"""
        return self.battery_manager.get_battery_history()
    
    def closeEvent(self, event):
        """Handle window close event"""
        logger.info("Battery Monitor Widget closing")
        
        # Stop monitoring if active
        if self.is_monitoring:
            self.battery_manager.stop_monitoring()
        
        # Cleanup resources
        self.battery_manager.cleanup()
        self.battery_service.cleanup()
        
        # Emit closing signal
        self.window_closing.emit()
        
        # Accept close event
        event.accept()
    
    def show_widget(self):
        """Show the widget and get initial data"""
        # Show the window
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Get initial battery reading
        QTimer.singleShot(500, self._on_refresh_once)
        
        logger.info("Battery Monitor Widget shown") 