from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QTextEdit
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
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.table)

    def _setup_bindings(self):
        self._vm.diagnostic_result.connect(self.on_diagnostic_result)
        self._vm.diagnostic_start.connect(self.on_diagnostic_start)
        self._vm.all_diagnostics_completed.connect(self.on_all_diagnostics_completed)
        self._vm.manual_check_requested.connect(self.on_manual_check_requested)
        self._vm.diagnostic_reset.connect(self.reset)

    @Slot(str)
    def on_diagnostic_start(self, key: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Module Name
        display_name = key.replace("diagnostic_", "").replace("_", " ").title()
        self.table.setItem(row, 0, QTableWidgetItem(display_name))
        
        # Initialize Result and Message as empty/pending
        self.table.setItem(row, 1, QTableWidgetItem("Running..."))
        self.table.setItem(row, 2, QTableWidgetItem(""))
        
        self.table.scrollToBottom()

    @Slot(str, bool, str)
    def on_diagnostic_result(self, key: str, success: bool, message: str):
        row = self.table.rowCount() - 1
        if row < 0:
            return

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

    @Slot(str, str)
    def on_manual_check_requested(self, key: str, message: str):
        from PySide6.QtWidgets import QMessageBox
        
        # Show dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Manual Check Required")
        msg_box.setText(message)

        if "[Precondition]" in message:
            ok_btn = msg_box.addButton("Ok", QMessageBox.AcceptRole)
        else:
            pass_btn = msg_box.addButton("Pass", QMessageBox.YesRole)
            fail_btn = msg_box.addButton("Fail", QMessageBox.NoRole)
        
        msg_box.exec()
        
        if "[Precondition]" in message:
            if msg_box.clickedButton() == ok_btn:
                result = "SKIP"
        else:
            result = "PASS" if msg_box.clickedButton() == pass_btn else "FAIL"
        # Resume diagnostic
        self._vm.resume_diagnostic(result)

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
