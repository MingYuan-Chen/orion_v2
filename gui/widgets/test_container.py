"""
Test container widget module
Provides a container for test group widgets with scrolling capability
"""

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QColor

class TestItemWidget(QWidget):
    """
    Test item widget, displaying the status and control for a single test
    """
    
    # Define signals
    test_started = Signal(str)  # Emitted when test button is clicked, passes test_id
    
    def __init__(self, test_id, test_name, parent=None):
        """
        Initialize test item widget
        
        Args:
            test_id: Test ID
            test_name: Test name
            parent: Parent widget
        """
        super().__init__(parent)
        self.test_id = test_id
        self.test_name = test_name
        
        # Status indicator colors
        self.status_colors = {
            "not_started": QColor("#808080"),  # gray
            "running": QColor("#FF9800"),      # orange
            "pass": QColor("#4CAF50"),         # green
            "fail": QColor("#F44336")          # red
        }
        
        # Set default status
        self.current_status = "not_started"
        self.status_message = ""
        
        # Flag to mark tests that should always remain disabled (In Dev tests)
        self.always_disabled = False
        
        # Create layout
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        # Create main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(QSize(16, 16))
        self.status_indicator.setStyleSheet(f"background-color: {self.status_colors[self.current_status].name()}; border-radius: 8px;")
        layout.addWidget(self.status_indicator)
        
        # Test name label
        self.name_label = QLabel(self.test_name)
        self.name_label.setStyleSheet("color: white;")
        layout.addWidget(self.name_label)
        
        # Add stretch to push button to the right
        layout.addStretch()
        
        # Start test button
        self.test_button = QPushButton("Start Test")
        self.test_button.setFixedSize(80, 25)
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        self.test_button.clicked.connect(self._on_test_button_clicked)
        layout.addWidget(self.test_button)
        
        # ensure the fixed height
        self.setFixedHeight(32)
    
    def set_always_disabled(self, always_disabled):
        """
        Set whether this test should always remain disabled
        
        Args:
            always_disabled: Whether the test should always be disabled
        """
        self.always_disabled = always_disabled
        if always_disabled:
            self.test_button.setEnabled(False)
            self.test_button.setText("In Dev")
            self.test_button.setStyleSheet("""
                QPushButton {
                    background-color: #666666;
                    color: #CCCCCC;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 2px;
                }
            """)
    
    def _on_test_button_clicked(self):
        """Handle test button click"""
        # Don't emit signal if test is always disabled
        if not self.always_disabled:
            self.test_started.emit(self.test_id)
    
    def set_state(self, state, message=""):
        """
        Set the state of the test
        
        Args:
            state: State ('not_started', 'running', 'pass', 'fail')
            message: Optional status message
        """
        self.current_status = state
        self.status_message = message
        
        # Update status indicator color
        if state in self.status_colors:
            self.status_indicator.setStyleSheet(f"background-color: {self.status_colors[state].name()}; border-radius: 8px;")
        
        # Update button state based on test state
        if state == "running":
            self.test_button.setEnabled(False)
            if not message:
                self.test_button.setText("Running...")
            else:
                # if there is a message, it may contain progress information
                self.test_button.setText(message)
        elif state == "pass" or state == "fail":
            # If test is always disabled, keep it disabled
            if self.always_disabled:
                self.test_button.setEnabled(False)
                self.test_button.setText("In Dev")
            else:
                self.test_button.setEnabled(True)
                self.test_button.setText("Re-Test")
        else:  # not_started
            # If test is always disabled, keep it disabled
            if self.always_disabled:
                self.test_button.setEnabled(False)
                self.test_button.setText("In Dev")
            else:
                self.test_button.setEnabled(True)
                self.test_button.setText("Start Test")
    
    def set_enabled(self, enabled):
        """
        Enable or disable the test button
        
        Args:
            enabled: Whether to enable the button
        """
        # If test is always disabled, don't enable it
        if self.always_disabled:
            self.test_button.setEnabled(False)
        else:
            self.test_button.setEnabled(enabled)

class TestContainer(QScrollArea):
    """
    A container widget for managing multiple test items
    Provides scrolling capability and manages test item widgets
    """
    
    # Define signals
    test_selected = Signal(str)  # Emitted when a test is selected, passes test_id
    
    def __init__(self, parent=None):
        """
        Initialize test container
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set scroll area properties
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Set style
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #252526;
            }
            QScrollBar:vertical {
                background: #333333;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Create content widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #252526; color: transparent;")
        
        # Create content layout
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(4)
        
        # Set content widget
        self.setWidget(self.content_widget)
        
        # Dictionary to store test widgets
        self.test_widgets = {}
        
        # Add stretch to ensure content is aligned at the top
        self.content_layout.addStretch()
    
    def add_test_group(self, test_id, title):
        """
        Add a test item widget
        
        Args:
            test_id: Test ID
            title: Test name
            
        Returns:
            Added TestItemWidget
        """
        # Create test item widget
        test_widget = TestItemWidget(test_id, title)
        
        # Connect test started signal
        test_widget.test_started.connect(lambda tid: self.test_selected.emit(tid))
        
        # Add to layout before the stretch
        self.content_layout.insertWidget(self.content_layout.count() - 1, test_widget)
        
        # Store in dictionary
        self.test_widgets[test_id] = test_widget
        
        return test_widget
    
    def get_test_widget(self, test_id):
        """
        Get test widget by ID
        
        Args:
            test_id: Test ID
            
        Returns:
            TestItemWidget or None if not found
        """
        return self.test_widgets.get(test_id)
    
    def set_test_state(self, test_id, state, message=""):
        """
        Set state for a specific test
        
        Args:
            test_id: Test ID
            state: State ('not_started', 'running', 'pass', 'fail')
            message: Optional message
        """
        if test_id in self.test_widgets:
            self.test_widgets[test_id].set_state(state, message)
    
    def set_all_enabled(self, enabled):
        """
        Enable or disable all test buttons
        
        Args:
            enabled: Whether to enable the buttons
        """
        for widget in self.test_widgets.values():
            widget.set_enabled(enabled)
    
    def get_all_test_ids(self):
        """
        Get all test IDs
        
        Returns:
            List of test IDs
        """
        return list(self.test_widgets.keys())
    
    def set_fixed_height(self, height):
        """
        Set fixed height for the container
        
        Args:
            height: Height value
        """
        self.setFixedHeight(height)
        
    def set_test_progress(self, test_id, progress_percent):
        """
        Set test progress (since the UI design does not have a separate progress bar display, only update the status text)
        
        Args:
            test_id: Test ID
            progress_percent: Progress percentage (0-100)
        """
        # only update the test state, because the current UI design does not have a separate progress indicator
        if test_id in self.test_widgets:
            # get the test widget
            widget = self.test_widgets[test_id]
            if widget.current_status == "running":
                # according to the user's requirement, the button only displays "Running", not the specific progress
                widget.set_state("running", "Running") 