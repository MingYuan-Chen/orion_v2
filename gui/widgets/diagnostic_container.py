"""
Diagnostic container module
Provides a container for diagnostic item widgets with scrolling capability
"""

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal

from gui.widgets.diagnostic_item_widget import DiagnosticItemWidget

class DiagnosticContainer(QScrollArea):
    """
    Container for diagnostic items with scrolling capability
    Manages multiple diagnostic item widgets
    """
    
    # 定义信号
    item_clicked = Signal(str)  # 当诊断项目被点击时发出，传递test_id
    
    def __init__(self, parent=None):
        """
        Initialize diagnostic container
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # 设置滚动区域属性
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        # 设置样式
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
        
        # 创建内容控件
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        
        # 创建内容布局
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 0, 5, 8)
        self.content_layout.setSpacing(2)
        
        # 设置内容控件
        self.setWidget(self.content_widget)
        
        # 存储诊断项目
        self.diagnostic_items = {}
        
        # 添加拉伸以确保内容靠上对齐
        self.content_layout.addStretch()
    
    def add_diagnostic_item(self, test_id, test_name):
        """
        添加诊断项目
        
        Args:
            test_id: 测试ID
            test_name: 测试名称
            
        Returns:
            添加的DiagnosticItemWidget
        """
        # 创建诊断项目控件
        item = DiagnosticItemWidget(test_id, test_name)
        
        # 在stretch之前添加到布局
        self.content_layout.insertWidget(self.content_layout.count()-1, item)
        
        # 存储诊断项目
        self.diagnostic_items[test_id] = item
        
        return item
    
    def get_diagnostic_item(self, test_id):
        """
        通过ID获取诊断项目控件
        
        Args:
            test_id: 测试ID
            
        Returns:
            DiagnosticItemWidget或者None（如果未找到）
        """
        return self.diagnostic_items.get(test_id)
    
    def update_item_status(self, test_id, status, time_value=""):
        """
        更新诊断项目状态
        
        Args:
            test_id: 测试ID
            status: 状态（'PASS', 'FAIL', 'WARNING', 'PENDING'）
            time_value: 可选的时间/值
        """
        if test_id in self.diagnostic_items:
            self.diagnostic_items[test_id].set_status(status, time_value)
    
    def reset_all_items(self):
        """
        重置所有诊断项目为PENDING状态
        """
        for item in self.diagnostic_items.values():
            item.reset()
    
    def get_all_test_ids(self):
        """
        获取所有测试ID
        
        Returns:
            测试ID列表
        """
        return list(self.diagnostic_items.keys())
    
    def set_fixed_height(self, height):
        """
        设置容器固定高度
        
        Args:
            height: 高度值
        """
        self.setFixedHeight(height) 