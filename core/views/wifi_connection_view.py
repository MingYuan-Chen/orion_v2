import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, Signal, QTimer
from PySide6.QtGui import QMouseEvent
from core.view_models.device_view_model import DeviceViewModel

class WifiNetworkItem(QFrame):
    """
    A widget representing a single WiFi network in the list.
    Expandable to show password field and connect button.
    """
    connect_requested = Signal(str, str) # ssid, password

    def __init__(self, ssid, signal, security, parent=None):
        super().__init__(parent)
        self.ssid = ssid
        self.security = security
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #3b3b3b; border-radius: 5px; margin-bottom: 5px;")
        
        self.main_layout = QVBoxLayout(self)
        self.header_layout = QHBoxLayout()
        
        # Header info
        self.ssid_label = QLabel(f"{ssid} ({signal}%)")
        self.ssid_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.security_label = QLabel(security)
        self.security_label.setStyleSheet("color: #aaa;")
        
        self.header_layout.addWidget(self.ssid_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.security_label)
        
        # Expandable content
        self.details_widget = QWidget()
        self.details_layout = QHBoxLayout(self.details_widget)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFixedSize(80, 30)
        self.connect_button.clicked.connect(self.on_connect_clicked)
        
        self.details_layout.addWidget(self.password_input)
        self.details_layout.addWidget(self.connect_button)
        
        self.details_widget.setVisible(False)
        
        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addWidget(self.details_widget)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Toggle details on click."""
        if event.button() == Qt.LeftButton:
            self.details_widget.setVisible(not self.details_widget.isVisible())
            # Don't consume event so parent can handle if needed, but here it's fine.
            super().mousePressEvent(event)

    def on_connect_clicked(self):
        password = self.password_input.text()
        self.connect_requested.emit(self.ssid, password)


class WifiConnectionView(QWidget):
    """
    View for scanning and connecting to WiFi networks.
    """
    def __init__(self, view_model: DeviceViewModel):
        super().__init__()
        self._vm = view_model
        self.setWindowTitle("WiFi Connection")
        self.setGeometry(200, 200, 400, 500)
        
        # Layouts
        self.main_layout = QVBoxLayout(self)
        self.top_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Scan WiFi")
        self.scan_button.clicked.connect(self.on_scan_button_clicked)
        self.status_label = QLabel("Status: Unknown")
        
        self.top_layout.addWidget(self.scan_button)
        self.top_layout.addWidget(self.status_label)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.scroll_area)
        
        # Connections
        self._vm.wifi_scan_finished.connect(self.on_scan_finished)
        self._vm.wifi_connection_result.connect(self.on_connection_result)
        self._vm.wifi_status_updated.connect(self.on_status_updated)
        
        # Auto scan on open? Maybe
        # self._vm.scan_wifi()

    @Slot(list)
    def on_scan_finished(self, networks: list):
        # Clear existing
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if not networks:
            self.status_label.setText("No networks found")
            return

        self.status_label.setText(f"Found {len(networks)} networks")
        
        for net in networks:
            item = WifiNetworkItem(net['ssid'], net['signal'], net['security'])
            item.connect_requested.connect(self._vm.connect_wifi)
            self.scroll_layout.addWidget(item)

    @Slot(bool, str)
    def on_connection_result(self, success: bool, message: str):
        if success:
            self.status_label.setText("Connected!")
        else:
            self.status_label.setText("Connection failed.")
        # Re-check status
        self._vm.check_wifi_status()
 
    @Slot()
    def on_scan_button_clicked(self):
        self.status_label.setText("Scanning...")
        self._vm.scan_wifi()
    
    @Slot(dict)
    def on_status_updated(self, status: dict):
        if status.get('connected'):
            self.status_label.setText(f"Connected to: {status.get('ssid')} ({status.get('ip')})")
        else:
            self.status_label.setText("Disconnected")
            
    @Slot()
    def start_scan(self):
        self.status_label.setText("Scanning...")
        self._vm.scan_wifi()

    def showEvent(self, event):
        super().showEvent(event)
        self._vm.check_wifi_status()
        # Delay scan to allow window to show up and repaint first
        QTimer.singleShot(100, self.start_scan)
