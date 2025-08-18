"""
Simple CPU Stress Test Chart Widget

使用純 Qt 組件提供 CPU 壓力測試的簡單圖表功能
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QCheckBox, QPushButton, QLabel, QTextEdit, QSpinBox)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from datetime import datetime, timedelta
import csv
import os
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
        self.show_warning_line = True  # 控制警告線顯示
        self.temp_warning_threshold = 85.0  # 85°C 警告閾值
        
        # 設置 UI
        self._setup_ui()
        
        # 用於存儲系統記憶體信息
        self.total_ram_mb = 3891  # 預設值，會被動態更新
        
        # 表格日誌相關
        self.table_initialized = False
        
        # CSV 日誌相關
        self.csv_logging_enabled = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_path = None
        self.device_id = "unknown"  # 將從外部設置
        
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
        self.warning_line_checkbox = QCheckBox("Warning Line")
        self.warning_line_checkbox.setChecked(True)
        self.warning_line_checkbox.setStyleSheet("color: white;")
        self.warning_line_checkbox.toggled.connect(self._on_warning_line_toggled)
        
        # 警告溫度調整 spinbox
        self.warning_temp_spinbox = QSpinBox()
        self.warning_temp_spinbox.setMinimum(50)  # 最低50度
        self.warning_temp_spinbox.setMaximum(110)  # 最高110度
        self.warning_temp_spinbox.setSingleStep(5)  # 每次跳5度
        self.warning_temp_spinbox.setValue(85)  # 預設85度
        self.warning_temp_spinbox.setSuffix("°C")
        self.warning_temp_spinbox.setMaximumWidth(80)
        self.warning_temp_spinbox.setStyleSheet("color: white; background-color: #3C3C3C; border: 1px solid #555555;")
        self.warning_temp_spinbox.valueChanged.connect(self._on_warning_temp_changed)
        
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
        controls_layout.addWidget(self.warning_temp_spinbox)
        controls_layout.addStretch()
        controls_layout.addWidget(self.stats_label)
        controls_layout.addWidget(self.clear_button)
        
        # 信息顯示區域（Duration 和 Current Temperature）- 放在控制面板下方
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(20)
        
        # Duration Label
        self.duration_label = QLabel("Duration: 0 Day 00:00:00")
        self.duration_label.setStyleSheet("""
            QLabel {
                color: #00BFFF;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
                background-color: #2A2A2A;
                padding: 5px 10px;
                border: 1px solid #3C3C3C;
                border-radius: 3px;
            }
        """)
        
        # Current Temperature Label
        self.current_temp_label = QLabel("Current Temperature: --°C")
        self.current_temp_label.setStyleSheet("""
            QLabel {
                color: #00FF00;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
                background-color: #2A2A2A;
                padding: 5px 10px;
                border: 1px solid #3C3C3C;
                border-radius: 3px;
            }
        """)
        
        info_layout.addWidget(self.duration_label)
        info_layout.addWidget(self.current_temp_label)
        info_layout.addStretch()  # 將空白區域移到最右邊
        
        # 先添加控制面板和信息區域
        chart_layout.addLayout(controls_layout)
        chart_layout.addWidget(info_container)
        
        # 然後添加圖表區域
        self.chart_area = ChartPaintWidget()
        self.chart_area.setMinimumHeight(320)  # 增加圖表高度，配合滾動設計
        chart_layout.addWidget(self.chart_area)
        
        # 數據顯示區域
        data_container = QWidget()
        data_layout = QVBoxLayout(data_container)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(0)
        
        # 固定標題區域
        self.header_display = QLabel()
        self.header_display.setFixedHeight(40)
        self.header_display.setStyleSheet("""
            QLabel {
                background-color: #2A2A2A;
                color: #00BFFF;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #3C3C3C;
                border-bottom: 2px solid #00BFFF;
            }
        """)
        
        # 可滾動的數據區域
        self.data_display = QTextEdit()
        self.data_display.setMaximumHeight(120)
        self.data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #3C3C3C;
                border-top: none;
                padding: 5px;
            }
        """)
        self.data_display.setPlaceholderText("Stress test data will appear here...")
        
        data_layout.addWidget(self.header_display)
        data_layout.addWidget(self.data_display)
        chart_layout.addWidget(data_container)
        
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
            
            # 防止重複數據：檢查是否與最後一個數據點太接近
            if (hasattr(self, 'last_data_time') and self.last_data_time and 
                abs(elapsed_seconds - self.last_data_time) < 0.5):  # 0.5秒內的重複數據忽略
                logger.debug(f"Skipping duplicate data point: elapsed={elapsed_seconds:.1f}s, last={self.last_data_time:.1f}s")
                return
            
            # 記錄本次數據時間
            self.last_data_time = elapsed_seconds
            
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
            self._update_info_labels(cpu_temp, elapsed_seconds)
            
        except Exception as e:
            logger.error(f"Error adding CPU data point: {e}")
    
    def _update_info_labels(self, cpu_temp: float, elapsed_seconds: float):
        """更新信息標籤（Duration 和 Current Temperature）"""
        try:
            # 更新 Duration 標籤
            total_seconds = int(elapsed_seconds)
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            duration_text = f"Duration: {days} Day {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.duration_label.setText(duration_text)
            
            # 更新 Current Temperature 標籤，根據溫度設置不同顏色
            temp_text = f"Current Temperature: {cpu_temp:.1f}°C"
            self.current_temp_label.setText(temp_text)
            
            # 根據溫度動態調整標籤顏色
            if cpu_temp >= self.temp_warning_threshold:
                # 高溫警告 - 紅色
                temp_color = "#FF6666"
            elif cpu_temp >= 70:
                # 中等溫度 - 橙色
                temp_color = "#FFA500"
            else:
                # 正常溫度 - 綠色
                temp_color = "#00FF00"
            
            # 動態更新溫度標籤的樣式
            self.current_temp_label.setStyleSheet(f"""
                QLabel {{
                    color: {temp_color};
                    font-size: 13px;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', monospace;
                    background-color: #2A2A2A;
                    padding: 5px 10px;
                    border: 1px solid #3C3C3C;
                    border-radius: 3px;
                }}
            """)
            
        except Exception as e:
            logger.error(f"Error updating info labels: {e}")
    
    def _update_chart(self):
        """更新圖表顯示"""
        try:
            # 更新圖表繪製組件的數據
            self.chart_area.set_data(
                self.time_data, 
                self.temp_data,
                self.temp_warning_threshold,  # 警告閾值
                self.show_temp_line,  # 顯示溫度線
                self.show_warning_line  # 顯示警告線
            )
            
        except Exception as e:
            logger.error(f"Error updating chart: {e}")
    
    def _update_stats(self):
        """更新統計信息"""
        points_count = len(self.temp_data)
        if points_count > 0:
            avg_temp = sum(self.temp_data) / len(self.temp_data)
            max_temp = max(self.temp_data)
            min_temp = min(self.temp_data)
            
            stats_text = (f"Points: {points_count} | "
                         f"Avg: {avg_temp:.1f}°C | "
                         f"Max: {max_temp:.1f}°C | "
                         f"Min: {min_temp:.1f}°C")
        else:
            stats_text = "Points: 0"
        
        self.stats_label.setText(stats_text)
    
    def _initialize_table_header(self):
        """初始化表格標題"""
        if not self.table_initialized:
            # 清空數據區域
            self.data_display.clear()
            
            # 設置固定標題（使用精確的字符寬度確保對齊）
            header_text = f"{'Timestamp':<10} {'Duration':<10} {'CPU Loading':<12} {'RAM Loading':<15} {'Temperature':<12}"
            separator = "─" * len(header_text)
            
            # 設置標題顯示
            self.header_display.setText(f"{header_text}\n{separator}")
            
            self.table_initialized = True
    
    def _update_data_display(self, cpu_temp: float, cpu_load: float, elapsed_time: float, ram_stress_enabled: bool = False, ram_stress_mb: int = 0):
        """更新數據顯示（表格格式）"""
        try:
            # 確保表格標題已初始化
            self._initialize_table_header()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 計算 RAM 使用百分比（基於設定值）
            if ram_stress_enabled and ram_stress_mb > 0:
                current_ram_percent = (ram_stress_mb / self.total_ram_mb) * 100 if self.total_ram_mb > 0 else 0
                ram_display = f"{current_ram_percent:5.1f}%({ram_stress_mb}MB)"
            else:
                ram_display = "0.0%(0MB)"
            
            # 根據溫度決定顏色格式
            if cpu_temp >= self.temp_warning_threshold:
                temp_color = "#ff6600"  # 橙色（85°C以上）
                temp_weight = "bold"
            else:
                temp_color = "#00ff00"  # 綠色
                temp_weight = "normal"
            
            # 格式化各欄位（精確對齊標題寬度）
            timestamp_text = f"{timestamp:<10}"
            duration_text = f"{elapsed_time:6.1f}s"
            duration_formatted = f"{duration_text:<10}"
            cpu_text = f"{cpu_load:5.1f}%"
            cpu_formatted = f"{cpu_text:<12}"
            ram_formatted = f"{ram_display:<15}"
            
            # 格式化溫度（帶顏色）
            temp_display = f"{cpu_temp:.0f}°C"
            temp_html = f"<span style='color: {temp_color}; font-weight: {temp_weight};'>{temp_display}</span>"
            
            # 創建完整的數據行（純文本部分 + HTML 溫度部分）
            data_row = f"<span style='font-family: Consolas, Monaco, monospace; white-space: pre;'>{timestamp_text} {duration_formatted} {cpu_formatted} {ram_formatted} </span>{temp_html}"
            
            # 添加到文本區域
            self.data_display.append(data_row)
            
            # 保持在合理的行數內（簡化邏輯，避免重複）
            # 使用更簡單的方法：直接控制 QTextEdit 的行數
            document = self.data_display.document()
            if document.blockCount() > 21:  # 21行（包括可能的空行）
                # 移除第一行數據
                cursor = self.data_display.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 刪除換行符
            
            # 自動滾動到底部
            from PySide6.QtGui import QTextCursor
            cursor = self.data_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.data_display.setTextCursor(cursor)
            
            # 如果啟用了 CSV 日誌，將數據寫入 CSV 檔案
            self._write_to_csv(timestamp, elapsed_time, cpu_load, ram_stress_enabled, ram_stress_mb, cpu_temp)
            
        except Exception as e:
            logger.error(f"Error updating data display: {e}")
    
    def _write_to_csv(self, timestamp: str, elapsed_time: float, cpu_load: float, 
                      ram_stress_enabled: bool, ram_stress_mb: int, cpu_temp: float):
        """將數據寫入 CSV 檔案"""
        if not self.csv_logging_enabled or not self.csv_writer:
            return
            
        try:
            # 計算 RAM 使用百分比
            if ram_stress_enabled and ram_stress_mb > 0:
                ram_percent = (ram_stress_mb / self.total_ram_mb) * 100 if self.total_ram_mb > 0 else 0
            else:
                ram_percent = 0.0
                ram_stress_mb = 0
            
            # 準備 CSV 行數據
            csv_row = [
                timestamp,              # Timestamp
                f"{elapsed_time:.1f}",  # Duration (s)
                f"{cpu_load:.1f}",      # CPU Loading (%)
                f"{ram_percent:.1f}",   # RAM Loading (%)
                ram_stress_mb,          # RAM Loading (MB)
                f"{cpu_temp:.1f}"       # Temperature (°C)
            ]
            
            # 寫入 CSV
            self.csv_writer.writerow(csv_row)
            self.csv_file.flush()  # 確保數據立即寫入檔案
            
        except Exception as e:
            logger.error(f"Error writing to CSV: {e}")
    
    @Slot(bool)
    def _on_temp_line_toggled(self, checked: bool):
        """溫度線顯示切換"""
        self.show_temp_line = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_warning_line_toggled(self, checked: bool):
        """警告線顯示切換"""
        self.show_warning_line = checked
        self._update_chart()
    
    @Slot(int)
    def _on_warning_temp_changed(self, value: int):
        """警告溫度值變更"""
        self.temp_warning_threshold = float(value)
        self._update_chart()
        logger.debug(f"Warning temperature threshold changed to: {value}°C")
    
    def clear_data(self):
        """清除所有數據"""
        self.temp_data.clear()
        self.time_data.clear()
        self.start_time = None
        self.last_data_time = None
        
        # 清除顯示
        self.chart_area.clear_data()
        self.data_display.clear()
        self.header_display.clear()
        
        # 重置表格初始化標誌
        self.table_initialized = False
        
        # 重置統計信息
        self._update_stats()
        
        # 重置信息標籤
        self.duration_label.setText("Duration: 0 Day 00:00:00")
        self.current_temp_label.setText("Current Temperature: --°C")
        
        # 如果 CSV 日誌正在運行，停止它
        if self.csv_logging_enabled:
            self._stop_csv_logging()
        
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
    
    def set_device_id(self, device_id: str):
        """設置設備 ID，用於 CSV 檔案命名"""
        self.device_id = device_id
        logger.debug(f"Device ID set to: {device_id}")
    
    def start_csv_logging(self):
        """開始 CSV 日誌記錄（公共方法）"""
        if not self.csv_logging_enabled:
            self._start_csv_logging()
    
    def stop_csv_logging(self):
        """停止 CSV 日誌記錄（公共方法）"""
        if self.csv_logging_enabled:
            self._stop_csv_logging()
    
    def _start_csv_logging(self):
        """開始 CSV 日誌記錄"""
        try:
            # 生成時間戳檔名，參照 battery_monitor 的命名邏輯
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.csv_file_path = f"stress_test_{self.device_id}_{timestamp}.csv"
            
            # 開啟 CSV 檔案並創建寫入器
            self.csv_file = open(self.csv_file_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # 寫入 CSV 標題
            header = [
                'Timestamp',
                'Duration (s)',
                'CPU Loading (%)', 
                'RAM Loading (%)',
                'RAM Loading (MB)',
                'Temperature (°C)'
            ]
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            
            self.csv_logging_enabled = True
            logger.info(f"CSV logging started: {self.csv_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to start CSV logging: {str(e)}")
            self.csv_logging_enabled = False
            self._close_csv_logging()
    
    def _stop_csv_logging(self):
        """停止 CSV 日誌記錄"""
        self.csv_logging_enabled = False
        self._close_csv_logging()
        logger.info("CSV logging stopped")
    
    def _close_csv_logging(self):
        """關閉 CSV 檔案並清理"""
        try:
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
                
            if self.csv_file_path:
                logger.info(f"CSV file saved: {self.csv_file_path}")
                
        except Exception as e:
            logger.error(f"Error closing CSV file: {str(e)}")
        finally:
            self.csv_file = None
            self.csv_writer = None
    
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