from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem, QInputDialog, QLineEdit
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QComboBox, QTabWidget
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger
from PySide6.QtGui import QColor, QIcon, QFont
import os
import sys
import csv
from PySide6.QtCore import QFile
from core.services.hardware_test_manager import HardwareTestManagerService
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QSizePolicy, QMessageBox

from gui.views.test_manager import TestManagerView
from gui.widgets.test_container import TestContainer
from gui.views.system_info_manager import SystemInfoManagerView
from gui.views.log_manager import LogManagerView
from gui.views.auto_diagnostic_view import AutoDiagnosticView


class DarkEditDialog(QDialog):
    """Custom dark theme edit dialog"""
    
    def __init__(self, parent=None, title="Edit", label_text="Enter value:", initial_text=""):
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle(title)
        self.resize(350, 120)
        
        # Set dark theme style
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #3E3E3E;
                color: #4FC3F7;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #0078D7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        
        # Create layout
        main_layout = QVBoxLayout(self)
        
        # Add label with bold font
        self.label = QLabel(label_text)
        font = self.label.font()
        font.setBold(True)
        self.label.setFont(font)
        main_layout.addWidget(self.label)
        
        # Add line edit
        self.line_edit = QLineEdit(initial_text)
        self.line_edit.selectAll()  # Select all text for easy editing
        main_layout.addWidget(self.line_edit)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        # Add space to push buttons to the right
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)  # Make it the default button (Enter key)
        button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_layout)
        
        # Set focus to the line edit
        self.line_edit.setFocus()
    
    def get_text(self):
        """Get the entered text"""
        return self.line_edit.text()

