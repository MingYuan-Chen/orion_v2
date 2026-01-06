from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QIcon
from core.view_models.device_view_model import DeviceViewModel

class BatteryMonitorView(QWidget):
    """
    View to display battery monitor information in a table with history.
    """
    MAX_ROW_COUNT = 1000

    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Battery Monitor")
        self.resize(1200, 400)
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Battery Status History")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Table Widget
        self.table = QTableWidget()
        self.columns = [
            "Timestamp", "Duration", "SoC", "Remaining Capacity", "Voltage", "Current",
            "Temperature", "LED Status", "Battery Status", "Safety Status", "AC Present"
        ]
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        
        # Table styling
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        main_layout.addWidget(self.table)

    def _setup_bindings(self):
        self._vm.battery_data_updated.connect(self.on_battery_data_updated)

    @Slot(dict)
    def on_battery_data_updated(self, data: dict):
        # Extract values
        timestamp = str(data.get("timestamp", "Unknown"))
        duration = str(data.get("duration", "Unknown"))
        voltage = str(data.get("voltage", "Unknown"))
        current = str(data.get("current", "Unknown"))
        rel_state = str(data.get("relative_state", "Unknown"))
        remaining_capacity = str(data.get("remaining_capacity", "Unknown"))
        temp = str(data.get("temperature", "Unknown"))
        batt_status = str(data.get("battery_status", "Unknown"))
        led_status = str(data.get("led_status", "Unknown"))
        interrupt = str(data.get("interrupt_status", "Unknown"))
        ac_present = str(data.get("ac_present", "Unknown"))
            
        # Prepare row data
        row_data = [
            timestamp, duration, rel_state, remaining_capacity, voltage, current,
            temp, led_status, batt_status, interrupt, ac_present
        ]

        # Insert new row
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        
        for col_idx, value in enumerate(row_data):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, col_idx, item)

        # Limit row count (FIFO)
        if self.table.rowCount() > self.MAX_ROW_COUNT:
            self.table.removeRow(0)
        
        # Scroll to bottom
        self.table.scrollToBottom()

    def showEvent(self, event):
        """Start monitoring when view is shown."""
        super().showEvent(event)
        self._vm.start_battery_monitor()

    def closeEvent(self, event):
        """Stop monitoring when view is closed."""
        self._vm.stop_battery_monitor()
        self.table.clearContents()
        self.table.setRowCount(0)
        super().closeEvent(event)
