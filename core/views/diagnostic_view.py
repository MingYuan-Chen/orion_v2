from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QColor
from core.view_models.device_view_model import DeviceViewModel

class DiagnosticView(QWidget):
    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Diagnostics")
        self.resize(700, 700)
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFixedWidth(200)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Module", "Result", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.table)

    def _setup_bindings(self):
        self._vm.diagnostic_result.connect(self.on_diagnostic_result)
        self._vm.all_diagnostics_completed.connect(self.on_all_diagnostics_completed)
        self._vm.diagnostic_reset.connect(self.reset)

    @Slot(str, bool, str)
    def on_diagnostic_result(self, key: str, success: bool, message: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Module Name
        # Remove "diagnostic_" prefix for cleaner display if present
        display_name = key.replace("diagnostic_", "").replace("_", " ").title()
        self.table.setItem(row, 0, QTableWidgetItem(display_name))
        
        # Result
        result_str = "PASS" if success else "FAIL"
        result_item = QTableWidgetItem(result_str)
        result_item.setTextAlignment(Qt.AlignCenter)
        
        if success:
            result_item.setForeground(QColor("green"))
            result_item.setBackground(QColor("#E8F5E9")) # Light green background
        else:
            result_item.setForeground(QColor("red"))
            result_item.setBackground(QColor("#FFEBEE")) # Light red background
            
        self.table.setItem(row, 1, result_item)
        
        # Message
        self.table.setItem(row, 2, QTableWidgetItem(message))
        
        self.table.scrollToBottom()

    @Slot()
    def on_all_diagnostics_completed(self):
        self.status_label.setText("Diagnostics Completed")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: green; background-color: lightgreen;")

    def start_diagnostic(self):
        self.table.setRowCount(0)
        self.status_label.setText("Running Diagnostics...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: blue; background-color: lightblue;")
    
    def reset(self):
        self.table.setRowCount(0)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; background-color: #2b2b2b;")

    def closeEvent(self, event):
        self._vm.interrupt_diagnostic()
        self.hide()
        event.ignore()
