"""
Test manager view module
Responsible for managing test execution, UI updates and result tracking
"""
from typing import Dict, List, Any, Optional
import datetime
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QColor

from util.logger import logger
from core.services.hardware_test_manager import HardwareTestManagerService
from gui.widgets.test_container import TestContainer


class TestManagerView(QObject):
    """
    Test manager view class
    Responsible for managing test execution, UI updates and result tracking
    """
    
    # define a signal for all tests completed
    all_tests_completed = Signal()
    
    def __init__(self, device_id: str, hw_test_manager: HardwareTestManagerService):
        """
        Initialize test manager view
        
        Args:
            device_id: Device ID
            hw_test_manager: Hardware test manager service
        """
        super().__init__()
        
        # save device ID and hardware test manager
        self.device_id = device_id
        self.hw_test_manager = hw_test_manager
        
        # test UI components reference
        self.test_container = None  # test container reference
        self.test_all_button = None  # test all button reference 
        self.result_table = None  # test result table reference
        self.progress_bar = None  # test progress bar reference
        
        # test status tracking
        self.test_results = {}  # store test results
        self.test_progress_records = {}  # store test progress records
        
        # test sequence related
        self.test_sequence = ["usb_ports", "emmc", "eeprom", "battery", "backlight", "led", "audio"]
        self.current_test_index = -1
        self.is_test_all_running = False
        
        # connect signals
        self._connect_signals()
        
        logger.info("Test manager view initialized")
    
    def _connect_signals(self):
        """Connect hardware test manager signals"""
        # connect hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_step_completed.connect(self._on_test_step_completed)
        self.hw_test_manager.test_step_retrying.connect(self._on_test_step_retrying)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
    
    def set_ui_components(self, test_container: TestContainer, test_all_button: QPushButton,
                           result_table: QTableWidget, progress_bar: QProgressBar):
        """
        Set UI components references
        
        Args:
            test_container: Test container widget
            test_all_button: "Test All" button
            result_table: Table widget for displaying test steps
            progress_bar: Progress bar for displaying test progress
        """
        self.test_container = test_container
        self.test_all_button = test_all_button
        self.result_table = result_table
        self.progress_bar = progress_bar
        
        # Connect test container signals
        self.test_container.test_selected.connect(self.start_test)
        
        # Connect test all button
        self.test_all_button.clicked.connect(self.start_test_all)
        
        # initialize test results and progress records
        test_ids = self.test_container.get_all_test_ids()
        for test_id in test_ids:
            self.test_results[test_id] = {
                "steps": [],
                "success": None,
                "message": ""
            }
            self.test_progress_records[test_id] = []
            
        # Set initial state for all tests
        for test_id in test_ids:
            self.test_container.set_test_state(test_id, "not_started")
    
    def start_test(self, test_id: str):
        """
        Start a specific test
        
        Args:
            test_id: Test ID to start
        """
        # clear the result of the previous test
        if self.result_table:
            self.result_table.setRowCount(0)
        
        # start the test
        self.hw_test_manager.start_test(self.device_id, test_id)
        
        # record the test start
        logger.info(f"Starting {test_id} test for device {self.device_id}")
    
    def start_test_all(self):
        """Start executing all test modules in sequence"""
        # if the test sequence is already running, ignore this call
        if self.is_test_all_running:
            return
            
        # clear the result of the previous test
        if self.result_table:
            self.result_table.setRowCount(0)
        
        # reset the test sequence
        self.current_test_index = -1
        self.is_test_all_running = True
        
        # disable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(False)
            self.test_all_button.setText("Running...")
        
        # start the first test
        self._execute_next_test()
        
        # record the test sequence start
        logger.info("Starting Test All sequence")
    
    def stop_current_test(self):
        """Stop the currently running test"""
        if self.hw_test_manager:
            self.hw_test_manager.stop_current_test()
    
    @Slot(str)
    def _on_test_started(self, test_id: str):
        """
        Handle test started event
        
        Args:
            test_id: Test ID
        """
        # update the test UI state
        self.test_container.set_test_state(test_id, "running")
        
        # initialize the test result storage
        self.test_results[test_id] = {
            "steps": [],
            "success": None,
            "message": ""
        }
        
        # clear the test progress records
        self.test_progress_records[test_id] = []
        
        logger.info(f"Test started: {test_id} for device {self.device_id}")

    @Slot(str, bool, str)
    def _on_test_completed(self, test_id: str, success: bool, message: str):
        """
        Handle test completed event
        
        Args:
            test_id: Test ID
            success: Whether test passed
            message: Result message
        """
        # store the test results
        if test_id in self.test_results:
            self.test_results[test_id]["success"] = success
            self.test_results[test_id]["message"] = message
        
        # update the test UI state
        self.test_container.set_test_state(test_id, "pass" if success else "fail", message)
        
        # record the test completed
        if success:
            logger.info(f"Test {test_id} completed: {message}")
        else:
            logger.error(f"Test {test_id} completed: {message}")
        
        # if we are running the test sequence, execute the next test
        if self.is_test_all_running:
            QTimer.singleShot(1000, self._execute_next_test)  # wait 1 second before starting the next test

    @Slot(str, int, bool, str)
    def _on_test_step_completed(self, test_id: str, step_index: int, success: bool, message: str):
        """
        Handle test step completed event
        
        Args:
            test_id: Test ID
            step_index: Step index
            success: Whether step passed
            message: Step result message
        """
        # store the step results
        if test_id in self.test_results:
            self.test_results[test_id]["steps"].append({
                "index": step_index,
                "success": success,
                "message": message
            })
        
        # update the test step UI
        if self.result_table:
            table = self.result_table
            row = table.rowCount()
            table.insertRow(row)
            
            # get the step description
            step_description = ""
            if test_id in self.hw_test_manager.test_workers and len(self.hw_test_manager.test_workers[test_id].steps) > step_index:
                step = self.hw_test_manager.test_workers[test_id].steps[step_index]
                step_description = step.description
            
            # add the step details
            table.setItem(row, 0, QTableWidgetItem(step_description))
            table.setItem(row, 1, QTableWidgetItem("Pass" if success else "Fail"))
            table.setItem(row, 2, QTableWidgetItem(message))
            
            # set the row color
            color = QColor("#00AA00") if success else QColor("#FF0000")
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setForeground(color)
            
            # scroll to the latest item
            table.scrollToBottom()
        
        # record the step completed
        if success:
            logger.info(f"Test {test_id} step {step_index+1}: {message}")
        else:
            logger.warning(f"Test {test_id} step {step_index+1}: {message}")
    
    @Slot(str, int, int, int, str)
    def _on_test_step_retrying(self, test_id: str, step_index: int, retry_count: int, max_retries: int, error: str):
        """
        Handle test step retry event
        
        Args:
            test_id: Test ID
            step_index: Step index
            retry_count: Current retry count
            max_retries: Maximum retry count
            error: Error message
        """
        # record the retry
        logger.warning(f"Test {test_id} step {step_index+1} retrying ({retry_count}/{max_retries}): {error}")
    
    @Slot(str, int, int)
    def _on_test_progress(self, test_id: str, current_step: int, total_steps: int):
        """
        Handle test progress event
        
        Args:
            test_id: Test ID
            current_step: Current step index (starts from 1)
            total_steps: Total number of steps
        """
        # update the progress bar
        progress_pct = int((current_step / total_steps) * 100)
        
        # Update global progress bar
        if self.progress_bar:
            self.progress_bar.setValue(progress_pct)
        
        # Update test-specific progress
        self.test_container.set_test_progress(test_id, progress_pct)
        
        # record the progress of the actual steps
        if current_step > 0:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            progress_record = {
                "timestamp": timestamp,
                "current_step": current_step,
                "total_steps": total_steps,
                "progress_percentage": progress_pct
            }
            self.test_progress_records[test_id].append(progress_record)
        
        # record the progress (every 25% completion)
        if current_step % max(1, total_steps // 4) == 0 or current_step == total_steps:
            logger.info(f"Test {test_id} progress: {current_step}/{total_steps} ({progress_pct}%)")
    
    def _execute_next_test(self):
        """Execute next test in the sequence"""
        self.current_test_index += 1
        
        # check if all tests are completed
        if self.current_test_index >= len(self.test_sequence):
            self._complete_test_all()
            return
            
        # get the next test ID
        test_id = self.test_sequence[self.current_test_index]
        
        # start the test
        self.start_test(test_id)

    def _complete_test_all(self):
        """Complete Test All sequence"""
        self.is_test_all_running = False
        self.current_test_index = -1
        
        # enable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(True)
            self.test_all_button.setText("Test All")
        
        # record the completion
        logger.info("Test All sequence completed")
        
        # emit the all tests completed signal
        self.all_tests_completed.emit()
    
    def get_test_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current test results
        
        Returns:
            Dictionary containing test results
        """
        return self.test_results
    
    def get_test_progress_records(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get test progress records
        
        Returns:
            Dictionary containing test progress records
        """
        return self.test_progress_records
    
    def cleanup(self):
        """Clean up test manager resources"""
        try:
            logger.debug("Cleaning up TestManagerView resources")
            
            # disconnect all signals
            try:
                self.hw_test_manager.test_started.disconnect(self._on_test_started)
                self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                self.hw_test_manager.test_step_completed.disconnect(self._on_test_step_completed)
                self.hw_test_manager.test_step_retrying.disconnect(self._on_test_step_retrying)
                self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                
                if self.test_container:
                    self.test_container.test_selected.disconnect(self.start_test)
                
                if self.test_all_button:
                    self.test_all_button.clicked.disconnect(self.start_test_all)
            except Exception:
                # signals may already be disconnected, ignore the error
                pass
            
            # clear the references
            self.test_container = None
            self.test_all_button = None
            self.result_table = None
            self.progress_bar = None
            
        except Exception as e:
            logger.error(f"Error during TestManagerView cleanup: {e}") 

    def set_test_buttons_enabled(self, enabled=True):
        """
        启用或禁用所有测试按钮
        
        Args:
            enabled: 是否启用按钮
        """
        if self.test_container:
            for test_id in self.test_container.get_all_test_ids():
                self.test_container.get_test_widget(test_id).set_button_enabled(enabled)
            
        # 启用或禁用"Test All"按钮
        if self.test_all_button:
            self.test_all_button.setEnabled(enabled) 