"""
Test group widget module
Provides a reusable widget for test modules, encapsulating the common UI behavior
"""

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QProgressBar, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Signal, QSize, Qt

class TestGroupWidget(QGroupBox):
    """
    A reusable widget for test modules
    Encapsulates label, status indicator, button and progress handling
    """
    
    # Define signals
    test_started = Signal(str)  # Emitted when test button is clicked, passes test_id
    
    def __init__(self, test_id, title, parent=None):
        """
        Initialize test group widget
        
        Args:
            test_id: Test ID
            title: Test group title
            parent: Parent widget
        """
        super().__init__(title, parent)
        
        # Save test ID
        self.test_id = test_id
        
        # Create UI components
        self._init_ui()
        
        # Set initial state
        self.set_state("not_started")
    
    def _init_ui(self):
        """Initialize UI components"""
        # Create container layout
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(9, 15, 9, 9)
        container_layout.setSpacing(5)
        
        # Create top horizontal layout (status indicator and button)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 5)
        top_layout.setSpacing(5)
        
        # Create status indicator
        self.status_label = QLabel()
        self.status_label.setFixedSize(QSize(16, 16))
        self.status_label.setStyleSheet("background-color: #333333; border-radius: 8px;")
        top_layout.addWidget(self.status_label)
        
        # Add stretchable space to push button to the right
        top_layout.addStretch()
        
        # Create test button
        self.test_button = QPushButton("Start Test")
        # Set button fixed width and height
        self.test_button.setFixedSize(100, 25)
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        self.test_button.clicked.connect(self._on_button_clicked)
        top_layout.addWidget(self.test_button)
        
        # Add top layout to container layout
        container_layout.addLayout(top_layout)
        
        # Add a small space to separate progress bar and button
        spacer_item = QSpacerItem(0, 3)  # Only 3 pixels height
        container_layout.addItem(spacer_item)
        
        # Create progress bar (default hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)  # Increase height to ensure digits are fully visible
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3F3F46;
                border-radius: 2px;
                text-align: center;
                background-color: #252526;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
            }
        """)
        
        # Add progress bar directly to container layout
        container_layout.addWidget(self.progress_bar)
        
        # Set fixed height to ensure enough space for all elements, even when progress bar is visible
        self.setFixedHeight(70)  # Decrease overall height
    
    def _on_button_clicked(self):
        """Handle button click event"""
        # Emit signal with test ID
        self.test_started.emit(self.test_id)
    
    def set_state(self, state, message=""):
        """
        Set test state and update UI accordingly
        
        Args:
            state: State ('not_started', 'running', 'pass', 'fail')
            message: Optional message
        """
        if state == "not_started":
            self.status_label.setStyleSheet("background-color: #333333; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            self.test_button.setText("Start Test")
            self.test_button.setEnabled(True)
            self.progress_bar.setVisible(False)
        
        elif state == "running":
            self.status_label.setStyleSheet("background-color: #FFA500; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            self.test_button.setText("Running...")
            self.test_button.setEnabled(False)
            self.progress_bar.setVisible(True)
        
        elif state == "pass":
            self.status_label.setStyleSheet("background-color: #00AA00; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            self.test_button.setText("Start Test")
            self.test_button.setEnabled(True)
            self.progress_bar.setVisible(False)
        
        elif state == "fail":
            self.status_label.setStyleSheet("background-color: #FF0000; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            self.test_button.setText("Start Test")
            self.test_button.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def set_progress(self, value):
        """
        Set progress bar value
        
        Args:
            value: Progress value (0-100)
        """
        self.progress_bar.setValue(value)
    
    def set_button_enabled(self, enabled):
        """
        Enable or disable the test button
        
        Args:
            enabled: Whether to enable the button
        """
        self.test_button.setEnabled(enabled)
    
    def get_status_label(self):
        """Get the status label widget"""
        return self.status_label
    
    def get_test_button(self):
        """Get the test button widget"""
        return self.test_button
    
    def get_progress_bar(self):
        """Get the progress bar widget"""
        return self.progress_bar 