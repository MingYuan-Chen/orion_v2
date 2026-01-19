from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QRadioButton, QButtonGroup, QLineEdit
)
from PySide6.QtCore import Slot, Signal
from PySide6.QtGui import QIntValidator

class PingTestItem(QFrame):
    """
    Component for a single Ping Test configuration.
    """
    remove_requested = Signal(QWidget) # Signal to remove itself

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wifi_ssid = None
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        self.setObjectName("ping_test_item")
        # Apply style to this frame
        self.setStyleSheet("""
            #ping_test_item {
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #2b2b2b;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Row 1: Type Selection + Close Button
        row1_layout = QHBoxLayout()
        
        self.rb_ethernet = QRadioButton("Ethernet")
        self.rb_wifi = QRadioButton("WiFi")
        self.rb_ethernet.setChecked(True)
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_ethernet)
        self.btn_group.addButton(self.rb_wifi)
        
        row1_layout.addWidget(QLabel("Type:"))
        row1_layout.addWidget(self.rb_ethernet)
        row1_layout.addWidget(self.rb_wifi)
        row1_layout.addStretch()
        
        # Remove button
        self.btn_remove = QPushButton("✖")
        self.btn_remove.setFixedSize(24, 24)
        self.btn_remove.setStyleSheet("QPushButton { border: none; font-weight: bold; color: #888; } QPushButton:hover { color: red; }")
        self.btn_remove.setToolTip("Remove this test item")
        row1_layout.addWidget(self.btn_remove)
        
        layout.addLayout(row1_layout)
        
        # Row 2: Configuration
        row2_layout = QHBoxLayout()
        
        # Duration
        row2_layout.addWidget(QLabel("Duration (s):"))
        self.txt_duration = QLineEdit("60")
        self.txt_duration.setFixedWidth(60)
        self.txt_duration.setValidator(QIntValidator(1, 999999))
        row2_layout.addWidget(self.txt_duration)
        row2_layout.addSpacing(15)

        # Address
        row2_layout.addWidget(QLabel("Ping Address:"))
        self.txt_address = QLineEdit("8.8.8.8")
        self.txt_address.setFixedWidth(100)
        row2_layout.addWidget(self.txt_address)
        
        row2_layout.addStretch()
        layout.addLayout(row2_layout)

        # Row 3: WiFi Details (Hidden by default)
        row3_layout = QHBoxLayout()
        self.lbl_target_detail = QLabel("Target: Ethernet")
        row3_layout.addWidget(self.lbl_target_detail)
        
        self.btn_select_ap = QPushButton("Select AP...")
        self.btn_select_ap.setVisible(False)
        row3_layout.addWidget(self.btn_select_ap)
        
        self.txt_wifi_password = QLineEdit()
        self.txt_wifi_password.setPlaceholderText("WiFi Password")
        self.txt_wifi_password.setEchoMode(QLineEdit.Password)
        self.txt_wifi_password.setVisible(False)
        self.txt_wifi_password.setFixedWidth(150)
        row3_layout.addWidget(self.txt_wifi_password)
        
        row3_layout.addStretch()
        layout.addLayout(row3_layout)

    def _setup_connections(self):
        self.btn_group.buttonClicked.connect(self.update_target_detail)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        # Logic for opening existing wifi view is tricky if we don't have reference to it.
        # We can expose a signal 'request_wifi_selection' and let the main view handle it.
        # But for now, let's assume we can pass the Wifi View opening callback or signal.
        
    # We need a signal to request WiFi AP selection from the main view
    request_wifi_selection = Signal(object) # passes self to identify which item requested it

    def _setup_connections(self):
        self.btn_group.buttonClicked.connect(self.update_target_detail)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        self.btn_select_ap.clicked.connect(lambda: self.request_wifi_selection.emit(self))

    @Slot()
    def update_target_detail(self):
        if self.rb_ethernet.isChecked():
            ip = getattr(self, 'eth_ip', 'Unknown')
            self.lbl_target_detail.setText(f"Target: Ethernet - IP: {ip}")
            self.btn_select_ap.setVisible(False)
            self.txt_wifi_password.setVisible(False)
        else:
            ssid = self.wifi_ssid if self.wifi_ssid else "Unknown"
            self.lbl_target_detail.setText(f"Target: WiFi - SSID: {ssid}")
            self.btn_select_ap.setVisible(True)
            self.txt_wifi_password.setVisible(True)

    def update_network_status(self, eth_connected: bool, eth_ip: str, wifi_connected: bool):
        self.eth_ip = eth_ip if eth_connected else "Unknown"
        self.update_target_detail()

    def set_wifi_ssid(self, ssid: str):
        self.wifi_ssid = ssid
        self.update_target_detail()

    def get_config(self) -> dict:
        """Returns the configuration for this test item."""
        config = {
            "type": "ping",
            "duration": int(self.txt_duration.text()) if self.txt_duration.text() else 0,
            "ip": self.txt_address.text(),
            "interface_type": "wifi" if self.rb_wifi.isChecked() else "ethernet"
        }
        
        if config["interface_type"] == "wifi":
            config["ssid"] = self.wifi_ssid
            config["password"] = self.txt_wifi_password.text()
        else:
            config["ssid"] = None
            config["password"] = None
            
        return config

    def set_enabled_inputs(self, enabled: bool):
        self.rb_ethernet.setEnabled(enabled)
        self.rb_wifi.setEnabled(enabled)
        self.txt_duration.setEnabled(enabled)
        self.txt_address.setEnabled(enabled)
        self.btn_select_ap.setEnabled(enabled)
        self.txt_wifi_password.setEnabled(enabled)
        self.btn_remove.setEnabled(enabled)
