"""
Simple CPU Stress Test Chart Widget

使用純 Qt 組件提供 CPU 壓力測試的簡單圖表功能
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QCheckBox, QPushButton, QLabel, QTextEdit)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from datetime import datetime, timedelta
from util.logger import logger

class SimpleCpuChartWidget(QWidget):
    """
    簡單的 CPU 溫度監控圖表組件
    使用 Qt 原生繪圖功能顯示 CPU 溫度監控
    """
    
    # 信號定義
    chart_cleared = Signal()
    data_exported = Signal(str)  # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 數據存儲
        self.temp_data = []
        self.time_data = []
        self.start_time = None
        self.max_data_points = 100  # 最多保存 100 個數據點
        
        # 圖表顯示控制
        self.show_temp_line = True
        self.temp_warning_threshold = 85.0  # 85°C 警告閾值
        
        # 設置 UI
        self._setup_ui()
        
        # 用於存儲系統記憶體信息
        self.total_ram_mb = 3891  # 預設值，會被動態更新
        
        logger.debug("Simple CPU chart widget initialized")
    
    def _setup_ui(self):
        """設置 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 圖表組
        chart_group = QGroupBox("CPU Temperature Monitor")
        chart_layout = QVBoxLayout(chart_group)
        
        # 控制面板
        controls_layout = QHBoxLayout()
        
        # 顯示控制復選框
        self.temp_line_checkbox = QCheckBox("Temperature")
        self.temp_line_checkbox.setChecked(True)
        self.temp_line_checkbox.setStyleSheet("color: white;")
        self.temp_line_checkbox.toggled.connect(self._on_temp_line_toggled)
        
        # 溫度警告線顯示
        self.warning_line_checkbox = QCheckBox("Warning Line (85°C)")
        self.warning_line_checkbox.setChecked(True)
        self.warning_line_checkbox.setStyleSheet("color: white;")
        self.warning_line_checkbox.toggled.connect(self._on_warning_line_toggled)
        
        # 統計信息標籤
        self.stats_label = QLabel("Points: 0")
        self.stats_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        # 清除按鈕
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMaximumWidth(60)
        self.clear_button.clicked.connect(self.clear_data)
        
        # 添加控件到控制面板
        controls_layout.addWidget(self.temp_line_checkbox)
        controls_layout.addWidget(self.warning_line_checkbox)
        controls_layout.addStretch()
        controls_layout.addWidget(self.stats_label)
        controls_layout.addWidget(self.clear_button)
        
        chart_layout.addLayout(controls_layout)
        
        # 圖表區域
        self.chart_area = ChartPaintWidget()
        self.chart_area.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_area)
        
        # 數據顯示區域
        self.data_display = QTextEdit()
        self.data_display.setMaximumHeight(100)
        self.data_display.setStyleSheet("background-color: #1E1E1E; color: white; font-family: monospace;")
        self.data_display.setPlaceholderText("CPU load data will appear here...")
        chart_layout.addWidget(self.data_display)
        
        layout.addWidget(chart_group)
    
    def add_data_point(self, cpu_temp: float, cpu_load: float = 0, ram_stress_enabled: bool = False, ram_stress_mb: int = 0):
        """
        添加數據點
        
        Args:
            cpu_temp: CPU 溫度（攝氏度）
            cpu_load: 實際 CPU 負載百分比（用於日誌）
            ram_stress_enabled: 是否啟用 RAM 壓力測試
            ram_stress_mb: RAM 壓力測試的 MB 數
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
            self.temp_data.append(cpu_temp)
            
            # 保持數據點數量在限制內
            if len(self.time_data) > self.max_data_points:
                self.time_data.pop(0)
                self.temp_data.pop(0)
            
            # 更新圖表和顯示
            self._update_chart()
            self._update_stats()
            self._update_data_display(cpu_temp, cpu_load, elapsed_seconds, ram_stress_enabled, ram_stress_mb)
            
        except Exception as e:
            logger.error(f"Error adding CPU data point: {e}")
    
    def _update_chart(self):
        """更新圖表顯示"""
        try:
            # 更新圖表繪製組件的數據
            self.chart_area.set_data(
                self.time_data, 
                self.temp_data,
                self.temp_warning_threshold,  # 警告閾值
                self.show_temp_line,  # 顯示溫度線
                True  # 顯示警告線
            )
            
        except Exception as e:
            logger.error(f"Error updating chart: {e}")
    
    def _update_stats(self):
        """更新統計信息"""
        points_count = len(self.temp_data)
        if points_count > 0:
            current_temp = self.temp_data[-1]
            avg_temp = sum(self.temp_data) / len(self.temp_data)
            max_temp = max(self.temp_data)
            min_temp = min(self.temp_data)
            
            stats_text = (f"Points: {points_count} | "
                         f"Current: {current_temp:.1f}°C | "
                         f"Avg: {avg_temp:.1f}°C | "
                         f"Max: {max_temp:.1f}°C | "
                         f"Min: {min_temp:.1f}°C")
        else:
            stats_text = "Points: 0"
        
        self.stats_label.setText(stats_text)
    
    def _update_data_display(self, cpu_temp: float, cpu_load: float, elapsed_time: float, ram_stress_enabled: bool = False, ram_stress_mb: int = 0):
        """更新數據顯示"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 計算 RAM 使用百分比（基於設定值）
            if ram_stress_enabled and ram_stress_mb > 0:
                # 使用目標 RAM 壓力值作為顯示值，不添加隨機變化
                # 使用動態獲取的系統總記憶體
                current_ram_percent = (ram_stress_mb / self.total_ram_mb) * 100 if self.total_ram_mb > 0 else 0
                
                # 根據溫度決定顏色格式
                if cpu_temp >= self.temp_warning_threshold:
                    temp_color = "color: #ff6600; font-weight: bold;"  # 橙色粗體（85°C以上）
                else:
                    temp_color = "color: #00ff00;"  # 綠色
                
                data_line = f"[{timestamp}] {elapsed_time:6.1f}s - CPU: {cpu_load:5.1f}% - RAM: {current_ram_percent:5.1f}% ({ram_stress_mb} MB) - Temp: {cpu_temp:.0f}°C"
            else:
                # 只有 CPU 測試
                # 根據溫度決定顏色格式
                if cpu_temp >= self.temp_warning_threshold:
                    temp_color = "color: #ff6600; font-weight: bold;"  # 橙色粗體（85°C以上）
                else:
                    temp_color = "color: #00ff00;"  # 綠色
                
                data_line = f"[{timestamp}] {elapsed_time:6.1f}s - CPU: {cpu_load:5.1f}% - RAM: 0.0% (0 MB) - Temp: {cpu_temp:.0f}°C"
            
            # 添加到文本區域
            self.data_display.append(data_line)
            
            # 保持在合理的行數內
            lines = self.data_display.toPlainText().split('\n')
            if len(lines) > 20:
                self.data_display.setPlainText('\n'.join(lines[-20:]))
            
            # 自動滾動到底部
            from PySide6.QtGui import QTextCursor
            cursor = self.data_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.data_display.setTextCursor(cursor)
            
        except Exception as e:
            logger.error(f"Error updating data display: {e}")
    
    @Slot(bool)
    def _on_temp_line_toggled(self, checked: bool):
        """溫度線顯示切換"""
        self.show_temp_line = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_warning_line_toggled(self, checked: bool):
        """警告線顯示切換"""
        # 這個功能可以後續實現
        pass
    
    def clear_data(self):
        """清除所有數據"""
        self.temp_data.clear()
        self.time_data.clear()
        self.start_time = None
        
        # 清除顯示
        self.chart_area.clear_data()
        self.data_display.clear()
        
        # 重置統計信息
        self._update_stats()
        
        # 發出清除信號
        self.chart_cleared.emit()
        
        logger.info("CPU chart data cleared")
    
    def set_total_ram_mb(self, total_ram_mb: int):
        """設置系統總記憶體大小（MB）"""
        self.total_ram_mb = total_ram_mb
        logger.debug(f"Updated total RAM to {total_ram_mb} MB")
    
    def set_chart_title(self, title: str):
        """設置圖表標題"""
        self.chart_area.set_title(title)
    
    def get_statistics(self) -> Dict[str, float]:
        """
        取得統計數據
        
        Returns:
            統計數據字典
        """
        if not self.temp_data:
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
            'count': len(self.temp_data),
            'current': self.temp_data[-1],
            'average': sum(self.temp_data) / len(self.temp_data),
            'maximum': max(self.temp_data),
            'minimum': min(self.temp_data),
            'duration': duration
        }


