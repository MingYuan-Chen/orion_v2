from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem, QInputDialog, QLineEdit
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog
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
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QSizePolicy

# import TestManagerView
from gui.views.test_manager import TestManagerView
from gui.widgets.test_container import TestContainer
# 导入新的模块化组件
from gui.views.system_info_manager import SystemInfoManagerView
from gui.views.log_manager import LogManagerView


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
            
            # 确保窗口可以调整大小
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.window.setMinimumSize(600, 500)  # 设置合理的最小尺寸
            self.window.setMaximumSize(16777215, 16777215)  # 最大尺寸设为很大的值
            
            logger.debug(f"Main window UI loaded successfully for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to load main window UI: {str(e)}")
            raise
        
        # Set window properties
        self._set_window_properties()
        
        # 创建系统信息管理器
        self.system_info_manager = SystemInfoManagerView(self.device_id, self.view_model.system_info_service)
        
        # 创建日志管理器
        self.log_manager = LogManagerView(self.device_id)
        
        # Initialize system info view
        self._init_system_info_view()
        
        # Initialize logs view
        self._init_logs_view()
        
        # Create hardware test manager
        self.hw_test_manager = HardwareTestManagerService(self.view_model._serial_worker)
        
        # 创建测试管理器视图
        self.test_manager = TestManagerView(self.device_id, self.hw_test_manager)
        
        # Connect signals and slots
        self._connect_signals()
        
        # Initialize functionality test UI
        self._init_functionality_test_ui()
        
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
        # 设置系统信息管理器的UI组件
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
        
        # 设置UI组件
        self.system_info_manager.set_ui_components(system_ui_components)
        
        # 连接系统信息管理器的信号
        self.system_info_manager.info_update_started.connect(lambda: self._set_ui_controls_enabled(False))
        self.system_info_manager.info_update_completed.connect(lambda: self._set_ui_controls_enabled(True))
        self.system_info_manager.info_update_error.connect(lambda msg: self.log_manager.add_log_entry("ERROR", f"System info update error: {msg}"))
    
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
        
        # 将UI组件设置到日志管理器
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
        # 此方法已由LogManagerView内部处理，这里保留方法以便向后兼容
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
        # 委托给日志管理器清除日志
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
        test_container.add_test_group("usb_ports", "USB Ports Test")
        test_container.add_test_group("emmc", "eMMC Test")
        test_container.add_test_group("eeprom", "EEPROM Test")
        test_container.add_test_group("battery", "Battery Test")
        test_container.add_test_group("backlight", "Backlight Test")
        test_container.add_test_group("led", "LED Test")
        test_container.add_test_group("audio", "Audio Test")
        
        # Get functionality test page layout
        tab_functionality = self.window.tab_functionality
        layout = tab_functionality.layout()
        
        # 在标题行和测试进度之间插入TestContainer
        # UI文件中第0项是标题行，第1项是测试进度，现在我们插入测试容器在它们之间
        layout.insertWidget(1, test_container)
        
        # Set the UI components of the test manager
        self.test_manager.set_ui_components(
            test_container,
            self.window.button_test_all,
            self.window.tableWidget_hardware_test_steps,
            self.window.progressBar_hardware_test
        )
        
        # Hide the progress bar by default
        self.window.progressBar_hardware_test.setVisible(False)
    
    def _set_initializing_state(self):
        """Set all system info display to initializing state"""
        # 委托给系统信息管理器设置初始化状态
        self.system_info_manager.set_initializing_state()

    def _set_ui_controls_enabled(self, enabled=True):
        """Enable or disable UI controls"""
        # 启用/禁用通过TestContainer管理的测试按钮
        # 使用测试管理器管理的UI组件
        if hasattr(self, 'test_manager') and hasattr(self.test_manager, 'test_container'):
            self.test_manager.set_test_buttons_enabled(enabled)
        
        # 启用/禁用"Test All"按钮
        if hasattr(self.window, 'button_test_all'):
            self.window.button_test_all.setEnabled(enabled)
        
        # 启用/禁用系统信息刷新按钮
        if hasattr(self.window, 'pushButton_refresh'):
            self.window.pushButton_refresh.setEnabled(enabled)
        
        # 启用/禁用发送命令按钮
        if hasattr(self.window, 'pushButton_send_command'):
            self.window.pushButton_send_command.setEnabled(enabled)
        
        # 启用/禁用导出结果按钮
        if hasattr(self.window, 'button_export_result'):
            self.window.button_export_result.setEnabled(enabled)
        
        # 启用/禁用日志过滤下拉框
        if hasattr(self.window, 'comboBox_log_level'):
            self.window.comboBox_log_level.setEnabled(enabled)
        if hasattr(self.window, 'comboBox_time_range'):
            self.window.comboBox_time_range.setEnabled(enabled)
        
        # 启用/禁用标签页
        if hasattr(self.window, 'tabWidget'):
            for i in range(self.window.tabWidget.count()):
                self.window.tabWidget.setTabEnabled(i, enabled)

    def _on_refresh_system_info(self):
        """Handle refresh button click"""
        # 委托给系统信息管理器处理刷新操作
        self.log_manager.add_log_entry("INFO", f"Refreshing system info for {self.device_id}...")
        self.system_info_manager.refresh_system_info()

    def _on_edit_model_name(self):
        """Handle model name edit button click"""
        current_text = self.window.value_model_name.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit model name",
            "Please enter the new model name:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                # 委托给系统信息管理器更新UI
                self.system_info_manager.update_model_name(new_text)
                # Maybe need to update backend data
    
    def _on_edit_serial_number(self):
        """Handle serial number edit button click"""
        current_text = self.window.value_serial_number.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit serial number",
            "Please enter the new serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                # 委托给系统信息管理器更新UI
                self.system_info_manager.update_serial_number(new_text)
                # Maybe need to update backend data
    
    def _on_edit_battery_model(self):
        """Handle battery model edit button click"""
        current_text = self.window.value_battery_model.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit battery model",
            "Please enter the new battery model:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                # 委托给系统信息管理器更新UI
                self.system_info_manager.update_battery_model(new_text)
                # Maybe need to update backend data
    
    def _on_edit_battery_serial(self):
        """Handle battery serial edit button click"""
        current_text = self.window.value_battery_serial.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit battery serial",
            "Please enter the new battery serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                # 委托给系统信息管理器更新UI
                self.system_info_manager.update_battery_serial(new_text)
                # Maybe need to update backend data

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
            
            # 确保窗口可以调整大小
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # 移除固定大小约束（如果有）
            if self.window.minimumSize().width() == self.window.maximumSize().width() or \
               self.window.minimumSize().height() == self.window.maximumSize().height():
                # 重置最小和最大尺寸
                self.window.setMinimumSize(600, 500)  # 设置合理的最小尺寸
                self.window.setMaximumSize(16777215, 16777215)  # 最大尺寸设为很大的值
            
            # Set taskbar related properties on Windows
            if sys.platform == 'win32':
                try:
                    # We don't directly call Win32 API here
                    # Let the system naturally associate the window - rely on the application identifier set earlier
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
                writer.writerow([
                    'Test Module',
                    'Timestamp',
                    'Current Step',
                    'Total Steps', 
                    'Progress %',
                    'Step Description',
                    'Step Status',
                    'Step Message'
                ])
                
                # write the progress records and step details for each test module
                for test_id, records in test_progress_records.items():
                    # get the step details of the test
                    test_steps = []
                    if test_id in test_results:
                        test_steps = test_results[test_id]["steps"]
                    
                    for record in records:
                        # basic progress information
                        row_data = [
                            test_id,
                            record['timestamp'],
                            record['current_step'],
                            record['total_steps'],
                            record['progress_percentage']
                        ]
                        
                        # add the step details
                        step_desc = ""
                        step_status = ""
                        step_message = ""
                        
                        # find the corresponding step information
                        current_step = record['current_step'] - 1  # convert to 0-based index
                        if test_id in self.hw_test_manager.test_workers:
                            worker = self.hw_test_manager.test_workers[test_id]
                            if len(worker.steps) > current_step:
                                step_desc = worker.steps[current_step].description
                        
                        # get the step status and message from the test results
                        for step in test_steps:
                            if step['index'] == current_step:
                                step_status = "Pass" if step['success'] else "Fail"
                                step_message = step['message']
                                break
                        
                        row_data.extend([step_desc, step_status, step_message])
                        writer.writerow(row_data)
            
            self.log_manager.add_log_entry("INFO", f"Test results exported to: {file_path}")
            
        except Exception as e:
            error_msg = f"Error exporting test results: {str(e)}"
            logger.error(error_msg)
            self.log_manager.add_log_entry("ERROR", error_msg)

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
        # 委托给系统信息管理器刷新系统信息
        self.system_info_manager.refresh_system_info()
    
    def _process_logs_response(self, response):
        """Process logs response"""
        # 委托给日志管理器处理日志响应
        self.log_manager.process_logs_response(response)
    
    def show(self):
        """Show window and trigger system info update"""
        # Check window properties again before showing, ensure it's part of the main application
        self._set_window_properties()
        
        # 确保窗口可以调整大小
        from PySide6.QtCore import Qt
        self.window.setWindowFlags(
            self.window.windowFlags() | 
            Qt.Window | 
            Qt.WindowMinMaxButtonsHint | 
            Qt.WindowCloseButtonHint
        )
        self.window.setAttribute(Qt.WA_DeleteOnClose, False)  # 防止窗口关闭时被删除
        
        # show the window
        self.window.show()
        
        # ensure the window is raised and activated
        self.window.raise_()
        self.window.activateWindow()
    
    def close(self):
        """Close window and release resources"""
        logger.info(f"Closing main window for device: {self.device_id}")
        
        # 1. stop all ongoing tests
        if hasattr(self, 'test_manager'):
            self.test_manager.stop_current_test()
        
        # 2. clean up the test manager resources
        if hasattr(self, 'test_manager') and hasattr(self.test_manager, 'cleanup'):
            logger.info("Cleaning up test manager")
            self.test_manager.cleanup()
        
        # 3. clean up the system info manager resources
        if hasattr(self, 'system_info_manager') and hasattr(self.system_info_manager, 'cleanup'):
            logger.info("Cleaning up system info manager")
            self.system_info_manager.cleanup()
        
        # 4. clean up the log manager resources
        if hasattr(self, 'log_manager') and hasattr(self.log_manager, 'cleanup'):
            logger.info("Cleaning up log manager")
            self.log_manager.cleanup()
        
        # 5. clean up the hardware test manager resources
        if hasattr(self, 'hw_test_manager') and hasattr(self.hw_test_manager, 'cleanup'):
            logger.info("Cleaning up hardware test manager")
            self.hw_test_manager.cleanup()
        
        # 6. clean up the view model resources
        if hasattr(self, 'view_model') and self.view_model and hasattr(self.view_model, 'cleanup'):
            logger.info("Cleaning up view model")
            self.view_model.cleanup()
        
        # 7. disconnect all signals
        try:
            # disconnect the view model signals
            if hasattr(self, 'view_model') and self.view_model:
                try:
                    self.view_model.command_result.disconnect(self._on_command_completed)
                except Exception:
                    pass  # if already disconnected, ignore the error
            
            # disconnect the test manager signals
            if hasattr(self, 'test_manager'):
                try:
                    self.test_manager.all_tests_completed.disconnect(self._on_all_tests_completed)
                except Exception:
                    pass  # ignore the error of already disconnected signal
                    
        except Exception as e:
            logger.error(f"Error disconnecting signals: {e}")
        
        # 8. remove the event filter
        if hasattr(self, 'window'):
            self.window.removeEventFilter(self)
            
        # 9. Close window
        self.window.close()
            
        # 10. Emit window closed signal
        self.window_closed.emit(self.device_id)
        
        logger.info(f"Main window resources cleaned up for device: {self.device_id}")