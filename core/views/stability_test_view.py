from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QRadioButton, QButtonGroup, QLineEdit, QSpacerItem, 
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer, QThreadPool
from PySide6.QtGui import QPainter, QBrush, QColor, QIntValidator
from core.view_models.device_view_model import DeviceViewModel
from core.workers.stability_test_worker import StabilityTestWorker

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
        # Timer to poll network status when this view is visible
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._vm.check_network_status)
        
        # ThreadPool for tasks
        self.threadpool = QThreadPool()
        
        # Progress timer
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.elapsed_seconds = 0
        self.total_duration = 0

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
        
        self.txt_wifi_password = QLineEdit()
        self.txt_wifi_password.setPlaceholderText("WiFi Password")
        self.txt_wifi_password.setEchoMode(QLineEdit.Password)
        self.txt_wifi_password.setVisible(False)
        self.txt_wifi_password.setFixedWidth(150)
        row2_layout.addWidget(self.txt_wifi_password)
        
        row2_layout.addStretch()
        ping_test_layout.addLayout(row2_layout)

        # Row 3: Start Button
        row3_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setFixedWidth(100)
        row3_layout.addWidget(self.btn_start)
        
        self.lbl_progress = QLabel("")
        row3_layout.addWidget(self.lbl_progress)
        
        row3_layout.addStretch()
        ping_test_layout.addLayout(row3_layout)

        # Spacer
        main_layout.addStretch()

        # Connect internal signals
        self.btn_group.buttonClicked.connect(self.update_target_detail)

    def _setup_bindings(self):
        self._vm.network_status_updated.connect(self.update_status)
        self.btn_start.clicked.connect(self.on_start_clicked)

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
        
        if wifi_connected:
            self.wifi_label.setText(f"WiFi: {wifi_info.get('connection', '')}")
        else:
            self.wifi_label.setText("WiFi: Disconnected")

        self.update_target_detail()

    @Slot()
    def update_target_detail(self):
        if self.rb_ethernet.isChecked():
            self.lbl_target_detail.setText(f"Target: Ethernet - IP: {getattr(self, 'eth_ip', 'Unknown')}")
            self.btn_select_ap.setVisible(False)
            self.txt_wifi_password.setVisible(False)
        else:
            if getattr(self, 'wifi_ssid', '') not in [None, '']:
                self.lbl_target_detail.setText(f"Target: WiFi - SSID: {self.wifi_ssid}")
            else:
                self.lbl_target_detail.setText("Target: WiFi - SSID: Unknown")
            self.btn_select_ap.setVisible(True)
            self.txt_wifi_password.setVisible(True)

    @Slot()
    def open_wifi_view(self):
        if self._wifi_view is None:
            from core.views.wifi_connection_view import WifiConnectionView
            self._wifi_view = WifiConnectionView(self._vm)
            # Connect the signal from the view
            self._wifi_view.ssid_selected.connect(self.on_wifi_ssid_selected)
        self._wifi_view.show()

    @Slot(str)
    def on_wifi_ssid_selected(self, ssid: str):
        self.wifi_ssid = ssid
        self.update_target_detail()

    @Slot()
    def on_start_clicked(self):
        if self.btn_start.text() == "Start":
            # Validation
            try:
                duration = int(self.txt_duration.text())
            except ValueError:
                self.lbl_progress.setText("Invalid duration")
                return
                
            ip_address = self.txt_address.text()
            if not ip_address:
                self.lbl_progress.setText("Invalid IP")
                return

            ssid = None
            password = None
            if self.rb_wifi.isChecked():
                ssid = getattr(self, 'wifi_ssid', None)
                if not ssid:
                     self.lbl_progress.setText("Select WiFi AP")
                     return
                password = self.txt_wifi_password.text()

            # Start Test
            self.btn_start.setText("Stop")
            self._set_inputs_enabled(False)
            self.lbl_progress.setText("Starting...")
            
            # Start Worker
            # Start Worker
            self.worker = StabilityTestWorker(
                self._vm._network_service,
                duration,
                ip_address,
                ssid,
                password
            )
            self.worker.result.connect(self.on_test_finished)
            # worker.signals.error.connect(...) # Can handle error if separate signal needed
            self.worker.start()
            
            # Start Timer
            self.elapsed_seconds = 0
            self.total_duration = duration
            self.progress_timer.start(1000)
            self.update_progress()
            
        else:
            # Stop Test
            # Send interrupt (Ctrl+C)
            self._vm.send_interrupt_bytes(b'\x03')
            self.lbl_progress.setText("Stopping...")
            # The worker will finish when the command is interrupted (hopefully)
            # We don't manually force terminate thread in QThreadPool generally.
            # But run_ping_test should return after interruption.

    def update_progress(self):
        self.lbl_progress.setText(f"{self.elapsed_seconds}/{self.total_duration} s")
        self.elapsed_seconds += 1
        
    def on_test_finished(self, summary: str):
        self.progress_timer.stop()
        self.btn_start.setText("Start")
        self._set_inputs_enabled(True)
        self.lbl_progress.setText(summary)

    def _set_inputs_enabled(self, enabled: bool):
        self.rb_ethernet.setEnabled(enabled)
        self.rb_wifi.setEnabled(enabled)
        self.txt_duration.setEnabled(enabled)
        self.txt_address.setEnabled(enabled)
        self.btn_select_ap.setEnabled(enabled)
        self.txt_wifi_password.setEnabled(enabled)


    def showEvent(self, event):
        super().showEvent(event)
        self._status_timer.start(60000) # Poll every 60 seconds
        QTimer.singleShot(200, self._vm.check_network_status) # Immediate check

    def closeEvent(self, event):
        self._status_timer.stop()
        if self._wifi_view:
            self._wifi_view.close()
        super().closeEvent(event)
