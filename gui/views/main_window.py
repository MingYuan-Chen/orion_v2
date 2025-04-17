import os
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
from PySide6.QtGui import QIcon
from gui.view_models.usb_view_model import UsbViewModel
from gui.view_models.emmc_view_model import EmmcViewModel
from gui.view_models.eeprom_view_model import EepromViewModel
from gui.view_models.command_view_model import CommandViewModel
from gui.views.battery_dashboard_view import BatteryDashboardView
from util.logger import logger
import sys
from PySide6.QtCore import Slot

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._load_ui()
        self._setup_view_model()
        self._setup_connections()
        
        # initialize battery dashboard view
        self.battery_dashboard = None
        
    def _load_ui(self):
        """Load the UI file"""
        try:
            # Get base path
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Load UI file
            ui_path = os.path.join(base_path, 'gui/ui/main_window.ui')
            ui_file = QFile(ui_path)
            if not ui_file.open(QFile.ReadOnly):
                raise Exception(f"Cannot open {ui_path}: {ui_file.errorString()}")
            
            loader = QUiLoader()
            self.ui = loader.load(ui_file, self)
            ui_file.close()
            
            # Set central widget
            self.setCentralWidget(self.ui.centralwidget)
            
            # Set window icon
            icon_path = os.path.join(base_path, 'resources/icons/header.ico')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                logger.warning(f"Window icon not found at {icon_path}")
            
            # Set window title
            self.setWindowTitle("DqaTestTool")
            
            self.resize(400, 580)
            
        except Exception as e:
            logger.error(f"Failed to load UI: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load UI: {str(e)}")
            raise
        
    def _setup_view_model(self):
        """Setup the view model"""
        # 只初始化 command_view_model
        self.command_view_model = CommandViewModel()
        
        # 其他 ViewModel 將在各自的按鈕點擊事件中按需創建
        self.usb_view_model = None
        self.emmc_view_model = None
        self.eeprom_view_model = None
        
    def _setup_connections(self):
        """Setup signal connections"""
        # Connect Test buttons
        self.ui.push_button_usb_test.clicked.connect(self._on_push_button_usb_test_clicked)
        self.ui.push_button_emmc_test.clicked.connect(self._on_push_button_emmc_test_clicked)
        self.ui.push_button_eeprom_test.clicked.connect(self._on_push_button_eeprom_test_clicked)
        
        # Connect Battery Dashboard button
        if hasattr(self.ui, 'push_button_open_battery_dashboard'):
            self.ui.push_button_open_battery_dashboard.clicked.connect(self._on_open_battery_dashboard)
        else:
            logger.warning("UI button 'push_button_open_battery_dashboard' not found.")
        
        # Connect Send Command button
        self.ui.push_button_send_command.clicked.connect(self._on_send_command_clicked)
        
        # press enter key to send command
        self.ui.line_edit_command.returnPressed.connect(self._on_send_command_clicked)
        
        # Connect/Disconnect Buttons
        if hasattr(self.ui, 'push_button_create_connection'):
             self.ui.push_button_create_connection.clicked.connect(self._on_connect_device_clicked)
             self.ui.push_button_create_connection.setEnabled(True)
        else:
             logger.warning("UI button 'push_button_create_connection' not found.")
             
        if hasattr(self.ui, 'push_button_disconnect'):
             self.ui.push_button_disconnect.clicked.connect(self.command_view_model.disconnect_device)
             self.ui.push_button_disconnect.setEnabled(False)
        else:
             logger.warning("UI button 'push_button_disconnect' not found.")
             
        if hasattr(self.ui, 'push_button_send_command'):
             self.ui.push_button_send_command.setEnabled(False)
        if hasattr(self.ui, 'line_edit_command'):
             self.ui.line_edit_command.setEnabled(False)
             
        # Initialize combo boxes
        self._init_combo_boxes()
        
        # Connect Command view model signals
        self.command_view_model.message_received.connect(self._on_log_message)
        self.command_view_model.worker_connected.connect(self._on_worker_connected)
        self.command_view_model.worker_disconnected.connect(self._on_worker_disconnected)
        self.command_view_model.worker_connection_error.connect(self._on_worker_connection_error)
    
    def _init_combo_boxes(self):
        """Initialize combo boxes with values"""
        # Initialize port combo box
        if hasattr(self.ui, 'combo_box_port'):
            # Add commonly used COM ports
            self.ui.combo_box_port.clear()
            com_ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]
            self.ui.combo_box_port.addItems(com_ports)
            self.ui.combo_box_port.setCurrentText("COM4")  # Default value
        
        # Initialize baudrate combo box
        if hasattr(self.ui, 'combo_box_baudrate'):
            # Add common baudrates
            self.ui.combo_box_baudrate.clear()
            baudrates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
            self.ui.combo_box_baudrate.addItems(baudrates)
            self.ui.combo_box_baudrate.setCurrentText("115200")  # Default value
        
        # Initialize latency combo box
        if hasattr(self.ui, 'combo_box_latency'):
            # Add latency values
            self.ui.combo_box_latency.clear()
            latencies = ["0", "1", "2", "3", "5", "10"]
            self.ui.combo_box_latency.addItems(latencies)
            self.ui.combo_box_latency.setCurrentText("3")  # Default value
    
    def _on_connect_device_clicked(self):
        """Handle Connect Device button clicked"""
        # Get selected values from combo boxes
        port = self.ui.combo_box_port.currentText()
        baudrate = int(self.ui.combo_box_baudrate.currentText())
        latency = int(self.ui.combo_box_latency.currentText())
        
        # Call CommandViewModel with the selected values
        self.command_view_model.connect_device(port, baudrate, latency)

    def _on_send_command_clicked(self):
        """Handle Send Command button clicked"""
        command = self.ui.line_edit_command.text()
        # Pass the command to the CommandViewModel for processing
        self.command_view_model.process_command(command)
        # Optionally clear the line edit after sending
        self.ui.line_edit_command.clear()

    def _on_log_message(self, message: str, color: str = "black", bold: bool = False):
        """Handle log message"""
        try:
            # convert \n to <br>
            message = message.replace('\n', '<br>')
            
            # Use HTML format to support color and bold text
            html_message = f'<span style="color: {color}; font-weight: {"bold" if bold else "normal"}">{message}</span>'
            self.ui.plain_text_edit_info_console.appendHtml(html_message)
            
            # Get scrollbar and set to maximum value
            scrollbar = self.ui.plain_text_edit_info_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # Ensure text area is updated
            self.ui.plain_text_edit_info_console.update()
            
        except Exception as e:
            logger.error(f"Failed to append message: {str(e)}")
        
    def _on_test_started(self):
        """Handle test started"""
        self.ui.push_button_usb_test.setEnabled(False)
        self.ui.push_button_emmc_test.setEnabled(False)
        self.ui.push_button_eeprom_test.setEnabled(False)
        
    def _on_test_finished(self):
        """Handle test finished"""
        self.ui.push_button_usb_test.setEnabled(True)
        self.ui.push_button_emmc_test.setEnabled(True)
        self.ui.push_button_eeprom_test.setEnabled(True)
        
    def _on_test_error(self, error_msg: str):
        """Handle test error"""
        QMessageBox.critical(self, "Test Error", error_msg)
        self.ui.push_button_usb_test.setEnabled(True)
        self.ui.push_button_emmc_test.setEnabled(True)
        self.ui.push_button_eeprom_test.setEnabled(True)
        
    # --- Optional: Slots to handle worker connection status --- 
    @Slot()
    def _on_worker_connected(self):
        """Handles the worker_connected signal from CommandViewModel."""
        logger.info("MainWindow: Worker connected signal received.")
        # Update UI elements
        if hasattr(self.ui, 'push_button_create_connection'):
             self.ui.push_button_create_connection.setEnabled(False)
        if hasattr(self.ui, 'push_button_disconnect'):
             self.ui.push_button_disconnect.setEnabled(True)
        if hasattr(self.ui, 'push_button_send_command'):
             self.ui.push_button_send_command.setEnabled(True)
        if hasattr(self.ui, 'line_edit_command'):
             self.ui.line_edit_command.setEnabled(True)

    @Slot()
    def _on_worker_disconnected(self):
        """Handles the worker_disconnected signal from CommandViewModel."""
        logger.info("MainWindow: Worker disconnected signal received.")
        # Update UI elements
        if hasattr(self.ui, 'push_button_create_connection'):
             self.ui.push_button_create_connection.setEnabled(True)
        if hasattr(self.ui, 'push_button_disconnect'):
             self.ui.push_button_disconnect.setEnabled(False)
        if hasattr(self.ui, 'push_button_send_command'):
             self.ui.push_button_send_command.setEnabled(False)
        if hasattr(self.ui, 'line_edit_command'):
             self.ui.line_edit_command.setEnabled(False)

    @Slot(str)
    def _on_worker_connection_error(self, error_msg: str):
        """Handles the worker_connection_error signal from CommandViewModel."""
        logger.error(f"MainWindow: Worker connection error signal received: {error_msg}")
        # Ensure UI reflects disconnected state on error
        self._on_worker_disconnected() 
        # Show error message (already handled by message_received connection, 
        # but you could show a specific popup here if needed)
        # QMessageBox.critical(self, "Connection Error", error_msg)

    @Slot()
    def _on_open_battery_dashboard(self):
        """open battery dashboard"""
        logger.info("Opening Battery Dashboard...")
        try:
            # if dashboard is not created, create it
            if not self.battery_dashboard:
                # when create, set auto_start=False, because we will call show_dashboard() manually
                self.battery_dashboard = BatteryDashboardView(auto_start=False)
                logger.debug("Battery Dashboard created")
            
            # display dashboard
            self.battery_dashboard.show_dashboard()
            logger.info("Battery Dashboard displayed")
            
        except Exception as e:
            error_msg = f"Failed to open Battery Dashboard: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def _on_push_button_usb_test_clicked(self):
        """Handle USB Test button clicked"""
        logger.info("USB Test button clicked")
        
        try:
            # Get connection parameters
            port = self.ui.combo_box_port.currentText()
            baudrate = int(self.ui.combo_box_baudrate.currentText())
            latency = int(self.ui.combo_box_latency.currentText())
            logger.info(f"Using connection parameters: Port={port}, Baudrate={baudrate}, Latency={latency}")
            
            # if not created, create it with connection parameters
            if not self.usb_view_model:
                self.usb_view_model = UsbViewModel(device_id='usb', port=port, baudrate=baudrate, timeout=latency)
                # connect signals
                self.usb_view_model.message_received.connect(self._on_log_message)
                self.usb_view_model.test_started.connect(self._on_test_started)
                self.usb_view_model.test_finished.connect(self._on_test_finished)
                self.usb_view_model.test_error.connect(self._on_test_error)
                logger.info("UsbViewModel created and signals connected")
            else:
                # Update connection parameters if already created
                self.usb_view_model.port = port
                self.usb_view_model.baudrate = baudrate
                self.usb_view_model.timeout = latency
            
            # start test
            self.usb_view_model.start_test()
        except Exception as e:
            error_msg = f"Failed to run USB test: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Test Error", error_msg)
    
    def _on_push_button_emmc_test_clicked(self):
        """Handle EMMC Test button clicked"""
        logger.info("EMMC Test button clicked")
        
        try:
            # Get connection parameters
            port = self.ui.combo_box_port.currentText()
            baudrate = int(self.ui.combo_box_baudrate.currentText())
            latency = int(self.ui.combo_box_latency.currentText())
            logger.info(f"Using connection parameters: Port={port}, Baudrate={baudrate}, Latency={latency}")
            
            # if not created, create it with connection parameters
            if not self.emmc_view_model:
                self.emmc_view_model = EmmcViewModel(device_id='emmc', port=port, baudrate=baudrate, timeout=latency)
                # connect signals
                self.emmc_view_model.message_received.connect(self._on_log_message)
                self.emmc_view_model.test_started.connect(self._on_test_started)
                self.emmc_view_model.test_finished.connect(self._on_test_finished)
                self.emmc_view_model.test_error.connect(self._on_test_error)
                logger.info("EmmcViewModel created and signals connected")
            else:
                # Update connection parameters if already created
                self.emmc_view_model.port = port
                self.emmc_view_model.baudrate = baudrate
                self.emmc_view_model.timeout = latency
            
            # start test
            self.emmc_view_model.start_test()
        except Exception as e:
            error_msg = f"Failed to run EMMC test: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Test Error", error_msg)
    
    def _on_push_button_eeprom_test_clicked(self):
        """Handle EEPROM Test button clicked"""
        logger.info("EEPROM Test button clicked")
        
        try:
            # Get connection parameters
            port = self.ui.combo_box_port.currentText()
            baudrate = int(self.ui.combo_box_baudrate.currentText())
            latency = int(self.ui.combo_box_latency.currentText())
            logger.info(f"Using connection parameters: Port={port}, Baudrate={baudrate}, Latency={latency}")
            
            # if not created, create it with connection parameters
            if not self.eeprom_view_model:
                self.eeprom_view_model = EepromViewModel(device_id='eeprom', port=port, baudrate=baudrate, timeout=latency)
                # connect signals
                self.eeprom_view_model.message_received.connect(self._on_log_message)
                self.eeprom_view_model.test_started.connect(self._on_test_started)
                self.eeprom_view_model.test_finished.connect(self._on_test_finished)
                self.eeprom_view_model.test_error.connect(self._on_test_error)
                logger.info("EepromViewModel created and signals connected")
            else:
                # Update connection parameters if already created
                self.eeprom_view_model.port = port
                self.eeprom_view_model.baudrate = baudrate
                self.eeprom_view_model.timeout = latency
            
            # start test
            self.eeprom_view_model.start_test()
        except Exception as e:
            error_msg = f"Failed to run EEPROM test: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Test Error", error_msg)

    def closeEvent(self, event):
        """Handle window close event"""
        # Cleanup any resources before closing
        logger.info("Application closing...")
        
        # close battery dashboard first if exists
        if self.battery_dashboard:
            logger.info("Closing Battery Dashboard...")
            try:
                # close dashboard (view model will handle resource cleanup)
                self.battery_dashboard.close()
                
                # explicitly release reference
                self.battery_dashboard = None
                logger.info("Battery Dashboard closed and resources cleaned up")
            except Exception as e:
                logger.error(f"Error during battery dashboard cleanup: {str(e)}")
        
        # Disconnect from device if connected
        try:
            # stop all tests
            if self.usb_view_model:
                self.usb_view_model.stop_test()
            if self.emmc_view_model:
                self.emmc_view_model.stop_test()
            if self.eeprom_view_model:
                self.eeprom_view_model.stop_test()
            
            # disconnect device
            self.command_view_model.disconnect_device()
            
            # wait for all threads to finish
            if hasattr(self.command_view_model, 'worker_thread') and self.command_view_model.worker_thread:
                logger.info("waiting for command worker thread to finish...")
                if not self.command_view_model.worker_thread.wait(3000):  # wait for 3 seconds
                    logger.warning("command worker thread not finished, force terminate")
                    self.command_view_model.worker_thread.terminate()
                    self.command_view_model.worker_thread.wait()
            
            # cleanup other view model resources
            self.command_view_model.cleanup()
            
        except Exception as e:
            logger.error(f"Error during disconnect on exit: {str(e)}")
        
        # Accept the close event
        event.accept()
