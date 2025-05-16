from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt, QSize, QRect, Property
from PySide6.QtGui import QPainter, QColor, QPen


class WaitingSpinner(QWidget):
    """
    一个简单的等待加载指示器小部件
    在刷新操作过程中显示旋转效果
    """
    
    def __init__(self, parent=None, center_on_parent=True, 
                 disable_parent_when_spinning=False, lines=12, 
                 line_length=10, line_width=2, radius=10, 
                 speed=1.0, color=QColor(81, 4, 71)):
        super().__init__(parent)
        
        # 保存参数
        self._center_on_parent = center_on_parent
        self._disable_parent_when_spinning = disable_parent_when_spinning
        
        # 设置UI参数
        self._color = color
        self._lines = lines
        self._line_length = line_length
        self._line_width = line_width
        self._radius = radius
        self._speed = speed
        self._current_counter = 0
        
        # 创建刷新计时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._update_interval = int(1000 / (self._lines * self._speed))
        self._timer.setInterval(self._update_interval)
        
        # 初始状态
        self._is_spinning = False
        
        # 设置小部件属性
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 隐藏小部件直到需要显示
        self.hide()
        
        # 设置固定大小
        total_size = (self._radius + self._line_length) * 2
        self.setFixedSize(QSize(total_size, total_size))
    
    def _rotate(self):
        """更新旋转角度并重绘小部件"""
        self._current_counter += 1
        if self._current_counter >= self._lines:
            self._current_counter = 0
        self.update()
    
    def paintEvent(self, event):
        """绘制旋转器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        if not self._is_spinning:
            return
        
        painter.translate(self.width() / 2, self.height() / 2)
        
        # 计算每条线的角度
        angle = 360.0 / self._lines
        
        # 计算渐变透明度变化
        alpha_change = 1.0 / self._lines
        
        # 绘制每条线
        pen = QPen(self._color)
        pen.setWidth(self._line_width)
        
        for i in range(self._lines):
            # 减小远离当前绘制位置的线条的透明度
            rotation = int((self._current_counter + i) % self._lines)
            alpha = 1.0 - alpha_change * rotation
            
            # 设置透明度
            pen.setColor(QColor(self._color.red(), self._color.green(), 
                                self._color.blue(), int(alpha * 255)))
            painter.setPen(pen)
            
            # 绘制线段
            painter.drawLine(self._radius, 0, self._radius + self._line_length, 0)
            
            # 旋转到下一条线的位置
            painter.rotate(angle)
    
    def start(self):
        """开始旋转"""
        self._is_spinning = True
        self.show()
        
        if self._disable_parent_when_spinning and self.parentWidget():
            self.parentWidget().setEnabled(False)
        
        if not self._timer.isActive():
            self._timer.start()
            self._current_counter = 0
    
    def stop(self):
        """停止旋转"""
        self._is_spinning = False
        self.hide()
        
        if self._disable_parent_when_spinning and self.parentWidget():
            self.parentWidget().setEnabled(True)
        
        if self._timer.isActive():
            self._timer.stop()
    
    def is_spinning(self):
        """返回旋转状态"""
        return self._is_spinning
    
    def set_position(self, x, y):
        """设置旋转器的位置"""
        self.move(x, y)
    
    def position_next_to(self, widget):
        """将旋转器定位在控件旁边"""
        if widget and widget.isVisible():
            rect = widget.geometry()
            self.move(rect.right() + 5, rect.top() + (rect.height() - self.height()) // 2) 