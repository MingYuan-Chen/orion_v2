from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
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
        self.setMinimumSize(600, 800)

        self._setup_ui()
        self._setup_bindings()
        self.update_labels(self._vm.system_info)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        
        font_bold = QFont()
        font_bold.setBold(True)

        for key in SystemInfoService.COMMANDS.keys():
            # Title Label (e.g., "Kernel Version")
            title_label = QLabel(key.replace("_", " ").title())
            title_label.setFont(font_bold)
            title_label.setStyleSheet("color: #F5F5F5; padding-top: 10px;")
            
            # Content Label
            content_label = QLabel("N/A")
            content_label.setWordWrap(True)
            content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            content_label.setStyleSheet("background-color: #2E2E2E; border-radius: 4px; padding: 5px; color: #CCCCCC;")
            
            self._labels[key] = content_label
            
            layout.addWidget(title_label)
            layout.addWidget(content_label)

        layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _setup_bindings(self):
        self._vm.system_info_changed.connect(self.on_system_info_changed)

    @Slot(str, str)
    def on_system_info_changed(self, key: str, value: str):
        if key in self._labels:
            self._labels[key].setText(value or "N/A")

    @Slot(dict)
    def update_labels(self, info: Dict[str, str]):
        for key, value in info.items():
            if key in self._labels:
                self._labels[key].setText(value or "N/A")

    def closeEvent(self, event):
        # Override close event to just hide the window
        self.hide()
        event.ignore()
