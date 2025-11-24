from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from typing import Dict

from core.view_models.device_view_model import DeviceViewModel
from core.services.system_info_service import SystemInfoService

class SystemInfoView(QWidget):
    """
    A view that displays detailed system information collected from the device.
    """
    def __init__(self, view_model: DeviceViewModel, parent: QWidget = None):
        super().__init__(parent)
        self._vm = view_model
        self._labels: Dict[str, QLabel] = {}

        self.setWindowTitle("System Information")
        self.setMinimumSize(700, 600)

        self._setup_ui()
        self._setup_bindings()
        self.update_labels(self._vm.system_info)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        font_bold = QFont()
        font_bold.setBold(True)

        commands = list(SystemInfoService.COMMANDS.keys())
        mid_point = 6 # Split point for 2 columns

        for i, key in enumerate(commands):
            # Title Label (e.g., "Kernel Version")
            title_label = QLabel(key.replace("_", " ").title())
            title_label.setFont(font_bold)
            title_label.setStyleSheet("color: #F5F5F5; padding-top: 5px;")
            
            # Content Label
            content_label = QLabel("N/A")
            content_label.setWordWrap(True)
            content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            content_label.setStyleSheet("background-color: #2E2E2E; border-radius: 4px; padding: 10px; color: #CCCCCC; font-size: 14px;")
            
            self._labels[key] = content_label
            
            target_layout = left_layout if i < mid_point else right_layout
            target_layout.addWidget(title_label)
            target_layout.addWidget(content_label)

        left_layout.addStretch()
        right_layout.addStretch()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

    def _setup_bindings(self):
        self._vm.system_info_changed.connect(self.on_system_info_changed)
        self._vm.system_info_reset.connect(self.on_system_info_reset)

    @Slot(str, str)
    def on_system_info_changed(self, key: str, value: str):
        if key in self._labels:
            self._labels[key].setText(value or "N/A")

    @Slot()
    def on_system_info_reset(self):
        for label in self._labels.values():
            label.setText("N/A")

    @Slot(dict)
    def update_labels(self, info: Dict[str, str]):
        for key, value in info.items():
            if key in self._labels:
                self._labels[key].setText(value or "N/A")

    def closeEvent(self, event):
        # Override close event to just hide the window
        self.hide()
        event.ignore()
