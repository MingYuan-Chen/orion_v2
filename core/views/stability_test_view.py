from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QRadioButton, QButtonGroup, QLineEdit, QSpacerItem, 
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QPainter, QBrush, QColor, QIntValidator
from core.view_models.device_view_model import DeviceViewModel

class LEDIndicator(QWidget):
    """
    A specific LED indicator widget.
    Colors: Red (Disconnected), Green (Connected), Gray (Unknown).
    """
    def __init__(self, size=15, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor("gray")

    def set_status(self, connected: bool):
        self._color = QColor("green") if connected else QColor("red")
        self.update()
    
    def set_color(self, color_name: str):
        self._color = QColor(color_name)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

class StabilityTestView(QWidget):
    """
    View for stability testing (Ping test, etc).
    """
    def __init__(self, view_model: DeviceViewModel, parent=None):
        super().__init__(parent)
        self._vm = view_model
        self._wifi_view = None
        self.setWindowTitle("Stability Test")
        self.resize(600, 400)
        self._setup_ui()
        self._setup_bindings()

        # Timer to poll network status when this view is visible
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._vm.check_network_status)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Network Frame
        network_frame = QFrame()
        network_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        network_layout = QVBoxLayout(network_frame)
        main_layout.addWidget(network_frame)

        # Row 1: Status Row (Label + LEDs)
        status_row = QHBoxLayout()
        status_label = QLabel("Network")
        status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_row.addWidget(status_label)
        status_row.addSpacing(20)

        # Ethernet Status
        self.eth_led = LEDIndicator()
        self.eth_label = QLabel("Ethernet: Unknown")
        status_row.addWidget(self.eth_led)
        status_row.addWidget(self.eth_label)
        status_row.addSpacing(15)

        # WiFi Status
        self.wifi_led = LEDIndicator()
        self.wifi_label = QLabel("WiFi: Unknown")
        status_row.addWidget(self.wifi_led)
        status_row.addWidget(self.wifi_label)
        
        status_row.addStretch()
        network_layout.addLayout(status_row)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        network_layout.addWidget(line)

        # 2. Ping Test Frame (inside Network Frame)
        ping_test_frame = QFrame()
        ping_test_layout = QVBoxLayout(ping_test_frame)
        network_layout.addWidget(ping_test_frame)

        # Row 1: Type, Duration, Address
        row1_layout = QHBoxLayout()
        
        # Radio Buttons
        self.rb_ethernet = QRadioButton("Ethernet")
        self.rb_wifi = QRadioButton("WiFi")
        self.rb_ethernet.setChecked(True) # Default
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_ethernet)
        self.btn_group.addButton(self.rb_wifi)
        
        row1_layout.addWidget(QLabel("Type:"))
        row1_layout.addWidget(self.rb_ethernet)
        row1_layout.addWidget(self.rb_wifi)
        row1_layout.addSpacing(20)

        # Duration
        row1_layout.addWidget(QLabel("Duration (s):"))
        self.txt_duration = QLineEdit("3600")
        self.txt_duration.setFixedWidth(60)
        self.txt_duration.setValidator(QIntValidator(1, 999999))
        row1_layout.addWidget(self.txt_duration)
        row1_layout.addSpacing(20)

        # Address
        row1_layout.addWidget(QLabel("Ping Address:"))
        self.txt_address = QLineEdit("8.8.8.8")
        self.txt_address.setFixedWidth(100)
        row1_layout.addWidget(self.txt_address)
        
        row1_layout.addStretch()
        ping_test_layout.addLayout(row1_layout)

        # Row 2: Target Detail
        row2_layout = QHBoxLayout()
        self.lbl_target_detail = QLabel("Target: Ethernet - IP: Unknown")
        row2_layout.addWidget(self.lbl_target_detail)
        
        self.btn_select_ap = QPushButton("Select AP...")
        self.btn_select_ap.setVisible(False)
        self.btn_select_ap.clicked.connect(self.open_wifi_view)
        row2_layout.addWidget(self.btn_select_ap)
        
        row2_layout.addStretch()
        ping_test_layout.addLayout(row2_layout)

        # Row 3: Start Button
        row3_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setFixedWidth(100)
        row3_layout.addWidget(self.btn_start)
        row3_layout.addStretch()
        ping_test_layout.addLayout(row3_layout)

        # Spacer
        main_layout.addStretch()

        # Connect internal signals
        self.btn_group.buttonClicked.connect(self.update_target_detail)

    def _setup_bindings(self):
        self._vm.network_status_updated.connect(self.update_status)

    @Slot(dict)
    def update_status(self, status: dict):
        # Ethernet
        eth_info = status.get("ethernet", {})
        eth_connected = eth_info.get("state") == "connected"
        self.eth_led.set_status(eth_connected)
        self.eth_ip = eth_info.get('ip', '')
        if eth_connected:
            self.eth_label.setText(f"Ethernet: {self.eth_ip}")
        else:
            self.eth_label.setText("Ethernet: Disconnected")

        # WiFi
        wifi_info = status.get("wifi", {})
        wifi_connected = wifi_info.get("state") == "connected"
        self.wifi_led.set_status(wifi_connected)
        self.wifi_ssid = wifi_info.get('connection', '')
        if wifi_connected:
            self.wifi_label.setText(f"WiFi: {self.wifi_ssid}")
        else:
            self.wifi_label.setText("WiFi: Disconnected")

        self.update_target_detail()

    @Slot()
    def update_target_detail(self):
        if self.rb_ethernet.isChecked():
            self.lbl_target_detail.setText(f"Target: Ethernet - IP: {getattr(self, 'eth_ip', 'Unknown')}")
            self.btn_select_ap.setVisible(False)
        else:
            self.lbl_target_detail.setText("Target: WiFi")
            self.btn_select_ap.setVisible(True)

    @Slot()
    def open_wifi_view(self):
        if self._wifi_view is None:
            from core.views.wifi_connection_view import WifiConnectionView
            self._wifi_view = WifiConnectionView(self._vm)
        self._wifi_view.show()

    def showEvent(self, event):
        super().showEvent(event)
        self._status_timer.start(60000) # Poll every 60 seconds
        QTimer.singleShot(100, self._vm.check_network_status) # Immediate check

    def closeEvent(self, event):
        self._status_timer.stop()
        if self._wifi_view:
            self._wifi_view.close()
        super().closeEvent(event)
