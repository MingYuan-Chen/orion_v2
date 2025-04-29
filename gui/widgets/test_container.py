"""
Test container widget module
Provides a container for test group widgets with scrolling capability
"""

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QGroupBox
from PySide6.QtCore import Signal

from gui.widgets.test_group_widget import TestGroupWidget

class TestContainer(QScrollArea):
    """
    A container widget for managing multiple test groups
    Provides scrolling capability and manages test group widgets
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
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setStyleSheet("background-color: #252526;")
        
        # Create scroll content widget
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #252526;")
        
        # Create layout for scroll content
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        
        # Set scroll content widget
        self.setWidget(self.scroll_content)
        
        # Dictionary to store test widgets
        self.test_widgets = {}
    
    def add_test_group(self, test_id, title):
        """
        Add a test group widget
        
        Args:
            test_id: Test ID
            title: Test group title
            
        Returns:
            Added TestGroupWidget
        """
        # Create test group widget
        test_widget = TestGroupWidget(test_id, title)
        
        # Connect test started signal
        test_widget.test_started.connect(lambda tid: self.test_selected.emit(tid))
        
        # Add to layout
        self.content_layout.addWidget(test_widget)
        
        # Store in dictionary
        self.test_widgets[test_id] = test_widget
        
        return test_widget
    
    def get_test_widget(self, test_id):
        """
        Get test widget by ID
        
        Args:
            test_id: Test ID
            
        Returns:
            TestGroupWidget or None if not found
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
    
    def set_test_progress(self, test_id, value):
        """
        Set progress for a specific test
        
        Args:
            test_id: Test ID
            value: Progress value (0-100)
        """
        if test_id in self.test_widgets:
            self.test_widgets[test_id].set_progress(value)
    
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