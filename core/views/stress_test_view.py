from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QGroupBox, QComboBox, QLineEdit, 
                               QFormLayout, QMessageBox)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIntValidator

from core.view_models.device_view_model import DeviceViewModel

class StressTestView(QWidget):
    """
    View for configuring and monitoring Stress Test.
    """
    def __init__(self, view_model: DeviceViewModel, parent: QWidget = None):
        super().__init__(parent)
        self._vm = view_model
        self._is_running = False
        
        self.setWindowTitle("Stress Test")
        self.setMinimumSize(400, 500)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        self._setup_ui()
        self._setup_bindings()
        
        # Initial check for free memory
        QTimer.singleShot(500, self._refresh_free_memory)

    def _setup_ui(self):
        # Common style for GroupBoxes to prevent title clipping
        group_style = """
            QGroupBox {
                margin-top: 15px;
                font-weight: bold;
                border: 1px solid gray;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
            }
        """

        # --- Settings Block ---
        self.settings_group = QGroupBox("Configuration")
        self.settings_group.setStyleSheet(group_style)
        settings_layout = QFormLayout()
        
        # CPU Selection
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(["100", "75", "50", "25"])
        self.cpu_combo.setCurrentText("100")
        settings_layout.addRow("CPU Loading (%):", self.cpu_combo)
        
        # Memory Input
        mem_layout = QHBoxLayout()
        self.mem_input = QLineEdit()
        self.mem_input.setPlaceholderText("MB")
        self.mem_input.setValidator(QIntValidator(0, 100000)) # Reasonable limits
        self.mem_input.setText("3072") # Default
        mem_layout.addWidget(self.mem_input)
        
        self.free_mem_label = QLabel("Free: N/A MB")
        self.free_mem_label.setStyleSheet("color: gray;")
        mem_layout.addWidget(self.free_mem_label)
        
        # It may confuse user to have a refresh button, so it is disabled for now.
        # self.refresh_mem_btn = QPushButton("↻")
        # self.refresh_mem_btn.setFixedSize(40, 40)
        # self.refresh_mem_btn.clicked.connect(self._refresh_free_memory)
        # mem_layout.addWidget(self.refresh_mem_btn)
        
        settings_layout.addRow("Memory Loading (MB):", mem_layout)
        
        # Start/Stop Button
        self.toggle_btn = QPushButton("Start Stress Test")
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        settings_layout.addRow(self.toggle_btn)
        
        self.settings_group.setLayout(settings_layout)
        self.main_layout.addWidget(self.settings_group)
        
        
        # --- Monitoring Block ---
        self.monitor_group = QGroupBox("Monitoring")
        self.monitor_group.setStyleSheet(group_style)
        monitor_layout = QFormLayout()
        
        self.lbl_timestamp = QLabel("N/A")
        self.lbl_duration = QLabel("0s")
        self.lbl_cpu = QLabel("0.0%")
        self.lbl_mem = QLabel("0.0%")
        self.lbl_temp = QLabel("Unknown")
        
        monitor_layout.addRow("Timestamp:", self.lbl_timestamp)
        monitor_layout.addRow("Duration:", self.lbl_duration)
        monitor_layout.addRow("CPU Usage:", self.lbl_cpu)
        monitor_layout.addRow("Memory Usage:", self.lbl_mem)
        monitor_layout.addRow("Temperature:", self.lbl_temp)
        
        self.monitor_group.setLayout(monitor_layout)
        self.main_layout.addWidget(self.monitor_group)
        
        self.main_layout.addStretch()

    def _setup_bindings(self):
        self._vm.stress_test_status_updated.connect(self._on_status_updated)

    @Slot()
    def _refresh_free_memory(self):
        free_mb = self._vm.get_free_memory_mb()
        self.free_mem_label.setText(f"Free: {free_mb} MB")

    @Slot()
    def _on_toggle_clicked(self):
        if not self._is_running:
            # Start
            try:
                cpu_load = int(self.cpu_combo.currentText())
                mem_load = int(self.mem_input.text())
                
                self._vm.start_stress_test(cpu_load, mem_load)
                
                self._is_running = True
                self.toggle_btn.setText("Stop Stress Test")
                
                # Lock settings individually
                self.cpu_combo.setEnabled(False)
                self.mem_input.setEnabled(False)
                # self.refresh_mem_btn.setEnabled(False)
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers.")
        else:
            # Stop
            self._vm.stop_stress_test()
            self._is_running = False
            self.toggle_btn.setText("Start Stress Test")
            
            # Unlock settings
            self.cpu_combo.setEnabled(True)
            self.mem_input.setEnabled(True)
            # self.refresh_mem_btn.setEnabled(True)

    @Slot(dict)
    def _on_status_updated(self, status: dict):
        self.lbl_timestamp.setText(status.get("timestamp", "N/A"))
        self.lbl_duration.setText(status.get("duration", "N/A"))
        self.lbl_cpu.setText(f"{status.get('cpu_usage', 0)}%")
        self.lbl_mem.setText(f"{status.get('memory_usage', 0)}%")
        self.lbl_temp.setText(f"{status.get('temperature', 'Unknown')}°C")
