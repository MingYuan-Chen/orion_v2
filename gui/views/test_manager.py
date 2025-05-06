"""
Test manager view module
Responsible for managing test execution, UI updates and result tracking
"""
from typing import Dict, List, Any, Optional
import datetime
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtGui import QColor

from util.logger import logger
from core.services.hardware_test_manager import HardwareTestManagerService
from gui.widgets.test_container import TestContainer
from gui.widgets.test_selection_widget import TestSelectionDialog


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
        self.original_test_sequence = ["functionality_audio", "functionality_backlight", "functionality_battery",
                               "functionality_eeprom", "functionality_emmc", "functionality_lcd", "functionality_led",
                               "functionality_usb"]
        self.test_sequence = self.original_test_sequence.copy()
        self.current_test_index = -1
        self.is_test_all_running = False
        
        # Parent widget reference for dialogs
        self.parent_widget = None
        
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
        
        # Connect new interaction signals
        self.hw_test_manager.test_pre_condition_required.connect(self._on_test_pre_condition_required)
        self.hw_test_manager.test_post_check_required.connect(self._on_test_post_check_required)
    
    def set_ui_components(self, test_container: TestContainer, test_all_button: QPushButton,
                          result_table: QTableWidget, progress_bar: QProgressBar, parent_widget=None):
        """
        Set UI components references
        
        Args:
            test_container: Test container widget
            test_all_button: "Test All" button
            result_table: Table widget for displaying test steps
            progress_bar: Progress bar for displaying test progress
            parent_widget: Parent widget for dialogs
        """
        self.test_container = test_container
        self.test_all_button = test_all_button
        self.result_table = result_table
        self.progress_bar = progress_bar
        self.parent_widget = parent_widget
        
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
        """Start executing selected test modules in sequence"""
        # if the test sequence is already running, ignore this call
        if self.is_test_all_running:
            return
            
        # create the test selection dialog - always use the original test sequence
        test_mapping = {test_id: test_id.replace("functionality_", "").capitalize() for test_id in self.original_test_sequence}
        dialog = TestSelectionDialog(test_mapping, self.parent_widget)
        
        # show the dialog and wait for user selection
        if dialog.exec() != QDialog.Accepted:
            logger.info("Test sequence selection cancelled")
            return
            
        # get the user selected test sequence
        selected_tests = dialog.get_selected_tests()
        if not selected_tests:
            logger.warning("No tests selected")
            return
            
        # update the test sequence with the selected tests
        self.test_sequence = selected_tests
        logger.info(f"Selected tests: {', '.join(selected_tests)}")
            
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
        Enable or disable all test buttons
        
        Args:
            enabled: Whether to enable the buttons
        """
        if self.test_container:
            for test_id in self.test_container.get_all_test_ids():
                self.test_container.get_test_widget(test_id).set_button_enabled(enabled)
            
        # Enable or disable "Test All" button
        if self.test_all_button:
            self.test_all_button.setEnabled(enabled)
    
    @Slot(str, int, str)
    def _on_test_pre_condition_required(self, test_id: str, step_index: int, pre_condition: str):
        """
        Handle test pre-condition required event
        
        Args:
            test_id: Test ID
            step_index: Step index
            pre_condition: Pre-condition instructions
        """
        logger.debug(f"Pre-condition required for test {test_id}, step {step_index}: {pre_condition}")
        
        if not self.parent_widget:
            # No parent widget to show dialog, continue automatically
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, True)
            return
            
        # Create and show pre-condition dialog
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle("Pre-condition required")
        msg_box.setText(f"Step {step_index + 1} preparation:")
        msg_box.setInformativeText(pre_condition)
        msg_box.setIcon(QMessageBox.Information)
        
        # Set the dark style sheet
        msg_box.setStyleSheet(self._get_dark_style_sheet())
        
        # Add custom buttons
        confirm_button = msg_box.addButton("Confirm and continue", QMessageBox.AcceptRole)
        skip_button = msg_box.addButton("Skip", QMessageBox.RejectRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.DestructiveRole)
        
        # Make buttons larger for easier clicking
        confirm_button.setMinimumSize(150, 30)
        skip_button.setMinimumSize(100, 30)
        cancel_button.setMinimumSize(100, 30)
        
        # Set minimum width
        msg_box.setMinimumWidth(450)
        
        # Adjust the width of the text label in the message box
        for label in msg_box.findChildren(QLabel):
            if label.text() == pre_condition:
                # Set the width of the text label and enable word wrap
                label.setMinimumWidth(350)
                label.setWordWrap(True)
        
        # Show dialog
        msg_box.exec()
        
        # Handle response
        clicked_button = msg_box.clickedButton()
        if clicked_button == confirm_button:
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, True)
        elif clicked_button == skip_button:
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, False)
        else:  # cancel_button or dialog closed
            self.hw_test_manager.handle_pre_condition_cancel(test_id, step_index)
    
    @Slot(str, int, str)
    def _on_test_post_check_required(self, test_id: str, step_index: int, post_check: str):
        """
        Handle test post-check required event
        
        Args:
            test_id: Test ID
            step_index: Step index
            post_check: Post-check instructions
        """
        logger.debug(f"Post-check required for test {test_id}, step {step_index}: {post_check}")
        
        if not self.parent_widget:
            # No parent widget to show dialog, continue automatically
            self.hw_test_manager.handle_post_check_response(test_id, step_index, True)
            return
            
        # Create and show post-check dialog
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle("Result confirmation")
        msg_box.setText(f"Step {step_index + 1} verification:")
        msg_box.setInformativeText(post_check)
        msg_box.setIcon(QMessageBox.Question)
        
        # Set the dark style sheet with wider dimensions
        style_sheet = self._get_dark_style_sheet()
        msg_box.setStyleSheet(style_sheet)
        
        # Add custom buttons
        pass_button = msg_box.addButton("Pass", QMessageBox.AcceptRole)
        fail_button = msg_box.addButton("Fail", QMessageBox.RejectRole)
        
        # Make buttons larger for easier clicking
        pass_button.setMinimumSize(100, 30)
        fail_button.setMinimumSize(100, 30)
        
        # Set fixed width
        msg_box.setMinimumWidth(450)
        
        # Adjust the width of the text label in the message box
        for label in msg_box.findChildren(QLabel):
            if label.text() == post_check:
                # Set the width of the text label and enable word wrap
                label.setMinimumWidth(350)
                label.setWordWrap(True)
        
        # Show dialog
        msg_box.exec()
        
        # Handle response
        clicked_button = msg_box.clickedButton()
        self.hw_test_manager.handle_post_check_response(
            test_id, step_index, clicked_button == pass_button)

    def _get_dark_style_sheet(self):
        """Return the dark style sheet"""
        return """
            QMessageBox {
                background-color: #2E2E2E;
                color: white;
                min-width: 400px;
            }
            QLabel {
                color: white;
                font-weight: bold;
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
        """ 