class ChartPaintWidget(QWidget):
    """簡單的圖表繪製組件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_data = []
        self.temp_data = []
        self.temp_warning_threshold = 85.0
        self.show_temp_line = True
        self.show_warning_line = True
        self.title = ""
        
        # 設置背景色
        self.setStyleSheet("background-color: #2D2D30; border: 1px solid #555555;")
    
    def set_data(self, time_data, temp_data, warning_threshold=None, show_temp=True, show_warning=True):
        """設置圖表數據"""
        self.time_data = time_data.copy() if time_data else []
        self.temp_data = temp_data.copy() if temp_data else []
        self.temp_warning_threshold = warning_threshold if warning_threshold is not None else 85.0
        self.show_temp_line = show_temp
        self.show_warning_line = show_warning
        self.update()  # 觸發重繪
    
    def clear_data(self):
        """清除圖表數據"""
        self.time_data.clear()
        self.temp_data.clear()
        self.update()
    
    def set_title(self, title: str):
        """設置圖表標題"""
        self.title = title
        self.update()
    
    def paintEvent(self, event):
        """繪製圖表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 獲取繪製區域
        rect = self.rect()
        margin = 40
        chart_rect = rect.adjusted(margin, margin, -margin, -margin)
        
        # 繪製背景
        painter.fillRect(rect, QColor('#2D2D30'))
        
        # 繪製標題
        if self.title:
            painter.setPen(QPen(QColor('white')))
            title_font = QFont()
            title_font.setPointSize(12)
            title_font.setBold(True)
            painter.setFont(title_font)
            title_rect = rect.adjusted(0, 0, 0, -rect.height() + 30)
            painter.drawText(title_rect, Qt.AlignCenter, self.title)
        
        # 繪製坐標軸
        painter.setPen(QPen(QColor('white'), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())  # X 軸
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())      # Y 軸
        
        # 繪製網格和標籤
        painter.setPen(QPen(QColor('gray'), 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Y 軸標籤 (0-100%)
        for i in range(0, 101, 20):
            y = chart_rect.bottom() - (i / 100.0) * chart_rect.height()
            painter.drawLine(chart_rect.left() - 5, y, chart_rect.left(), y)
            painter.drawText(chart_rect.left() - 35, y - 5, 30, 10, Qt.AlignRight, f"{i}%")
            
            # 網格線
            if i > 0:
                painter.setPen(QPen(QColor('gray'), 1, Qt.DotLine))
                painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
                painter.setPen(QPen(QColor('gray'), 1))
        
        # 如果有數據，繪製數據線
        if len(self.time_data) > 1 and len(self.temp_data) > 1:
            # 計算縮放因子
            time_range = max(self.time_data) - min(self.time_data)
            if time_range > 0:
                x_scale = chart_rect.width() / time_range
                y_scale = chart_rect.height() / 100.0  # 假設最大溫度 100°C
                
                # 繪製溫度警告線
                if self.show_warning_line:
                    painter.setPen(QPen(QColor('orange'), 2, Qt.DashLine))
                    warning_y = chart_rect.bottom() - self.temp_warning_threshold * y_scale
                    painter.drawLine(chart_rect.left(), warning_y, chart_rect.right(), warning_y)
                
                # 繪製溫度線
                if self.show_temp_line:
                    painter.setPen(QPen(QColor('green'), 2))
                    
                    for i in range(1, len(self.time_data)):
                        x1 = chart_rect.left() + (self.time_data[i-1] - min(self.time_data)) * x_scale
                        y1 = chart_rect.bottom() - self.temp_data[i-1] * y_scale
                        x2 = chart_rect.left() + (self.time_data[i] - min(self.time_data)) * x_scale
                        y2 = chart_rect.bottom() - self.temp_data[i] * y_scale
                        
                        painter.drawLine(x1, y1, x2, y2)
        
        # 繪製圖例
        if self.show_temp_line:
            legend_x = chart_rect.right() - 150
            legend_y = chart_rect.top() + 10
            
            if self.show_temp_line:
                painter.setPen(QPen(QColor('green'), 2))
                painter.drawLine(legend_x, legend_y, legend_x + 20, legend_y)
                painter.setPen(QPen(QColor('white')))
                painter.drawText(legend_x + 25, legend_y + 5, "Temperature")
                legend_y += 20

        
        painter.end()


if __name__ == "__main__":
    """測試簡單圖表組件"""
    import sys
    from PySide6.QtWidgets import QApplication
    import random
    import time
    
    app = QApplication(sys.argv)
    
    widget = SimpleCpuChartWidget()
    widget.show()
    widget.resize(800, 500)
    widget.set_chart_title("CPU Stress Test - Target: 75%")
    
    # 模擬數據
    from PySide6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(lambda: widget.add_data_point(
        50 + 30 * random.random(), 75))
    timer.start(1000)  # 每秒添加一個數據點
    
    sys.exit(app.exec())