class MainWindowController(QObject):
    """
    Controller class for managing device monitoring main window
    Each device will create a separate instance
    """
    # Add window closed signal
    window_closed = Signal(str)  # Send device ID
    
    def __init__(self, device_id, view_model):
        """
        Initialize main window controller
        
        Args:
            device_id: device ID
            view_model: DeviceManagerViewModel instance
        """
        # Call QObject initialization
        super().__init__()
        
        # Save device ID and view model
        self.device_id = device_id
        self.view_model = view_model
        
        # Add update status flag
        self.is_updating = False
        
        # add current tab index
        self.current_tab_index = -1
        
        # Ensure view_model has system_info_service
        if not hasattr(self.view_model, 'system_info_service') and hasattr(self.view_model, '_serial_worker'):
            from core.services.system_info import SystemInfoService
            self.view_model.system_info_service = SystemInfoService(self.view_model._serial_worker)
        
        # Load UI
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'main_window.ui')
                icon_path = os.path.join(base_path, 'resources', 'icons', 'header.ico')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.abspath(__file__))
                gui_dir = os.path.dirname(current_dir)
                ui_file_path = os.path.join(gui_dir, "ui", "main_window.ui")
                
                # Get icon path - go up two levels from gui/views
                base_dir = os.path.dirname(gui_dir)
                icon_path = os.path.join(base_dir, "resources", "icons", "header.ico")
            
            logger.debug(f"Loading main window UI from: {ui_file_path}")
            
            # Load UI file
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                error_msg = f"Cannot open {ui_file_path}: {ui_file.errorString()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Load UI using QUiLoader
            loader = QUiLoader()
            self.window = loader.load(ui_file)
            ui_file.close()
            
            if not self.window:
                error_msg = f"Failed to load UI file: {loader.errorString()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Ensure the window can be resized
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.window.setMinimumSize(600, 500)  # set a reasonable minimum size
            self.window.setMaximumSize(16777215, 16777215)  # set the maximum size to a large value
            
            logger.debug(f"Main window UI loaded successfully for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to load main window UI: {str(e)}")
            raise
        
        # create the waiting spinner widget
        from gui.widgets.waiting_spinner import WaitingSpinner
        self.waiting_spinner = WaitingSpinner(
            parent=self.window,
            disable_parent_when_spinning=False,
            radius=10,
            line_length=5,
            line_width=2,
            speed=1.5,
            color=QColor(0, 120, 215)  # use blue, match the system style
        )
        
        # Set window properties
        self._set_window_properties()
        
        # create the system info manager
        self.system_info_manager = SystemInfoManagerView(self.device_id, self.view_model.system_info_service)
        
        # create the log manager
        self.log_manager = LogManagerView(self.device_id)
        
        # Initialize system info view
        self._init_system_info_view()
        
        # Initialize logs view
        self._init_logs_view()
        
        # Create hardware test manager
        self.hw_test_manager = HardwareTestManagerService(self.view_model._serial_worker)
        
        # Create the test manager view
        self.test_manager = TestManagerView(self.device_id, self.hw_test_manager)
        
        # Create auto diagnostic view
        self.auto_diagnostic_view = AutoDiagnosticView(self.device_id, self.hw_test_manager)
        
        # Connect signals and slots
        self._connect_signals()
        
        # Initialize functionality test UI
        self._init_functionality_test_ui()
        
        # Initialize auto diagnostic view
        self._init_auto_diagnostic_view()
        
        # Connect refresh button
        self.window.pushButton_refresh.clicked.connect(self._on_refresh_system_info)
        
        # Initialize display status as "Initializing"
        self._set_initializing_state()
        
        # Install event filter to capture window close event
        self.window.installEventFilter(self)
        
        # Connect edit button signals
        self.window.button_edit_model_name.clicked.connect(self._on_edit_model_name)
        self.window.button_edit_serial_number.clicked.connect(self._on_edit_serial_number)
        self.window.button_edit_battery_model.clicked.connect(self._on_edit_battery_model)
        self.window.button_edit_battery_serial.clicked.connect(self._on_edit_battery_serial)
        
        # 连接标签页切换信号
        if hasattr(self.window, 'tabWidget'):
            self.window.tabWidget.currentChanged.connect(self._on_tab_changed)
    
    def eventFilter(self, obj, event):
        """Filter window events to capture close event"""
        if obj is self.window and event.type() == QEvent.Close:
            logger.info(f"Main window for device {self.device_id} is closing")
            # Stop update timer
            # self.update_timer.stop()
            # Emit window close signal
            self.window_closed.emit(self.device_id)
        return super().eventFilter(obj, event)
    
    def _init_system_info_view(self):
        """Initialize system info view settings"""
        # set the ui components of the system info manager
        system_ui_components = {
            "refresh_button": self.window.pushButton_refresh,
            "last_updated_label": self.window.label_last_updated,
            
            # System basic info
            "model_name": self.window.value_model_name,
            "serial_number": self.window.value_serial_number,
            "cpu": self.window.value_cpu,
            "memory": self.window.value_memory,
            "storage": self.window.value_storage,
            
            # Battery info
            "battery_model": self.window.value_battery_model,
            "battery_serial": self.window.value_battery_serial,
            "charge_progress": self.window.progressBar_charge,
            "charge": self.window.value_charge,
            "voltage": self.window.value_voltage,
            "current": self.window.value_current,
            "temperature": self.window.value_temperature,
        }
        
        # set the ui components
        self.system_info_manager.set_ui_components(system_ui_components)
        
        # set a function to add system log, directly write to the log manager
        # use anonymous function to wrap, ensure the log will not cause the switch to the system log tab
        self.system_info_manager.add_system_log = lambda level, message: self._add_system_log_without_tab_switch(level, message)
        
        # connect the signals of the system info manager
        # when updating, directly call the method to handle instead of using the signal, so that the tab switch can be controlled
        # when the update is completed, re-enable the UI controls
        self.system_info_manager.info_update_completed.connect(self._on_system_info_update_completed)
        
        # when the update is error, add the error log, and close the waiting icon
        self.system_info_manager.info_update_error.connect(self._on_system_info_update_error)
    
    def _add_system_log_without_tab_switch(self, level, message):
        """Add system log without switching tabs"""
        # record the current tab
        current_tab = -1
        if hasattr(self.window, 'tabWidget'):
            current_tab = self.window.tabWidget.currentIndex()
            
        # add the log, but do not scroll to bottom to avoid activating the log tab
        self.log_manager.add_log_entry(level, message, scroll_to_bottom=False)
        
        # if updating and current tab is valid, restore to the previous tab
        if self.is_updating and current_tab >= 0 and hasattr(self.window, 'tabWidget'):
            self.window.tabWidget.setCurrentIndex(current_tab)
    
    def _on_system_info_update_completed(self):
        """Handle the event of system info update completed"""
        # restore the updating status flag
        self.is_updating = False
        
        # stop the waiting icon
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.stop()
        
        # enable all UI controls
        self.set_ui_controls_state(True)
        
        # add the completed log
        self.log_manager.add_log_entry("INFO", "System info update completed")
    
    def _on_system_info_update_error(self, error_message):
        """Handle the event of system info update error"""
        # restore the updating status flag
        self.is_updating = False
        
        # stop the waiting icon
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.stop()
        
        # enable all UI controls
        self.set_ui_controls_state(True)
        
        # add the error log
        self.log_manager.add_log_entry("ERROR", f"System info update error: {error_message}")
    
    def _init_logs_view(self):
        """Initialize logs view settings"""
        # Configure logs table
        logs_table = self.window.tableWidget_logs
        logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        logs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Message column stretch
        
        # Set column width
        logs_table.setColumnWidth(0, 180)  # Timestamp column
        logs_table.setColumnWidth(1, 80)   # Level column
        
        # Enable automatic row height adjustment to display full content
        logs_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Set table to automatically wrap text
        logs_table.setWordWrap(True)
        
        # set the ui components to the log manager
        self.log_manager.set_ui_components(
            self.window.tableWidget_logs,
            self.window.comboBox_log_level,
            self.window.comboBox_time_range,
            self.window.pushButton_clear_logs
        )
        
        # Connect command send button
        self.window.pushButton_send_command.clicked.connect(self._on_send_command)
        self.window.lineEdit_command.returnPressed.connect(self._on_send_command)
        
        # Connect logs refresh button
        self.window.pushButton_refresh_logs.clicked.connect(self._refresh_logs)
    
    def _filter_logs(self):
        """Filter logs based on selected level and time range"""
        # this method is already handled internally by LogManagerView, keep it for backward compatibility
        pass
    
    def _refresh_logs(self):
        """Refresh log data"""
        # In actual application, get latest logs from device
        logger.info(f"Refreshing logs for device: {self.device_id}")
        
        # For example, can send command to get logs
        self.view_model.send_command(self.device_id, "get_logs")
        
        # Can update logs in command_completed signal processing
    
    def _clear_logs(self):
        """Clear log table"""
        # delegate to the log manager to clear logs
        self.log_manager.clear_logs()
    
    def _on_send_command(self):
        """Process command sending"""
        command = self.window.lineEdit_command.text().strip()
        if not command:
            return
            
        logger.info(f"Sending command to device {self.device_id}: {command}")
        
        # Send command to device
        self.view_model.send_command(self.device_id, command)
        
        # Clear command input box
        self.window.lineEdit_command.clear()
        
        # Add command record to logs
        self.log_manager.add_log_entry("INFO", f"[Command] {command}")
    
    def _connect_signals(self):
        """Connect signals and slots"""
        # Connect command result signal from view model
        self.view_model.command_result.connect(self._on_command_completed)
        
        # connect the all tests completed signal of the test manager
        self.test_manager.all_tests_completed.connect(self._on_all_tests_completed)
        
        # connect the export result button
        if hasattr(self.window, 'button_export_result'):
            self.window.button_export_result.clicked.connect(self._export_test_results)
    
    def _init_functionality_test_ui(self):
        """Initialize functionality test UI elements"""
        # Configure shared test steps table
        hw_test_table = self.window.tableWidget_hardware_test_steps
        hw_test_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        hw_test_table.horizontalHeader().setStretchLastSection(True)
        hw_test_table.setColumnWidth(0, 200)  # Step column
        hw_test_table.setColumnWidth(1, 80)   # Status column
        
        # Set table minimum height
        hw_test_table.verticalHeader().setDefaultSectionSize(30)  # Set row height to 30 pixels
        hw_test_table.setMinimumHeight(180)   # Set minimum height
        
        # Create the test container
        test_container = TestContainer()
        
        # Create test modules in the container
        test_container.add_test_group("functionality_audio", "Audio Test")
        test_container.add_test_group("functionality_backlight", "Backlight Test")
        test_container.add_test_group("functionality_battery", "Battery Test")
        test_container.add_test_group("functionality_camera", "Camera Test")
        test_container.add_test_group("functionality_charge", "Charge Test")
        test_container.add_test_group("functionality_eeprom", "EEPROM Test")
        test_container.add_test_group("functionality_emmc", "eMMC Test")
        test_container.add_test_group("functionality_lcd", "LCD Test")
        test_container.add_test_group("functionality_led", "LED Test")
        test_container.add_test_group("functionality_power_button", "Power Button Test")
        test_container.add_test_group("functionality_touch", "Touch Test")
        test_container.add_test_group("functionality_usb", "USB Test")

        
        # Get functionality test page layout
        tab_functionality = self.window.tab_functionality
        layout = tab_functionality.layout()
        
        # Create abort button
        self.window.button_abort_test = QPushButton("Abort Test")
        self.window.button_abort_test.setMinimumSize(100, 0)
        
        # Style abort button (red background for emphasis)
        self.window.button_abort_test.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F44336;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
        """)
        
        # Add the abort button to the layout
        if hasattr(self.window, 'button_export_result'):
            # Find the export result button's parent layout
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if isinstance(item, QHBoxLayout):
                    for j in range(item.count()):
                        widget = item.itemAt(j).widget()
                        if widget == self.window.button_export_result:
                            # Insert abort button before export result button
                            item.insertWidget(j, self.window.button_abort_test)
                            break
        
        # insert the test container between the title row and the test progress
        # the 0th item is the title row, the 1st item is the test progress, now we insert the test container between them
        layout.insertWidget(1, test_container)
        
        # Set the UI components of the test manager
        self.test_manager.set_ui_components(
            test_container,
            self.window.button_test_all,
            self.window.tableWidget_hardware_test_steps,
            self.window.progressBar_hardware_test,
            self.window,  # Parent widget as the parent of the dialog
            self.window.button_abort_test  # Pass the abort button to test manager
        )
        
        # Set the log recording function, record the command to the system log
        self.test_manager.add_system_log = lambda level, message: self.log_manager.add_log_entry(level, message)
        
        # Hide the progress bar by default
        self.window.progressBar_hardware_test.setVisible(False)
    
    def _set_initializing_state(self):
        """Set all system info display to initializing state"""
        # delegate to the system info manager to set the initializing state
        self.system_info_manager.set_initializing_state()

    def _on_refresh_system_info(self):
        """Handle refresh button click"""
        # 记录当前标签页，但不强制切换回去，让用户可以自由切换
        if hasattr(self.window, 'tabWidget'):
            self.current_tab_index = self.window.tabWidget.currentIndex()
            logger.debug(f"当前标签页索引: {self.current_tab_index} (Dashboard)")
        
        # 设置更新状态标志
        self.is_updating = True
        
        # 添加日志，但不切换到日志标签
        self.log_manager.add_log_entry("INFO", f"Refreshing system info for {self.device_id}...")
        
        # 定位并显示等待图标在刷新按钮旁边
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.position_next_to(self.window.pushButton_refresh)
            self.waiting_spinner.start()
        
        # 禁用所有控件，但保持标签页切换功能可用
        self.set_ui_controls_state_except_tabs(False)
        
        # 执行系统信息刷新
        self.system_info_manager.refresh_system_info()

    def _on_edit_model_name(self):
        """handle the edit model name button click"""
        if self.system_info_manager.edit_model_name():
            self.log_manager.add_log_entry("INFO", "Model name updated")

    def _on_edit_serial_number(self):
        """handle the edit serial number button click"""
        if self.system_info_manager.edit_serial_number():
            self.log_manager.add_log_entry("INFO", "Serial number updated")

    def _on_edit_battery_model(self):
        """handle the edit battery model button click"""
        if self.system_info_manager.edit_battery_model():
            self.log_manager.add_log_entry("INFO", "Battery model updated")

    def _on_edit_battery_serial(self):
        """handle the edit battery serial number button click"""
        if self.system_info_manager.edit_battery_serial():
            self.log_manager.add_log_entry("INFO", "Battery serial number updated")

    def _set_window_properties(self):
        """Set window properties, ensure it is recognized as part of the main application"""
        try:
            # Get application instance
            app = QApplication.instance()
            if not app:
                logger.warning("Unable to get QApplication instance")
                return
                
            # Get global application display name
            app_name = app.applicationDisplayName() or app.applicationName() or "VT Hydra System Monitor"
            
            # Use application icon
            if app.windowIcon() and not self.window.windowIcon():
                self.window.setWindowIcon(app.windowIcon())
                
            # Set window title to include application name
            title = f"{app_name} - Device {self.device_id} Monitoring"
            self.window.setWindowTitle(title)
            
            # Set window flags to ensure it is recognized as the main application window
            self.window.setWindowFlags(self.window.windowFlags() | Qt.Window)
            
            # ensure the window can be resized
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # remove the fixed size constraint (if any)
            if self.window.minimumSize().width() == self.window.maximumSize().width() or \
               self.window.minimumSize().height() == self.window.maximumSize().height():
                # reset the minimum and maximum size
                self.window.setMinimumSize(600, 500)  # set a reasonable minimum size
                self.window.setMaximumSize(16777215, 16777215)  # set the maximum size to a large value
            
            # Set taskbar related properties on Windows
            if sys.platform == 'win32':
                try:
                    # we don't directly call Win32 API here
                    # let the system naturally associate the window - rely on the application identifier set earlier
                    pass
                except Exception as e:
                    logger.warning(f"Unable to set Windows window properties: {e}")
            
            logger.debug(f"Window properties set: {title}")
        except Exception as e:
            logger.warning(f"Error setting window properties: {e}")

    @Slot()
    def _on_all_tests_completed(self):
        """Handle the event of all tests completed"""
        self.log_manager.add_log_entry("INFO", "All hardware tests completed")
    
    def _export_test_results(self):
        """Export test results to a CSV file"""
        try:
            # get the save file path
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"test_results_{self.device_id}_{timestamp}.csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self.window,
                "Export Test Results",
                default_filename,
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # get the test results and progress records from the test manager
            test_results = self.test_manager.get_test_results()
            test_progress_records = self.test_manager.get_test_progress_records()
                
            # write to the CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # write the title row
                writer.writerow(["Module", "Step", "Timestamp", "Time", "Result", "Command", "Response"])
                
                # write the progress records and step details for each test module
                for test_id, records in test_progress_records.items():
                    # get the step details of the test
                    test_steps = []
                    if test_id in test_results:
                        test_steps = test_results[test_id]["steps"]
                    
                    for record in records:
                        # find the corresponding step information
                        current_step = record['current_step'] - 1  # convert to 0-based index
                        
                        # get the step status, message and time from the test results
                        step_desc = ""
                        step_message = ""
                        step_command = ""
                        step_response = ""
                        step_time = "--:--:--"  # default time
                        
                        # get the step information from the test results
                        for step in test_steps:
                            if step['index'] == current_step:
                                step_message = step['message']
                                # get the step description from the test results
                                if 'description' in step:
                                    step_desc = step['description']
                                    logger.debug(f"Found description in test result: {step_desc}")
                                # get the command and response from the test results
                                if 'command' in step:
                                    step_command = step['command']
                                    logger.debug(f"Found command in test result: {step_command}")
                                if 'response' in step:
                                    step_response = step['response']
                                    logger.debug(f"Found response in test result: {step_response}")
                                # get the execution time of the step
                                if 'time' in step:
                                    step_time = step['time']
                                break
                        
                        # try to get the step description from the test worker
                        if not step_desc and test_id in self.hw_test_manager.test_workers:
                            worker = self.hw_test_manager.test_workers[test_id]
                            if len(worker.steps) > current_step:
                                test_step = worker.steps[current_step]
                                # get the step description
                                if hasattr(test_step, 'description'):
                                    step_desc = test_step.description
                                    logger.debug(f"Found description in worker: {step_desc}")
                                
                                # only get the command when it is not in the test results
                                if not step_command and hasattr(test_step, 'command'):
                                    step_command = test_step.command
                                    logger.debug(f"Found command in worker: {step_command}")
                                
                                # only get the response when it is not in the test results
                                if not step_response:
                                    # use the response property first, if not, use the result property
                                    if hasattr(test_step, 'response') and test_step.response:
                                        step_response = test_step.response
                                        logger.debug(f"Found response in worker (response attr): {step_response}")
                                    elif hasattr(test_step, 'result') and test_step.result:
                                        step_response = test_step.result
                                        logger.debug(f"Found response in worker (result attr): {step_response}")
                        
                        # record the final collected information
                        logger.debug(f"Final step info - Test: {test_id}, Step: {current_step+1}, Desc: '{step_desc}', Cmd: '{step_command}', Time: {step_time}")
                        
                        # create the row data
                        row_data = [
                            test_id,              # Module
                            step_desc,            # Step
                            record['timestamp'],  # Timestamp
                            step_time,            # Time - use the execution time of the step
                            step_message,         # Result
                            step_command,         # Command
                            step_response         # Response
                        ]
                        
                        writer.writerow(row_data)
            
            self.log_manager.add_log_entry("INFO", f"Test results exported to: {file_path}")
            
        except Exception as e:
            error_msg = f"Error exporting test results: {str(e)}"
            logger.error(error_msg)

    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """
        Handle command completed event
        
        Args:
            device_id: Device ID
            command: Command sent
            response: Command response
        """
        # Only process commands for this device
        if device_id != self.device_id:
            return
            
        # Log command and response
        self.log_manager.add_log_entry("DEBUG", f"[Response] {response}")
        
        # Process response based on command
        if command.startswith("get_logs"):
            self._process_logs_response(response)
    
    def _update_dashboard(self):
        """Update dashboard information"""
        # delegate to the system info manager to refresh the system info
        self.system_info_manager.refresh_system_info()
    
    def _process_logs_response(self, response):
        """Process logs response"""
        # delegate to the log manager to process the logs response
        self.log_manager.process_logs_response(response)
    
    def show(self):
        """Show window and trigger system info update"""
        # Check window properties again before showing, ensure it's part of the main application
        self._set_window_properties()
        
        # ensure the window can be resized
        from PySide6.QtCore import Qt
        self.window.setWindowFlags(
            self.window.windowFlags() | 
            Qt.Window | 
            Qt.WindowMinMaxButtonsHint | 
            Qt.WindowCloseButtonHint
        )
        self.window.setAttribute(Qt.WA_DeleteOnClose, False)  # prevent the window from being deleted when closed
        
        # show the window
        self.window.show()
        
        # ensure the window is raised and activated
        self.window.raise_()
        self.window.activateWindow()
    
    def close(self):
        """Close the main window and cleanup resources"""
        try:
            logger.info(f"Closing main window for device {self.device_id}")
            
            # stop the waiting icon
            if hasattr(self, 'waiting_spinner') and self.waiting_spinner:
                self.waiting_spinner.stop()
                self.waiting_spinner = None
            
            # Clean up hardware test manager
            if self.hw_test_manager:
                logger.debug("Cleaning up hardware test manager")
                # Stop any running tests
                self.hw_test_manager.stop_current_test()
                if hasattr(self.hw_test_manager, 'cleanup'):
                    self.hw_test_manager.cleanup()
            
            # Clean up test manager
            if self.test_manager:
                logger.debug("Cleaning up test manager")
                self.test_manager.cleanup()
                self.test_manager = None
            
            # Clean up system info manager
            if self.system_info_manager:
                logger.debug("Cleaning up system info manager")
                # Disconnect signals
                try:
                    self.system_info_manager.info_update_completed.disconnect()
                    self.system_info_manager.info_update_error.disconnect()
                except Exception:
                    # Signals may already be disconnected
                    pass
                
                if hasattr(self.system_info_manager, 'cleanup'):
                    self.system_info_manager.cleanup()
                self.system_info_manager = None
            
            # Clean up log manager
            if self.log_manager:
                logger.debug("Cleaning up log manager")
                if hasattr(self.log_manager, 'cleanup'):
                    self.log_manager.cleanup()
                self.log_manager = None
            
            # Clean up auto diagnostic view
            if self.auto_diagnostic_view:
                logger.debug("Cleaning up auto diagnostic view")
                self.auto_diagnostic_view.cleanup()
                self.auto_diagnostic_view = None
            
            # Clean up the view model
            if hasattr(self, 'view_model') and self.view_model and hasattr(self.view_model, 'cleanup'):
                logger.debug("Cleaning up view model")
                self.view_model.cleanup()
            
            # Disconnect signals
            try:
                # Disconnect view model signals
                if hasattr(self, 'view_model') and self.view_model:
                    try:
                        self.view_model.command_result.disconnect(self._on_command_completed)
                    except Exception:
                        pass  # If already disconnected, ignore the error
                
                # Disconnect test manager signals
                if hasattr(self, 'test_manager'):
                    try:
                        self.test_manager.all_tests_completed.disconnect(self._on_all_tests_completed)
                    except Exception:
                        pass  # Ignore error of already disconnected signal
            except Exception as e:
                logger.error(f"Error disconnecting signals: {e}")
            
            # Remove event filter
            if hasattr(self, 'window') and self.window:
                self.window.removeEventFilter(self)
            
            # Close the window
            if self.window:
                logger.debug("Closing the main window")
                self.window.close()
                self.window = None
            
            # Emit window closed signal
            self.window_closed.emit(self.device_id)
            
            logger.info(f"Main window resources cleaned up for device: {self.device_id}")
            
        except Exception as e:
            logger.error(f"Error during main window cleanup: {str(e)}")
            # Still try to close the window even if there was an error
            if self.window:
                self.window.close()
                self.window = None

    def set_ui_controls_state(self, enabled=True, exclude_widgets=None):
        """
        General UI control enable/disable method
        
        Args:
            enabled (bool): Whether to enable the controls
            exclude_widgets (list): List of widgets to exclude from the enable/disable operation
        """
        if exclude_widgets is None:
            exclude_widgets = []
        
        # handle the buttons
        for button in self.window.findChildren(QPushButton):
            if button not in exclude_widgets:
                button.setEnabled(enabled)
        
        # handle the combo boxes
        for combobox in self.window.findChildren(QComboBox):
            if combobox not in exclude_widgets:
                combobox.setEnabled(enabled)
        
        # handle the line edits
        for lineedit in self.window.findChildren(QLineEdit):
            if lineedit not in exclude_widgets:
                lineedit.setEnabled(enabled)
        
        # handle the tab widgets
        for tabwidget in self.window.findChildren(QTabWidget):
            if tabwidget not in exclude_widgets:
                for i in range(tabwidget.count()):
                    tabwidget.setTabEnabled(i, enabled)
        
        # 确保系统日志页中的发送命令按钮和输入框状态正确
        if hasattr(self.window, 'pushButton_send_command'):
            self.window.pushButton_send_command.setEnabled(enabled)
        if hasattr(self.window, 'lineEdit_command'):
            self.window.lineEdit_command.setEnabled(enabled)
                
        # if there is a TestManager, handle the test container buttons
        if hasattr(self, 'test_manager') and hasattr(self.test_manager, 'test_container'):
            self.test_manager.set_test_buttons_enabled(enabled)
            
        # if there is an AutoDiagnosticView, handle its buttons
        if hasattr(self, 'auto_diagnostic_view'):
            self.auto_diagnostic_view.set_buttons_enabled(enabled)

    def _init_auto_diagnostic_view(self):
        """Initialize auto diagnostic view settings"""
        # create the auto diagnostic component
        self.auto_diagnostic_widget = self.auto_diagnostic_view.create_widget()
        
        # add the auto diagnostic component as a standalone layout, directly add to the Dashboard tab
        # get the Dashboard tab layout
        dashboard_layout = self.window.tab_dashboard.layout()
        if dashboard_layout:
            # add the auto diagnostic component (after the System Overview group box)
            dashboard_layout.addWidget(self.auto_diagnostic_widget)
        else:
            # if the Dashboard page has no layout, create a new one
            dashboard_layout = QVBoxLayout(self.window.tab_dashboard)
            dashboard_layout.addWidget(self.window.groupBox_system_overview)  # add the system overview first
            dashboard_layout.addWidget(self.auto_diagnostic_widget)  # then add the auto diagnostic
        
        # set the auto diagnostic test items
        diagnostic_tests = {
            "diagnostic_cpu_name": "Check CPU Name",
            "diagnostic_cpu_processor": "Check CPU Processor",
            "diagnostic_emmc_size": "Check eMMC Size",
            "diagnostic_mac_address": "Check MAC Address",
            "diagnostic_memory_size": "Check Memory Size",
            "diagnostic_nor_flash_size": "Check NOR Flash Size",
            "diagnostic_pic_version": "Check PIC Version",
            "diagnostic_sync_time": "Check Sync Time",
            "diagnostic_set_get_rtc_time": "Check Set and Get RTC Time",
            "diagnostic_design_capacity": "Check Design Capacity",
            "diagnostic_design_voltage": "Check Design Voltage",
            "diagnostic_uboot_version": "Check U-Boot Version",
            "diagnostic_kernal_name": "Check Kernal Name",
            "diagnostic_panel_id_resolution": "Check Panel ID and Resolution",
            "diagnostic_wifi_bt": "Check Wifi and Bluetooth"
        }
        self.auto_diagnostic_view.setup_diagnostic_items(diagnostic_tests)
        
        # Set the add_system_log method of the auto diagnostic view
        self.auto_diagnostic_view.add_system_log = lambda level, message: self.log_manager.add_log_entry(level, message)
        
        # connect the signals
        self.auto_diagnostic_view.all_diagnostics_completed.connect(self._on_all_diagnostics_completed)
        self.auto_diagnostic_view.export_report_requested.connect(self._export_diagnostic_report)

    @Slot()
    def _on_all_diagnostics_completed(self):
        """handle the event of all diagnostics completed"""
        self.log_manager.add_log_entry("INFO", "All diagnostic tests completed")

    def _export_diagnostic_report(self):
        """export the diagnostic report"""
        # get the current time as part of the file name
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"diagnostic_report_{self.device_id}_{current_time}.csv"
        
        # show the file save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Export Diagnostic Report",
            default_filename,
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return  # the user cancelled
        
        try:
            # get the diagnostic results
            results = self.auto_diagnostic_view.get_diagnostic_results()
            
            # write to the CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # write the title row
                writer.writerow(["Module", "Step", "Timestamp", "Time", "Result", "Command", "Response"])
                
                # write the test results
                for test_id, result in results.items():
                    # get the status and time information
                    status = result.get("status", "UNKNOWN")
                    time_str = result.get("time", "--:--:--")
                    
                    # get the current time as the timestamp (because the diagnostic test might not have recorded it)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # get the details data
                    details = result.get("details", {})
                    
                    # check if there is step information
                    if isinstance(details, dict) and "steps" in details and details["steps"]:
                        # if there is detailed step information, create a row for each step
                        for step in details["steps"]:
                            # ensure to get the correct fields from the step information
                            step_desc = step.get("description", "")
                            step_command = step.get("command", "")
                            
                            # use the response property first, if not, use the result property
                            step_response = step.get("response", "")
                            if not step_response and step.get("result") is not None:
                                step_response = step.get("result", "")
                            # if the response is None, use an empty string instead
                            if step_response is None:
                                step_response = ""
                            
                            writer.writerow([
                                test_id,                         # Module
                                step_desc,                       # Step
                                timestamp,                       # Timestamp
                                time_str,                        # Time
                                "PASS" if step.get("passed", False) else "FAIL",  # Result
                                step_command,                     # Command
                                str(step_response)                # Response
                            ])
                    else:
                        # if there is no detailed step information, create a row for the basic information
                        # get the basic message
                        message = details.get("message", "") if isinstance(details, dict) else ""
                        writer.writerow([
                            test_id,           # Module
                            "",                # Step
                            timestamp,         # Timestamp
                            time_str,          # Time
                            status,            # Result
                            "",                # Command
                            message            # Response
                        ])
            
            self.log_manager.add_log_entry("INFO", f"Diagnostic report exported to {file_path}")
        except Exception as e:
            self.log_manager.add_log_entry("ERROR", f"Failed to export diagnostic report: {str(e)}")
            logger.error(f"Failed to export diagnostic report: {str(e)}")

    def _on_tab_changed(self, index):
        """Handle tab change event"""
        # only save the current tab index when not updating
        if not self.is_updating:
            self.current_tab_index = index
            logger.debug(f"Tab changed to index {index}")

    def set_ui_controls_state_except_tabs(self, enabled=True):
        """
        Set UI controls state, but keep the tabs available
        
        Args:
            enabled (bool): Whether to enable the controls
        """
        # exclude the tab widgets
        exclude_widgets = []
        if hasattr(self.window, 'tabWidget'):
            exclude_widgets.append(self.window.tabWidget)
        
        # call the original method, but exclude the tab widgets
        self.set_ui_controls_state(enabled, exclude_widgets)