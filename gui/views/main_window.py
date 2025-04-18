from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger


class MainWindowController(QObject):
    """
    控制器類用於管理設備監控主窗口
    每個設備會創建一個獨立的實例
    """
    # 添加窗口關閉信號
    window_closed = Signal(str)  # 發送設備ID
    
    def __init__(self, device_id, view_model):
        """
        初始化主窗口控制器
        
        Args:
            device_id: 設備ID
            view_model: DeviceManagerViewModel 實例
        """
        # 調用 QObject 初始化
        super().__init__()
        
        # 保存設備ID和視圖模型
        self.device_id = device_id
        self.view_model = view_model
        
        # 載入UI
        self.window = QUiLoader().load("gui/ui/main_window.ui")
        
        # 設置窗口標題
        self.window.setWindowTitle(f"System Monitoring - Device {device_id}")
        
        # 初始化表格
        self._init_tables()
        
        # 連接信號和槽
        self._connect_signals()
        
        # 設置自動更新計時器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard)
        self.update_timer.start(5000)  # 每5秒更新一次
        
        # 初始載入設備數據
        self._update_dashboard()
        
        # 安裝事件過濾器來捕獲窗口關閉事件
        self.window.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """過濾窗口事件以捕獲關閉事件"""
        if obj is self.window and event.type() == QEvent.Close:
            logger.info(f"Main window for device {self.device_id} is closing")
            # 停止更新計時器
            self.update_timer.stop()
            # 發出窗口關閉信號
            self.window_closed.emit(self.device_id)
        return super().eventFilter(obj, event)
    
    def _init_tables(self):
        """初始化表格設置"""
        # 配置硬件表格
        hw_table = self.window.tableWidget_hw
        hw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 配置診斷表格
        diag_table = self.window.tableWidget_diagnostic
        diag_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加一些示例數據
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        """添加示例數據到表格"""
        # 硬件表格示例數據
        hw_table = self.window.tableWidget_hw
        hw_table.setRowCount(4)
        
        components = [
            ("CPU", "NXP i.MX6 Quad", "CPU-2023-0123", "Normal"),
            ("Memory", "DDR4-8GB", "MEM-2023-9876", "Normal"),
            ("Storage", "eMMC 128GB", "STO-2023-4567", "Normal"),
            ("Battery", "MD-BAT", "240500734", "Normal")
        ]
        
        for row, (comp, part, serial, status) in enumerate(components):
            hw_table.setItem(row, 0, QTableWidgetItem(comp))
            hw_table.setItem(row, 1, QTableWidgetItem(part))
            hw_table.setItem(row, 2, QTableWidgetItem(serial))
            hw_table.setItem(row, 3, QTableWidgetItem(status))
        
        # 診斷表格示例數據
        diag_table = self.window.tableWidget_diagnostic
        diag_table.setRowCount(3)
        
        tests = [
            ("System Boot Test", "Passed", "00:01:23"),
            ("Memory Test", "Passed", "00:03:45"),
            ("Storage Test", "Passed", "00:02:12")
        ]
        
        for row, (test, status, time) in enumerate(tests):
            diag_table.setItem(row, 0, QTableWidgetItem(test))
            diag_table.setItem(row, 1, QTableWidgetItem(status))
            diag_table.setItem(row, 2, QTableWidgetItem(time))
    
    def _connect_signals(self):
        """連接UI信號和槽"""
        # 連接按鈕點擊事件
        self.window.pushButton_detect_hw.clicked.connect(self._on_detect_hardware)
        self.window.pushButton_save_config.clicked.connect(self._on_save_config)
        self.window.pushButton_run_tests.clicked.connect(self._on_run_tests)
        self.window.pushButton_export_report.clicked.connect(self._on_export_report)
    
    def _update_dashboard(self):
        """更新儀表板信息"""
        # 更新最後更新時間
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time}")
        
        # 在實際應用中，您需要從設備獲取真實數據
        # 這裡僅作為示例，顯示一些靜態數據
        
        # 更新基本系統信息
        self.window.value_model_name.setText(f"Device Model {self.device_id}")
        self.window.value_serial_number.setText(f"SN-{self.device_id}-2023")
        
        # 更新電池信息
        battery_level = 78  # 這應該從設備獲取
        self.window.progressBar_charge.setValue(battery_level)
        self.window.value_charge.setText(f"{battery_level}%")
    
    def _on_detect_hardware(self):
        """檢測硬件按鈕點擊事件"""
        logger.info(f"Detecting hardware for device: {self.device_id}")
        # 實際應用中，您應該發送命令給設備以獲取硬件信息
        # 然後更新表格
        
        # 示例：假設我們發送命令並獲得響應
        self.view_model.send_command(self.device_id, "get_hardware_info")
    
    def _on_save_config(self):
        """保存配置按鈕點擊事件"""
        logger.info(f"Saving configuration for device: {self.device_id}")
        # 實現保存配置的邏輯
    
    def _on_run_tests(self):
        """運行測試按鈕點擊事件"""
        logger.info(f"Running diagnostic tests for device: {self.device_id}")
        # 實現運行診斷測試的邏輯
    
    def _on_export_report(self):
        """導出報告按鈕點擊事件"""
        logger.info(f"Exporting diagnostic report for device: {self.device_id}")
        # 實現導出診斷報告的邏輯
    
    def show(self):
        """顯示窗口"""
        self.window.show()
    
    def close(self):
        """關閉窗口並釋放資源"""
        self.update_timer.stop()
        self.window.close()


if __name__ == "__main__":
    # 測試代碼
    import sys
    from PySide6.QtWidgets import QApplication
    from gui.view_models.device_manager_view_model import DeviceManagerViewModel
    
    app = QApplication(sys.argv)
    view_model = DeviceManagerViewModel()
    
    # 創建一個測試設備ID
    test_device_id = "TEST001"
    
    # 創建窗口控制器
    controller = MainWindowController(test_device_id, view_model)
    controller.show()
    
    sys.exit(app.exec()) 