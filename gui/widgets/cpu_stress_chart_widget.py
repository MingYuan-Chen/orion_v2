"""
CPU Stress Test Chart Widget

提供 CPU 壓力測試的即時監控圖表功能
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QCheckBox, QPushButton, QLabel)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QPen, QColor
from datetime import datetime, timedelta
from util.logger import logger

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available, using simple placeholder chart")

class CpuStressChartWidget(QWidget):
    """
    CPU 壓力測試圖表組件
    顯示 CPU 負載即時監控曲線
    """
    
    # 信號定義
    chart_cleared = Signal()
    data_exported = Signal(str)  # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 數據存儲
        self.cpu_data = []
        self.time_data = []
        self.start_time = None
        self.max_data_points = 1000  # 最多保存 1000 個數據點
        
        # 圖表顯示控制
        self.show_cpu_load = True
        self.show_target_load = True
        
        # 設置 UI
        self._setup_ui()
        self._setup_chart()
        
        logger.debug("CPU stress chart widget initialized")
    
    def _setup_ui(self):
        """設置 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 圖表組
        chart_group = QGroupBox("CPU Loading Chart")
        chart_layout = QVBoxLayout(chart_group)
        
        # 控制面板
        controls_layout = QHBoxLayout()
        
        # 顯示控制復選框
        self.cpu_load_checkbox = QCheckBox("CPU Load")
        self.cpu_load_checkbox.setChecked(True)
        self.cpu_load_checkbox.toggled.connect(self._on_cpu_load_toggled)
        
        self.target_load_checkbox = QCheckBox("Target Load")
        self.target_load_checkbox.setChecked(True)
        self.target_load_checkbox.toggled.connect(self._on_target_load_toggled)
        
        # 統計信息標籤
        self.stats_label = QLabel("Points: 0")
        self.stats_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        # 清除按鈕
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMaximumWidth(60)
        self.clear_button.clicked.connect(self.clear_data)
        
        # 保存按鈕
        self.save_button = QPushButton("Save Chart")
        self.save_button.setMaximumWidth(80)
        self.save_button.clicked.connect(self.save_chart_with_dialog)
        
        # 添加控件到控制面板
        controls_layout.addWidget(self.cpu_load_checkbox)
        controls_layout.addWidget(self.target_load_checkbox)
        controls_layout.addStretch()
        controls_layout.addWidget(self.stats_label)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addWidget(self.save_button)
        
        chart_layout.addLayout(controls_layout)
        
        # 圖表占位符
        self.chart_placeholder = QWidget()
        self.chart_placeholder.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_placeholder)
        
        layout.addWidget(chart_group)
    
    def _setup_chart(self):
        """設置圖表"""
        # 創建圖表容器布局
        chart_layout = QVBoxLayout(self.chart_placeholder)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            # 使用 matplotlib 創建圖表
            self.figure = Figure(figsize=(10, 4), facecolor='#2D2D30')
            self.canvas = FigureCanvas(self.figure)
            self.axes = self.figure.add_subplot(111, facecolor='#2D2D30')
            
            # 設置圖表樣式
            self.axes.set_xlabel('Time (seconds)', color='white')
            self.axes.set_ylabel('CPU Load (%)', color='white')
            self.axes.set_ylim(0, 100)
            self.axes.grid(True, alpha=0.3, color='white')
            
            # 設置坐標軸顏色
            self.axes.tick_params(colors='white')
            self.axes.spines['bottom'].set_color('white')
            self.axes.spines['left'].set_color('white')
            self.axes.spines['top'].set_color('white')
            self.axes.spines['right'].set_color('white')
            
            # 初始化線條
            self.cpu_load_line, = self.axes.plot([], [], 'g-', linewidth=2, label='CPU Load')
            self.target_load_line, = self.axes.plot([], [], 'orange', linestyle='--', linewidth=2, label='Target Load')
            
            # 添加圖例
            self.axes.legend(loc='upper right', facecolor='#2D2D30', edgecolor='white', labelcolor='white')
            
            # 調整布局
            self.figure.tight_layout()
            
            chart_layout.addWidget(self.canvas)
            
        else:
            # 使用簡單的占位符
            placeholder_label = QLabel("Chart requires matplotlib\nPlease install: pip install matplotlib")
            placeholder_label.setAlignment(Qt.AlignCenter)
            placeholder_label.setStyleSheet("color: white; background-color: #2D2D30; border: 1px solid #555555;")
            placeholder_label.setMinimumHeight(300)
            chart_layout.addWidget(placeholder_label)
        
        logger.debug("CPU stress chart setup completed")
    
    def add_data_point(self, cpu_load: float, target_load: float = None):
        """
        添加數據點
        
        Args:
            cpu_load: 實際 CPU 負載百分比
            target_load: 目標 CPU 負載百分比
        """
        try:
            current_time = datetime.now()
            
            # 設置開始時間
            if self.start_time is None:
                self.start_time = current_time
            
            # 計算相對時間（秒）
            elapsed_seconds = (current_time - self.start_time).total_seconds()
            
            # 添加數據
            self.time_data.append(elapsed_seconds)
            self.cpu_data.append(cpu_load)
            
            # 保持數據點數量在限制內
            if len(self.time_data) > self.max_data_points:
                self.time_data.pop(0)
                self.cpu_data.pop(0)
            
            # 更新圖表
            self._update_chart(target_load)
            
            # 更新統計信息
            self._update_stats()
            
        except Exception as e:
            logger.error(f"Error adding CPU data point: {e}")
    
    def _update_chart(self, target_load: float = None):
        """更新圖表顯示"""
        try:
            if not MATPLOTLIB_AVAILABLE or not self.time_data or not self.cpu_data:
                return
            
            # 更新 CPU 負載曲線
            if self.show_cpu_load:
                self.cpu_load_line.set_data(self.time_data, self.cpu_data)
            else:
                self.cpu_load_line.set_data([], [])
            
            # 更新目標負載曲線
            if self.show_target_load and target_load is not None:
                target_data = [target_load] * len(self.time_data)
                self.target_load_line.set_data(self.time_data, target_data)
            else:
                self.target_load_line.set_data([], [])
            
            # 自動調整 X 軸範圍
            if len(self.time_data) > 1:
                x_min = min(self.time_data)
                x_max = max(self.time_data)
                x_range = x_max - x_min
                padding = max(x_range * 0.05, 1)  # 至少 1 秒的 padding
                self.axes.set_xlim(x_min - padding, x_max + padding)
            
            # 刷新畫布
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating CPU chart: {e}")
    
    def _update_stats(self):
        """更新統計信息"""
        points_count = len(self.cpu_data)
        if points_count > 0:
            current_load = self.cpu_data[-1]
            avg_load = sum(self.cpu_data) / len(self.cpu_data)
            max_load = max(self.cpu_data)
            min_load = min(self.cpu_data)
            
            stats_text = (f"Points: {points_count} | "
                         f"Current: {current_load:.1f}% | "
                         f"Avg: {avg_load:.1f}% | "
                         f"Max: {max_load:.1f}% | "
                         f"Min: {min_load:.1f}%")
        else:
            stats_text = "Points: 0"
        
        self.stats_label.setText(stats_text)
    
    @Slot(bool)
    def _on_cpu_load_toggled(self, checked: bool):
        """CPU 負載顯示切換"""
        self.show_cpu_load = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_target_load_toggled(self, checked: bool):
        """目標負載顯示切換"""
        self.show_target_load = checked
        self._update_chart()
    
    def clear_data(self):
        """清除所有數據"""
        self.cpu_data.clear()
        self.time_data.clear()
        self.start_time = None
        
        # 清除圖表
        if MATPLOTLIB_AVAILABLE:
            self.cpu_load_line.set_data([], [])
            self.target_load_line.set_data([], [])
            self.canvas.draw()
        
        # 重置統計信息
        self._update_stats()
        
        # 發出清除信號
        self.chart_cleared.emit()
        
        logger.info("CPU stress chart data cleared")
    
    def get_chart_data(self) -> Dict[str, Any]:
        """
        取得圖表數據
        
        Returns:
            包含時間和 CPU 負載數據的字典
        """
        return {
            'time_data': self.time_data.copy(),
            'cpu_data': self.cpu_data.copy(),
            'start_time': self.start_time,
            'data_count': len(self.cpu_data)
        }
    
    def load_chart_data(self, data: Dict[str, Any]):
        """
        載入圖表數據
        
        Args:
            data: 包含時間和 CPU 負載數據的字典
        """
        try:
            self.time_data = data.get('time_data', [])
            self.cpu_data = data.get('cpu_data', [])
            self.start_time = data.get('start_time')
            
            self._update_chart()
            self._update_stats()
            
            logger.info(f"Loaded {len(self.cpu_data)} CPU data points")
            
        except Exception as e:
            logger.error(f"Error loading CPU chart data: {e}")
    
    def save_chart_with_dialog(self):
        """顯示保存對話框並保存圖表"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save CPU Stress Chart",
                f"cpu_stress_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG Files (*.png);;All Files (*)"
            )
            
            if file_path:
                self.save_chart(file_path)
                
        except Exception as e:
            logger.error(f"Error showing save dialog: {e}")
    
    def save_chart(self, file_path: str):
        """
        保存圖表為圖片
        
        Args:
            file_path: 保存路徑
        """
        try:
            if MATPLOTLIB_AVAILABLE:
                # 使用 matplotlib 保存圖表
                self.figure.savefig(file_path, facecolor='#2D2D30', dpi=150, bbox_inches='tight')
                self.data_exported.emit(file_path)
                logger.info(f"CPU stress chart saved to: {file_path}")
            else:
                logger.warning("Cannot save chart: matplotlib not available")
            
        except Exception as e:
            logger.error(f"Error saving CPU chart: {e}")
    
    def set_chart_title(self, title: str):
        """設置圖表標題"""
        if MATPLOTLIB_AVAILABLE:
            self.axes.set_title(title, color='white', fontsize=12)
            self.canvas.draw()
    
    def get_statistics(self) -> Dict[str, float]:
        """
        取得統計數據
        
        Returns:
            統計數據字典
        """
        if not self.cpu_data:
            return {
                'count': 0,
                'current': 0,
                'average': 0,
                'maximum': 0,
                'minimum': 0,
                'duration': 0
            }
        
        duration = self.time_data[-1] - self.time_data[0] if len(self.time_data) > 1 else 0
        
        return {
            'count': len(self.cpu_data),
            'current': self.cpu_data[-1],
            'average': sum(self.cpu_data) / len(self.cpu_data),
            'maximum': max(self.cpu_data),
            'minimum': min(self.cpu_data),
            'duration': duration
        }
    
    def cleanup(self):
        """清理資源"""
        self.clear_data()
        logger.debug("CPU stress chart widget cleaned up")


if __name__ == "__main__":
    """測試 CPU 壓力測試圖表組件"""
    import sys
    from PySide6.QtWidgets import QApplication
    import random
    import time
    
    app = QApplication(sys.argv)
    
    widget = CpuStressChartWidget()
    widget.show()
    
    # 模擬數據
    def add_test_data():
        for i in range(100):
            cpu_load = 50 + 30 * random.random()  # 50-80% 隨機負載
            widget.add_data_point(cpu_load, 75)  # 目標 75%
            app.processEvents()
            time.sleep(0.1)
    
    # 添加測試數據
    from PySide6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(lambda: widget.add_data_point(
        50 + 30 * random.random(), 75))
    timer.start(500)  # 每 0.5 秒添加一個數據點
    
    sys.exit(app.exec())