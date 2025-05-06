"""
Test selection widget module
Provides a widget for selecting test modules to run
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QScrollArea, QWidget
)
from PySide6.QtGui import QColor

class TestSelectionWidget(QWidget):
    """
    Widget for selecting test modules
    """
    
    # Define a signal for when the selection changes
    selection_changed = Signal(list)  # Emit a list of selected test IDs when the selection changes
    
    def __init__(self, test_sequence_mapping, parent=None):
        """
        Initialize the widget
        
        Args:
            test_sequence_mapping: Dictionary mapping test IDs to display names
            parent: Parent widget
        """
        super().__init__(parent)
        
        # set the background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#2E2E2E"))
        self.setPalette(palette)
        
        # apply the dark theme style
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: white;
            }
            QCheckBox {
                color: white;
                spacing: 10px;
                font-size: 13px;
                min-height: 28px;
                background-color: #2E2E2E;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #777777;
                background-color: #3E3E3E;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #0078D7;
                background-color: #0078D7;
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border-color: #0078D7;
            }
        """)
        
        # create the layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2E2E2E;
            }
            QScrollBar:vertical {
                background: #2E2E2E;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # create a widget to place the checkboxes
        scroll_content = QWidget()
        # set the background color of the scroll content area
        scroll_content.setAutoFillBackground(True)
        palette = scroll_content.palette()
        palette.setColor(scroll_content.backgroundRole(), QColor("#2E2E2E"))
        scroll_content.setPalette(palette)
        scroll_content.setStyleSheet("background-color: #2E2E2E;")
        
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 10, 5, 10)
        scroll_layout.setSpacing(8)
        
        # store the checkbox references
        self.checkboxes = {}
        
        # add checkboxes for each test module
        for test_id, display_name in test_sequence_mapping.items():
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(True)  # default to select all
            checkbox.stateChanged.connect(self._on_selection_changed)
            # ensure each checkbox has the correct style
            checkbox.setAutoFillBackground(True)
            palette = checkbox.palette()
            palette.setColor(checkbox.backgroundRole(), QColor("#2E2E2E"))
            palette.setColor(checkbox.foregroundRole(), QColor("white"))
            checkbox.setPalette(palette)
            checkbox.setStyleSheet("background-color: #2E2E2E; color: white;")
            
            self.checkboxes[test_id] = checkbox
            scroll_layout.addWidget(checkbox)
        
        # add a stretch to the bottom
        scroll_layout.addStretch()
        
        # set the content widget
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # create the "select all" button
        select_all_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Deselect All")
        self.select_all_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4FC3F7;
                border: none;
                text-align: left;
                font-size: 13px;
                padding: 5px;
            }
            QPushButton:hover {
                color: #81D4FA;
                text-decoration: underline;
            }
            QPushButton:pressed {
                color: #29B6F6;
            }
        """)
        self.select_all_button.clicked.connect(self._select_all)
        select_all_layout.addWidget(self.select_all_button)
        select_all_layout.addStretch()
        
        # add the select all button layout to the main layout
        main_layout.addLayout(select_all_layout)
    
    def _select_all(self):
        """Select or deselect all checkboxes"""
        # check if all are currently selected
        all_selected = all(checkbox.isChecked() for checkbox in self.checkboxes.values())
        
        # toggle the selection state
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(not all_selected)
        
        # update the button text
        if not all_selected:
            self.select_all_button.setText("Deselect All")
        else:
            self.select_all_button.setText("Select All")
        
        # emit the selection changed signal
        self._on_selection_changed()
    
    def _on_selection_changed(self):
        """Trigger when the selection changes"""
        selected_tests = self.get_selected_tests()
        self.selection_changed.emit(selected_tests)
    
    def get_selected_tests(self):
        """Get the list of selected test IDs"""
        return [test_id for test_id, checkbox in self.checkboxes.items() if checkbox.isChecked()]
    
    def select_all(self, select=True):
        """Select or deselect all checkboxes"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(select)
        
        # update the button text
        if select:
            self.select_all_button.setText("Deselect All")
        else:
            self.select_all_button.setText("Select All")

class TestSelectionDialog(QDialog):
    """
    Dialog for selecting test modules to run
    """
    
    def __init__(self, test_sequence_mapping, parent=None):
        """
        Initialize the dialog
        
        Args:
            test_sequence_mapping: Dictionary mapping test IDs to display names
            parent: Parent widget
        """
        super().__init__(parent)
        
        # set the window properties
        self.setWindowTitle("Select Test Modules")
        self.resize(400, 450)
        
        # force apply the dark background
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#2E2E2E"))
        self.setPalette(palette)
        
        # apply the dark theme style
        self.setStyleSheet("""
            * {
                background-color: #2E2E2E;
                color: white;
            }
            QDialog {
                background-color: #2E2E2E;
                color: white;
                border: 1px solid #555555;
            }
            QWidget {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 5px;
                background-color: #2E2E2E;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
            QPushButton#cancelButton {
                background-color: #555555;
            }
            QPushButton#cancelButton:hover {
                background-color: #666666;
            }
            QPushButton#cancelButton:pressed {
                background-color: #444444;
            }
            QScrollArea {
                background-color: #2E2E2E;
            }
            QCheckBox {
                background-color: #2E2E2E;
                color: white;
            }
        """)
        
        # create the layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # add the description label
        description_label = QLabel("Please select the test modules to execute:")
        description_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(description_label)
        
        # add the selection widget
        self.selection_widget = TestSelectionWidget(test_sequence_mapping, self)
        main_layout.addWidget(self.selection_widget)
        
        # create the button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # add a stretch to push the buttons to the right
        button_layout.addStretch()
        
        # cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setMinimumHeight(36)
        button_layout.addWidget(self.cancel_button)
        
        # start button
        self.start_button = QPushButton("Start Test")
        self.start_button.clicked.connect(self.accept)
        self.start_button.setMinimumHeight(36)
        button_layout.addWidget(self.start_button)
        
        # add the button layout to the main layout
        main_layout.addLayout(button_layout)
    
    def showEvent(self, event):
        """Dialog show event, ensure all sub-widgets have the correct style"""
        super().showEvent(event)
        
        # ensure all sub-widgets have the correct background color
        for widget in self.findChildren(QWidget):
            if not isinstance(widget, QPushButton):  # do not change the button style
                widget.setAutoFillBackground(True)
                palette = widget.palette()
                palette.setColor(widget.backgroundRole(), QColor("#2E2E2E"))
                widget.setPalette(palette)
    
    def get_selected_tests(self):
        """Get the list of selected test IDs"""
        return self.selection_widget.get_selected_tests()
