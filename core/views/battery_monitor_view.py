from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from core.view_models.device_view_model import DeviceViewModel

class BatteryMonitorView(QWidget):
    """
    View to display battery monitor information.
    """
    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Battery Monitor")
        self.resize(400, 300)
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Battery Status")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Info Grid
        self.info_grid = QGridLayout()
        main_layout.addLayout(self.info_grid)

        # Labels for specific keys
        self.labels = {}
        keys = [
            ("Voltage", "voltage"),
            ("Current", "current"),
            ("Relative State", "relative_state"),
            ("Temperature", "temperature"),
            ("Battery Status", "battery_status"),
            ("LED Status", "led_status"),
            ("Interrupt Status", "interrupt_status"),
            ("CPU Usage", "cpu_usage"),
            ("Memory Usage", "memory_usage")
        ]

        for i, (display_name, key) in enumerate(keys):
            name_label = QLabel(f"{display_name}:")
            name_label.setFont(QFont("Arial", 10, QFont.Bold))
            value_label = QLabel("N/A")
            value_label.setFont(QFont("Arial", 10))
            
            self.info_grid.addWidget(name_label, i, 0)
            self.info_grid.addWidget(value_label, i, 1)
            self.labels[key] = value_label

        main_layout.addStretch()

    def _setup_bindings(self):
        self._vm.battery_data_updated.connect(self.on_battery_data_updated)

    @Slot(dict)
    def on_battery_data_updated(self, data: dict):
        for key, value in data.items():
            if key == "top_info" and isinstance(value, dict):
                 if "cpu_usage" in value:
                     self.labels["cpu_usage"].setText(str(value["cpu_usage"]))
                 if "memory_usage" in value:
                     self.labels["memory_usage"].setText(str(value["memory_usage"]))
            elif key in self.labels:
                self.labels[key].setText(str(value))

    def showEvent(self, event):
        """Start monitoring when view is shown."""
        super().showEvent(event)
        self._vm.start_battery_monitor()

    def closeEvent(self, event):
        """Stop monitoring when view is closed."""
        self._vm.stop_battery_monitor()
        super().closeEvent(event)
