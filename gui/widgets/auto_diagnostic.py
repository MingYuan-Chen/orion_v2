from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPainter, QBrush

class StatusIndicator(QLabel):
    """Gradient status indicator, showing different colors for different statuses"""
    
    def __init__(self, color=QColor("#808080"), parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(QSize(16, 16))  # 恢复到原始尺寸16x16
        
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
        painter.drawEllipse(2, 2, 12, 12)  # 恢复原始绘制尺寸
        
class DiagnosticItem(QWidget):
    """Diagnostic item component, displaying the status and result of a single test"""
    
    def __init__(self, test_name, parent=None):
        super().__init__(parent)
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
        layout.setContentsMargins(10, 7, 10, 7)  # 增加上下内边距，确保内容完整显示
        layout.setAlignment(Qt.AlignVCenter)  # 设置垂直居中
        
        # status indicator
        self.indicator = StatusIndicator(self.status_colors["PENDING"])
        layout.addWidget(self.indicator, 0, Qt.AlignVCenter)  # 设置垂直居中
        
        # test name
        self.name_label = QLabel(test_name)
        self.name_label.setStyleSheet("font-weight: normal; color: white;")
        layout.addWidget(self.name_label, 0, Qt.AlignVCenter)  # 设置垂直居中
        
        # add stretch
        layout.addStretch()
        
        # status label
        self.status_label = QLabel("PENDING")
        self.status_label.setStyleSheet("font-weight: bold; color: #9E9E9E;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.status_label, 0, Qt.AlignVCenter)  # 设置垂直居中
        
        # time/value label
        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("color: #AAAAAA;")
        self.time_label.setFixedWidth(80)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.time_label, 0, Qt.AlignVCenter)  # 设置垂直居中
        
    def setStatus(self, status, time_value=""):
        """Update the test status and time/value"""
        self.status = status
        if time_value:
            self.time_value = time_value
            
        # update UI
        if status in self.status_colors:
            color = self.status_colors[status]
            self.indicator.setColor(color)
            self.status_label.setText(status)
            self.status_label.setStyleSheet(f"font-weight: bold; color: {color.name()};")  # 移除字体大小设置
            self.time_label.setText(self.time_value)

class AutoDiagnosticWidget(QWidget):
    """Auto diagnostic component, displaying all test items and running status"""
    
    run_all_tests = Signal()  # signal to run all tests
    export_report = Signal()  # signal to export report
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # set style
        self.setStyleSheet("""
            QWidget#diagnosticWidget {
                background-color: #1E1E1E;
                color: white;
                border-radius: 5px;
            }
            QLabel#titleLabel {
                font-weight: bold;
                font-size: 14px;
                color: #4FC3F7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
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
        
        # create main layout - 修改为固定高度并使其填充可用宽度
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 5)  # 恢复原始内边距
        self.main_layout.setSpacing(5)  # 恢复原始间距
        
        # create main container and apply style
        self.main_widget = QWidget()
        self.main_widget.setObjectName("diagnosticWidget")
        widget_layout = QVBoxLayout(self.main_widget)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget)
        
        # create top layout (title and buttons)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 10, 10, 10)  # 恢复原始内边距
        
        # title
        title_label = QLabel("Auto Diagnostic")
        title_label.setObjectName("titleLabel")
        top_layout.addWidget(title_label)
        
        # add stretch
        top_layout.addStretch()
        
        # export report button
        self.export_button = QPushButton("Export Report")
        self.export_button.clicked.connect(self.export_report.emit)
        top_layout.addWidget(self.export_button)
        
        # spacing
        top_layout.addSpacing(10)
        
        # run all tests button
        self.run_button = QPushButton("Run All Tests")
        self.run_button.clicked.connect(self.run_all_tests.emit)
        top_layout.addWidget(self.run_button)
        
        # add top layout to main layout
        widget_layout.addLayout(top_layout)
        
        # add separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333333;")
        line.setMaximumHeight(1)
        widget_layout.addWidget(line)
        
        # create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # test items container
        self.items_container = QWidget()
        self.items_container.setStyleSheet("background-color: transparent;")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(5, 2, 5, 8)  # 增加底部边距
        self.items_layout.setSpacing(2)  # 添加少量间距
        
        # set test items container as the content of the scroll area
        self.scroll_area.setWidget(self.items_container)
        
        # add scroll area to main layout
        widget_layout.addWidget(self.scroll_area)
        
        # store test items
        self.diagnostic_items = {}
        
        # calculate item height - 使用更精确的计算方式
        item_height = 32  # 略微增加单个项目高度，包含边距和间距
        visible_items = 5
        
        # 设置滚动区域高度，确保有足够空间
        scroll_height = item_height * visible_items + 15  # 额外增加15像素空间
        self.scroll_area.setFixedHeight(scroll_height)
        
        # 设置主组件为固定高度
        total_height = scroll_height + 60  # 标题区域大约占60像素
        self.setFixedHeight(total_height)
        
        # 添加一个stretch到items_layout末尾，确保项目靠上排列
        self.items_layout.addStretch()
    
    def addDiagnosticItem(self, test_id, test_name):
        """Add diagnostic test item"""
        item = DiagnosticItem(test_name)
        self.items_layout.addWidget(item)  # 直接添加，不需要insertWidget
        self.diagnostic_items[test_id] = item
        return item
        
    def updateItemStatus(self, test_id, status, time_value=""):
        """Update the status of the test item"""
        if test_id in self.diagnostic_items:
            self.diagnostic_items[test_id].setStatus(status, time_value)
            
    def resetAllItems(self):
        """Reset all test items to pending state"""
        for item in self.diagnostic_items.values():
            item.setStatus("PENDING")
