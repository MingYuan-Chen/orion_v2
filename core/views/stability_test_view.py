from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QRadioButton, QButtonGroup, QLineEdit, QSpacerItem, 
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer, QThreadPool
from PySide6.QtGui import QPainter, QBrush, QColor, QIntValidator
from core.view_models.device_view_model import DeviceViewModel
from core.workers.stability_test_worker import StabilityTestWorker
from core.views.components.ping_test_item import PingTestItem

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
        self.test_items = [] # List to store PingTestItem instances
        self.setWindowTitle("Stability Test")
        self.resize(600, 500)
        self._setup_ui()
        self._setup_bindings()

        # Timer to poll network status when this view is visible
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._vm.check_network_status)
        
        # Progress timer
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.elapsed_seconds = 0
        self.total_duration = 0

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top row: Start Button
        top_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setFixedWidth(100)
        top_layout.addWidget(self.btn_start)
        
        self.lbl_progress = QLabel("")
        top_layout.addWidget(self.lbl_progress)
        
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # 1. Network Frame
        network_frame = QFrame()
        network_frame.setObjectName("network_frame") # Set object name for CSS targeting
        network_frame.setStyleSheet("""
            #network_frame {
                border: 1px solid #555;
                border-radius: 6px;
            }
        """)
        network_layout = QVBoxLayout(network_frame)
        main_layout.addWidget(network_frame)

        # Row 1: Status Row (Label + LEDs + Add Button)
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
        
        # Add Button
        self.btn_add_item = QPushButton("+")
        self.btn_add_item.setFixedSize(30, 30)
        self.btn_add_item.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.btn_add_item.setToolTip("Add new test item")
        self.btn_add_item.clicked.connect(self.add_test_item)
        status_row.addWidget(self.btn_add_item)
        
        network_layout.addLayout(status_row)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("border: 1px solid #555; border-radius: 5px;")
        network_layout.addWidget(line)

        # 2. Test Items Area
        # We use a scroll area just in case, or just a vertical layout if items are few
        # Let's stick to layout inside network_frame for now as requested "ping_test_frame wrapped"
        # The user wanted ping_test_frame to be a component.
        # We will add items to this layout.
        self.items_layout = QVBoxLayout()
        network_layout.addLayout(self.items_layout)
        
        # Add one initial item
        self.add_test_item()

        # Spacer
        main_layout.addStretch()

    def add_test_item(self):
        item = PingTestItem()
        item.remove_requested.connect(self.remove_test_item)
        item.request_wifi_selection.connect(self.on_request_wifi_selection)
        self.items_layout.addWidget(item)
        self.test_items.append(item)

    def remove_test_item(self, item):
        if len(self.test_items) > 1: # Keep at least one
            self.items_layout.removeWidget(item)
            item.deleteLater()
            self.test_items.remove(item)
        else:
            # Maybe just clear inputs? Or allow removing if we handle empty start
            pass

    def _setup_bindings(self):
        self._vm.network_status_updated.connect(self.update_status)
        self.btn_start.clicked.connect(self.on_start_clicked)

    @Slot(object)
    def on_request_wifi_selection(self, item):
        self._current_selecting_item = item
        if self._wifi_view is None:
            from core.views.wifi_connection_view import WifiConnectionView
            self._wifi_view = WifiConnectionView(self._vm)
            # Connect the signal from the view
            self._wifi_view.ssid_selected.connect(self.on_wifi_ssid_selected)
        self._wifi_view.show()

    @Slot(str)
    def on_wifi_ssid_selected(self, ssid: str):
        if hasattr(self, '_current_selecting_item') and self._current_selecting_item:
            self._current_selecting_item.set_wifi_ssid(ssid)

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

        # Update status for each test item
        for item in self.test_items:
            item.update_network_status(eth_connected, self.eth_ip, wifi_connected)

    @Slot()
    def on_start_clicked(self):
        if self.btn_start.text() == "Start":
            # Collect Configs
            test_configs = []
            total_duration = 0
            
            for item in self.test_items:
                config = item.get_config()
                # Basic Validation
                if config['duration'] <= 0:
                     self.lbl_progress.setText("Invalid duration in an item")
                     return
                if not config['ip']:
                     self.lbl_progress.setText("Invalid IP in an item")
                     return
                if config['interface_type'] == 'wifi' and not config['ssid']:
                     self.lbl_progress.setText("WiFi SSID missing in an item")
                     return
                
                test_configs.append(config)
                total_duration += config['duration']

            if not test_configs:
                return

            # Start Test
            self.btn_start.setText("Stop")
            self._set_inputs_enabled(False)
            self.lbl_progress.setText("Starting...")
            self.btn_add_item.setEnabled(False)
            
            # Stop status timer to prevent interference with test commands
            self._status_timer.stop()
            
            # Start Worker
            self.worker = StabilityTestWorker(
                self._vm._network_service,
                test_configs
            )
            self.worker.result.connect(self.on_test_finished)
            self.worker.ping_started.connect(self.on_ping_started)
            # worker.signals.error.connect(...) # Can handle error if separate signal needed
            self.worker.start()
            
            # Start Timer
            self.elapsed_seconds = 0
            self.total_duration = total_duration # This is approximate, as there is setup time
            
        else:
            # Stop Test
            # Send interrupt (Ctrl+C)
            self._vm.send_interrupt_bytes(b'\x03')
            self.lbl_progress.setText("Stopping...")
            # The worker will finish when the command is interrupted (hopefully)
            # We don't manually force terminate thread in QThreadPool generally.
            # But run_ping_test should return after interruption.

    def update_progress(self):
        self.elapsed_seconds += 1
        self.lbl_progress.setText(f"{self.elapsed_seconds}/{self.total_duration} s")
        
    @Slot()
    def on_ping_started(self):
        self.progress_timer.start(1000)
        self.update_progress()
        
    def on_test_finished(self, summary: str):
        self.progress_timer.stop()
        self._status_timer.start(60000) # Restart status polling
        
        self.btn_start.setText("Start")
        self._set_inputs_enabled(True)
        self.lbl_progress.setText(summary)

    def _set_inputs_enabled(self, enabled: bool):
        for item in self.test_items:
            item.set_enabled_inputs(enabled)
        self.btn_add_item.setEnabled(enabled)


    def showEvent(self, event):
        super().showEvent(event)
        self._status_timer.start(60000) # Poll every 60 seconds
        QTimer.singleShot(300, self._vm.check_network_status) # Immediate check

    def closeEvent(self, event):
        self._status_timer.stop()
        if self._wifi_view:
            self._wifi_view.close()
        super().closeEvent(event)
