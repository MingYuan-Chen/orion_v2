"""
Diagnostic container module
Provides a container for diagnostic item widgets with scrolling capability
"""

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, QTimer

from gui.widgets.diagnostic_item_widget import DiagnosticItemWidget

class DiagnosticContainer(QScrollArea):
    """
    Container for diagnostic items with scrolling capability
    Manages multiple diagnostic item widgets
    """
    
    # define signal
    item_clicked = Signal(str)  # when the diagnostic item is clicked, emit the test_id
    
    def __init__(self, parent=None):
        """
        Initialize diagnostic container
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # set the scroll area properties
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        # set the style
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2E2E2E;
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
        
        # create the content widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        
        # create the content layout
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 0, 5, 8)
        self.content_layout.setSpacing(2)
        
        # set the content widget
        self.setWidget(self.content_widget)
        
        # store the diagnostic items
        self.diagnostic_items = {}
        
        # add stretch to ensure the content is aligned at the top
        self.content_layout.addStretch()
    
    def add_diagnostic_item(self, test_id, test_name):
        """
        add the diagnostic item
        
        Args:
            test_id: the test id
            test_name: the test name
            
        Returns:
            the added DiagnosticItemWidget
        """
        # create the diagnostic item widget
        item = DiagnosticItemWidget(test_id, test_name)
        
        # add the item to the layout before the stretch
        self.content_layout.insertWidget(self.content_layout.count()-1, item)
        
        # store the diagnostic item
        self.diagnostic_items[test_id] = item
        
        return item
    
    def get_diagnostic_item(self, test_id):
        """
        get the diagnostic item by the test id
        
        Args:
            test_id: the test id
            
        Returns:
            the DiagnosticItemWidget or None (if not found)
        """
        return self.diagnostic_items.get(test_id)
    
    def update_item_status(self, test_id, status, time_value=""):
        """
        update the diagnostic item status
        
        Args:
            test_id: the test id
            status: the status ('PASS', 'FAIL', 'WARNING', 'PENDING')
            time_value: the optional time/value
        """
        if test_id in self.diagnostic_items:
            self.diagnostic_items[test_id].set_status(status, time_value)
    
    def reset_all_items(self):
        """
        reset all the diagnostic items to the PENDING status
        """
        for item in self.diagnostic_items.values():
            item.reset()
    
    def get_all_test_ids(self):
        """
        get all the test ids
        
        Returns:
            the list of test ids
        """
        return list(self.diagnostic_items.keys())
    
    def set_fixed_height(self, height):
        """
        set the fixed height
        
        Args:
            height: the height value
        """
        self.setFixedHeight(height)
    
    def scroll_to_item(self, test_id):
        """
        Scroll to the specific diagnostic item
        
        Args:
            test_id: the test id to scroll to
        """
        if test_id in self.diagnostic_items:
            # Get the widget
            item = self.diagnostic_items[test_id]
            
            # Scroll to the item's position
            self.ensureWidgetVisible(item, 0, 5) 