"""
Diagnostic item widget module
Provides a widget for displaying individual diagnostic test status and results
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter, QBrush

class StatusIndicator(QLabel):
    """Circular status indicator showing different colors for different statuses"""
    
    def __init__(self, color=QColor("#808080"), parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(QSize(16, 16))
        
    def setColor(self, color):
        """Set the indicator color"""
        self.color = color
        self.update()
        
    def paintEvent(self, event):
        """Draw the circular indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)


class DiagnosticItemWidget(QWidget):
    """Diagnostic item widget, displaying the status and result of a single test"""
    
    def __init__(self, test_id, test_name, parent=None):
        super().__init__(parent)
        self.test_id = test_id
        self.test_name = test_name
        self.status = "PENDING"
        self.time_value = "--:--:--"
        
        # status color mapping
        self.status_colors = {
            "PASS": QColor("#4CAF50"),      # green
            "FAIL": QColor("#F44336"),      # red
            "WARNING": QColor("#FF9800"),   # orange
            "PENDING": QColor("#9E9E9E")    # gray
        }
        
        # create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setAlignment(Qt.AlignVCenter)
        
        # status indicator
        self.indicator = StatusIndicator(self.status_colors["PENDING"])
        layout.addWidget(self.indicator, 0, Qt.AlignVCenter)
        
        # test name
        self.name_label = QLabel(test_name)
        self.name_label.setStyleSheet("font-weight: normal; color: white;")
        layout.addWidget(self.name_label, 0, Qt.AlignVCenter)
        
        # add stretch
        layout.addStretch()
        
        # status label
        self.status_label = QLabel("PENDING")
        self.status_label.setStyleSheet("font-weight: bold; color: #9E9E9E;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.status_label, 0, Qt.AlignVCenter)
        
        # time/value label
        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("color: #AAAAAA;")
        self.time_label.setFixedWidth(80)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.time_label, 0, Qt.AlignVCenter)
        
    def set_status(self, status, time_value=""):
        """Update the test status and time/value"""
        self.status = status
        if time_value:
            self.time_value = time_value
            
        # update UI
        if status in self.status_colors:
            color = self.status_colors[status]
            self.indicator.setColor(color)
            self.status_label.setText(status)
            self.status_label.setStyleSheet(f"font-weight: bold; color: {color.name()};")
            self.time_label.setText(self.time_value)
    
    def reset(self):
        """Reset to pending state"""
        self.set_status("PENDING", "--:--:--")
    
    def get_test_id(self):
        """Return the test ID"""
        return self.test_id 